from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/manage_wave64_speech_promotion.py"
SPEC = importlib.util.spec_from_file_location("wave64_speech_promotion", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_request(root: Path, candidate_id: str = "CANDIDATE-1") -> dict:
    artifact = root / "candidate.bin"
    artifact.write_bytes(b"immutable candidate fixture\n")
    artifact_hash = MODULE.sha256_file(artifact)
    return {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "character_version": "C01-V1",
        "artifact": {"path": str(artifact), "sha256": artifact_hash, "bytes": artifact.stat().st_size},
        "authority": {
            "identity_policy": "locked_character_voice",
            "reference_id": "REF-1",
            "reference_sha256": "1" * 64,
            "model_id": "MODEL-1",
            "approved_use": "production_dialogue",
            "rights_valid": True,
            "production_authorized": True,
            "reference_revoked": False,
            "model_revoked": False,
        },
        "evaluation": {"record_sha256": "2" * 64, "hard_gates_pass": True, "ranking_complete": True},
        "review": {
            "playback_review_pass": True,
            "playback_record_sha256": "3" * 64,
            "final_production_authority_pass": True,
            "production_record_sha256": "4" * 64,
            "roles_are_distinct": True,
            "artifact_sha256": artifact_hash,
        },
        "rollback": {"action": "restore_previous_active_or_none"},
        "content_based_suppression": False,
    }


class Wave64SpeechPromotionTests(unittest.TestCase):
    def test_missing_authority_is_refused_without_ledger_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = valid_request(root)
            request["review"]["playback_review_pass"] = False
            request["review"]["playback_record_sha256"] = None
            ledger = MODULE.PromotionLedger(root / "state.json")
            result = ledger.promote(request)
            self.assertEqual("refused", result["decision"])
            self.assertIn("review_playback_review_pass_not_passed", result["blockers"])
            self.assertFalse(result["ledger_mutated"])
            self.assertFalse((root / "state.json").exists())

    def test_atomic_promotion_is_idempotent_and_hash_conflicts_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = valid_request(root)
            ledger = MODULE.PromotionLedger(root / "state.json")
            first = ledger.promote(request)
            first_bytes = (root / "state.json").read_bytes()
            replay = ledger.promote(request)
            self.assertTrue(first["ledger_mutated"])
            self.assertTrue(replay["idempotent_replay"])
            self.assertFalse(replay["ledger_mutated"])
            self.assertEqual(first_bytes, (root / "state.json").read_bytes())
            conflicting = json.loads(json.dumps(request))
            other = root / "other.bin"
            other.write_bytes(b"different immutable bytes\n")
            conflicting["artifact"] = {"path": str(other), "sha256": MODULE.sha256_file(other), "bytes": other.stat().st_size}
            conflicting["review"]["artifact_sha256"] = conflicting["artifact"]["sha256"]
            with self.assertRaisesRegex(MODULE.PromotionError, "hash conflict"):
                ledger.promote(conflicting)

    def test_reference_revocation_invalidates_and_rollback_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = valid_request(root)
            ledger = MODULE.PromotionLedger(root / "state.json")
            ledger.promote(request)
            self.assertEqual(["CANDIDATE-1"], ledger.revoke(reference_ids={"REF-1"}))
            state = MODULE.load_object(root / "state.json")
            self.assertNotIn("CANDIDATE-1", state["active"])
            self.assertIn("REF-1", state["revoked_reference_ids"])
            replay = ledger.promote(request)
            self.assertIn("authority_reference_revoked_by_ledger", replay["blockers"])
            rollback_request = valid_request(root, "CANDIDATE-2")
            rollback_request["authority"]["reference_id"] = "REF-2"
            rollback_request["authority"]["reference_sha256"] = "5" * 64
            ledger.promote(rollback_request)
            result = ledger.rollback("CANDIDATE-2")
            self.assertEqual("rolled_back", result["decision"])
            self.assertTrue(ledger.rollback("CANDIDATE-2")["idempotent_replay"])

    def test_review_hash_must_match_promoted_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            request = valid_request(Path(temporary))
            request["review"]["artifact_sha256"] = "f" * 64
            self.assertIn("review_artifact_sha256_mismatch", MODULE.validate_promotion_request(request))


if __name__ == "__main__":
    unittest.main()
