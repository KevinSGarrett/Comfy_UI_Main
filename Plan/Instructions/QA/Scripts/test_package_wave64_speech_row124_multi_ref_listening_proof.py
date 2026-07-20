from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/package_wave64_speech_row124_multi_ref_listening_proof.py"
SPEC = importlib.util.spec_from_file_location("row124_multi_ref_listening_proof", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class PackageWave64SpeechRow124MultiRefListeningProofTests(unittest.TestCase):
    def test_classify_blockers_clears_only_listening_request_gap(self) -> None:
        blockers = MODULE.classify_blockers(
            independent_source_reference_count=1,
            listening_request_prepared=True,
            raw_dialogue_timing_pass=False,
            production_reference_authority_pass=False,
        )
        by_class = {item["class"]: item for item in blockers}
        self.assertEqual(
            by_class["MULTI_REFERENCE_CONTINUITY"]["codes"],
            [
                "INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO",
                "MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE",
            ],
        )
        self.assertEqual(
            by_class["PRODUCTION_VOICE_AUTHORITY"]["codes"],
            ["PRODUCTION_CHARACTER_REFERENCE_AUTHORITY_ABSENT"],
        )
        self.assertEqual(
            by_class["LISTENING_AUTHORITY"]["codes"],
            ["INDEPENDENT_PLAYBACK_REVIEW_ABSENT", "FINAL_VOICE_CERTIFICATION_PENDING"],
        )
        self.assertEqual(
            by_class["LISTENING_AUTHORITY"]["cleared_by_this_packet"],
            ["LISTENING_REVIEW_REQUEST_UNPREPARED"],
        )
        self.assertEqual(
            by_class["DIALOGUE_TIMING"]["codes"],
            ["RAW_DIALOGUE_TIMING_OUT_OF_TOLERANCE"],
        )
        codes = MODULE.flatten_blocker_codes(blockers)
        self.assertNotIn("LISTENING_REVIEW_REQUEST_UNPREPARED", codes)
        self.assertIn("INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO", codes)

    def test_classify_blockers_marks_unprepared_listening_request(self) -> None:
        blockers = MODULE.classify_blockers(
            independent_source_reference_count=2,
            listening_request_prepared=False,
            raw_dialogue_timing_pass=True,
            production_reference_authority_pass=False,
        )
        listening = next(item for item in blockers if item["class"] == "LISTENING_AUTHORITY")
        self.assertIn("LISTENING_REVIEW_REQUEST_UNPREPARED", listening["codes"])
        self.assertEqual(listening["cleared_by_this_packet"], [])
        multi_ref = next(item for item in blockers if item["class"] == "MULTI_REFERENCE_CONTINUITY")
        self.assertEqual(multi_ref["codes"], ["MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE"])

    def test_verify_row124_rejects_complete_claim(self) -> None:
        row = {
            "runtime_classification": MODULE.EXPECTED_ROW124_CLASSIFICATION,
            "row_complete": True,
            "automated_gates": {
                "chain_specific_speaker_identity_pass": True,
                "raw_dialogue_timing_pass": False,
                "independent_playback_review_pass": False,
                "production_reference_authority_pass": False,
                "final_voice_certification_pass": False,
                "row_complete": False,
            },
            "row": {
                "tracker_id": MODULE.TRACKER_ID,
                "item_id": MODULE.ITEM_ID,
                "status": MODULE.ROW_STATUS,
            },
            "durable_artifacts": {
                "candidate": {"sha256": MODULE.EXPECTED_CANDIDATE_SHA256},
            },
        }
        with self.assertRaisesRegex(MODULE.ProofError, "row_complete"):
            MODULE.verify_row124_evidence(row)

    def test_verify_continuity_rejects_multi_source_claim(self) -> None:
        evaluation = {
            "classification": MODULE.EXPECTED_CONTINUITY_CLASSIFICATION,
            "continuity_summary": {"line_count": 10, "scene_count": 3},
            "row_gates": {
                "131": {
                    "independent_source_reference_count": 2,
                    "calibrated_embedding_route_count": 1,
                    "false_acceptance_measured": False,
                    "row_complete": False,
                },
                "132": {"independent_playback_review_pass": False, "row_complete": False},
                "133": {"row_complete": False},
            },
        }
        with self.assertRaisesRegex(MODULE.ProofError, "exactly one independent source reference"):
            MODULE.verify_continuity_diagnostic(evaluation)

    def test_dry_run_builds_offline_packet_without_writes(self) -> None:
        packet = MODULE.build_proof_packet(ROOT, stamp="DRYRUNTEST", write_outputs=False)
        self.assertEqual(packet["proof_tier"], "OFFLINE_PROOF_BOUNDED")
        self.assertFalse(packet["row_complete"])
        self.assertFalse(packet["decision"]["product_completion"])
        self.assertFalse(packet["boundaries"]["gpu_used"])
        self.assertFalse(packet["boundaries"]["sound_csv_written"])
        self.assertFalse(packet["boundaries"]["row075_touched"])
        self.assertIn("listening_review_request_payload", packet)
        self.assertIn("INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO", packet["blocker_codes"])
        self.assertFalse(
            (
                ROOT
                / "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-124_MULTI_REF_LISTENING_CURRENT_DELTA_DRYRUNTEST.json"
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
