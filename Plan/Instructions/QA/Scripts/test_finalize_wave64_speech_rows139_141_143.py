from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "finalize_wave64_speech_rows139_141_143.py"
SPEC = importlib.util.spec_from_file_location("speech_mix_review_finalizer", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_packet() -> tuple[dict, dict, dict]:
    manifest = {
        "classification": MODULE.EXPECTED_CLASSIFICATION,
        "source_media_unchanged": True,
        "row139": {
            "status": MODULE.ROW_STATUS["139"], "row_complete": False,
            "ambience_continuity_gate_pass": True, "mix_balance_gate_pass": True,
        },
        "row141": {
            "status": MODULE.ROW_STATUS["141"], "row_complete": False,
            "spatial_room_evaluator_executed": True, "mandatory_ensemble_complete": False,
        },
        "row143": {
            "status": MODULE.ROW_STATUS["143"], "row_complete": False, "request_schema_valid": True,
            "human_review_record_present": False, "human_playback_proof_present": False,
        },
        "boundaries": {
            "is_synthetic": True, "automated_metrics_are_human_review": False,
            "human_review_fabricated": False, "production_runtime_proof_present": False,
            "production_authority_present": False, "production_ready": False,
            "content_based_suppression": False, "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False,
        },
    }
    gates = {name: {"status": "PASS"} for name in (
        "ambience_continuity", "mix_balance_review", "spatial_position_check",
    )}
    gates["room_reverb_check"] = {"status": "FAIL"}
    for name in ("spatial_audio_playback_review", "production_runtime_proof", "production_spatial_room_authority"):
        gates[name] = {"status": "BLOCKED"}
    gates["overall_pass"] = {"status": "FAIL"}
    report = {"gates": gates, "overall_pass": False, "is_synthetic": True}
    request = {
        "schema_name": "wave64_human_audio_review_request",
        "review_id": "W64-SPEECH-L01-SPATIAL-MIX-HUMAN-REVIEW-001",
    }
    return manifest, report, request


class SpeechMixReviewFinalizerTests(unittest.TestCase):
    def test_row_statuses_are_fail_closed(self) -> None:
        self.assertEqual({"139", "141", "143"}, set(MODULE.ROW_STATUS))
        self.assertTrue(all(status.startswith("Blocked_") for status in MODULE.ROW_STATUS.values()))

    def test_validate_packet_accepts_bounded_result(self) -> None:
        MODULE.validate_packet(*valid_packet())

    def test_validate_packet_rejects_false_authority(self) -> None:
        manifest, report, request = valid_packet()
        manifest["boundaries"]["production_ready"] = True
        with self.assertRaises(MODULE.FinalizationError):
            MODULE.validate_packet(manifest, report, request)

    def test_validate_packet_rejects_fabricated_human_authority(self) -> None:
        for field in ("human_review_record_present", "human_playback_proof_present"):
            with self.subTest(field=field):
                manifest, report, request = valid_packet()
                manifest["row143"][field] = True
                with self.assertRaisesRegex(MODULE.FinalizationError, "human review authority"):
                    MODULE.validate_packet(manifest, report, request)

    def test_validate_packet_rejects_review_request_identity_mismatch(self) -> None:
        for field, value in (("schema_name", "wrong_schema"), ("review_id", "wrong_review")):
            with self.subTest(field=field):
                manifest, report, request = valid_packet()
                request[field] = value
                with self.assertRaisesRegex(MODULE.FinalizationError, r"request(?: schema)? identity"):
                    MODULE.validate_packet(manifest, report, request)

    def test_validate_packet_requires_room_failure_and_blocked_playback(self) -> None:
        manifest, report, request = valid_packet()
        report["gates"]["room_reverb_check"]["status"] = "PASS"
        with self.assertRaisesRegex(MODULE.FinalizationError, "room conformance failure"):
            MODULE.validate_packet(manifest, report, request)
        manifest, report, request = valid_packet()
        report["gates"]["spatial_audio_playback_review"]["status"] = "PASS"
        with self.assertRaisesRegex(MODULE.FinalizationError, "not blocked"):
            MODULE.validate_packet(manifest, report, request)

    def test_csv_update_is_idempotent_and_preserves_other_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rows.csv"
            fields = ["Item_ID", "Status", "Coverage_Audit_Status", "Evidence_Path", "Status_Decision", "Notes"]
            rows = [{name: "old" for name in fields} | {"Item_ID": f"ITEM-W64-{number}"} for number in (139, 141, 143)]
            rows.append({name: "keep" for name in fields} | {"Item_ID": "ITEM-W64-999", "Status": "UserOwned"})
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            MODULE.update_rows(path, "Item_ID", "ITEM", "evidence")
            first = path.read_bytes()
            MODULE.update_rows(path, "Item_ID", "ITEM", "evidence")
            self.assertEqual(first, path.read_bytes())
            with path.open("r", encoding="utf-8", newline="") as handle:
                updated = list(csv.DictReader(handle))
            self.assertEqual("UserOwned", updated[-1]["Status"])
            self.assertTrue(all(updated[index]["Status"].startswith("Blocked_") for index in range(3)))

    def test_copy_exact_rejects_existing_hash_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.bin"
            destination = root / "durable.bin"
            source.write_bytes(b"source")
            destination.write_bytes(b"conflict")
            with self.assertRaises(MODULE.FinalizationError):
                MODULE.copy_exact(source, destination)

    def test_bound_file_rejects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "artifact.json"
            path.write_text(json.dumps({"value": 1}), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.FinalizationError, "binding mismatch"):
                MODULE.require_bound_file({"sha256": "0" * 64}, path, "artifact")


if __name__ == "__main__":
    unittest.main()
