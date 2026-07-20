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
    def test_classify_blockers_clears_listening_request_when_single_ref(self) -> None:
        blockers = MODULE.classify_blockers(
            independent_source_reference_count=1,
            listening_request_prepared=True,
            raw_dialogue_timing_pass=False,
            production_reference_authority_pass=False,
            matrix_complete=False,
        )
        by_class = {item["class"]: item for item in blockers}
        self.assertEqual(
            by_class["MULTI_REFERENCE_CONTINUITY"]["codes"],
            [
                "INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO",
                "MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE",
            ],
        )
        self.assertEqual(by_class["MULTI_REFERENCE_CONTINUITY"]["cleared_by_this_packet"], [])
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
            [
                "RAW_DIALOGUE_TIMING_OUT_OF_TOLERANCE",
                MODULE.TIMING_DISPOSITION_UNDOCUMENTED_CODE,
            ],
        )
        codes = MODULE.flatten_blocker_codes(blockers)
        self.assertNotIn("LISTENING_REVIEW_REQUEST_UNPREPARED", codes)
        self.assertIn("INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO", codes)

    def test_classify_blockers_clears_independent_ref_count_when_two_bound(self) -> None:
        blockers = MODULE.classify_blockers(
            independent_source_reference_count=2,
            listening_request_prepared=True,
            raw_dialogue_timing_pass=False,
            production_reference_authority_pass=False,
            matrix_complete=False,
        )
        multi_ref = next(item for item in blockers if item["class"] == "MULTI_REFERENCE_CONTINUITY")
        self.assertEqual(multi_ref["codes"], ["MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE"])
        self.assertEqual(
            multi_ref["cleared_by_this_packet"],
            ["INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO"],
        )
        codes = MODULE.flatten_blocker_codes(blockers)
        self.assertNotIn("INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO", codes)
        self.assertIn("MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE", codes)
        self.assertIn("PRODUCTION_CHARACTER_REFERENCE_AUTHORITY_ABSENT", codes)

    def test_classify_blockers_clears_matrix_incomplete_when_measured_complete(self) -> None:
        blockers = MODULE.classify_blockers(
            independent_source_reference_count=2,
            listening_request_prepared=True,
            raw_dialogue_timing_pass=False,
            production_reference_authority_pass=False,
            matrix_complete=True,
        )
        multi_ref = next(item for item in blockers if item["class"] == "MULTI_REFERENCE_CONTINUITY")
        self.assertEqual(multi_ref["codes"], [])
        self.assertEqual(
            multi_ref["cleared_by_this_packet"],
            [
                "INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO",
                "MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE",
            ],
        )
        codes = MODULE.flatten_blocker_codes(blockers)
        self.assertNotIn("MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE", codes)
        self.assertIn("PRODUCTION_CHARACTER_REFERENCE_AUTHORITY_ABSENT", codes)
        self.assertIn("INDEPENDENT_PLAYBACK_REVIEW_ABSENT", codes)

    def test_classify_blockers_fail_closed_timing_waiver_retains_out_of_tolerance(self) -> None:
        blockers = MODULE.classify_blockers(
            independent_source_reference_count=2,
            listening_request_prepared=True,
            raw_dialogue_timing_pass=False,
            production_reference_authority_pass=False,
            matrix_complete=True,
            timing_waiver_packet_prepared=True,
            timing_waiver_granted=False,
        )
        timing = next(item for item in blockers if item["class"] == "DIALOGUE_TIMING")
        self.assertEqual(timing["codes"], ["RAW_DIALOGUE_TIMING_OUT_OF_TOLERANCE"])
        self.assertEqual(
            timing["cleared_by_this_packet"],
            [MODULE.TIMING_DISPOSITION_UNDOCUMENTED_CODE],
        )
        self.assertEqual(timing["disposition"], MODULE.TIMING_WAIVER_DISPOSITION)
        self.assertFalse(timing["timing_waiver_granted"])
        codes = MODULE.flatten_blocker_codes(blockers)
        self.assertIn("RAW_DIALOGUE_TIMING_OUT_OF_TOLERANCE", codes)
        self.assertNotIn(MODULE.TIMING_DISPOSITION_UNDOCUMENTED_CODE, codes)

    def test_build_fail_closed_timing_waiver_packet_exact_criteria(self) -> None:
        packet = MODULE.build_raw_dialogue_timing_fail_closed_waiver_packet(
            stamp="UNITTEST",
            candidate_sha256=MODULE.EXPECTED_CANDIDATE_SHA256,
        )
        self.assertFalse(packet["waiver_granted"])
        self.assertFalse(packet["raw_dialogue_timing_pass"])
        self.assertEqual(packet["blocker_code_retained"], "RAW_DIALOGUE_TIMING_OUT_OF_TOLERANCE")
        self.assertIn("path_a_retimed_immutable_candidate", packet["clearance_paths"])
        self.assertIn(
            "path_b_authorized_timing_contract_revision_or_waiver_grant",
            packet["clearance_paths"],
        )
        self.assertGreater(packet["measured"]["out_of_tolerance_by_seconds"], 0.0)
        self.assertFalse(packet["boundaries"]["timing_waiver_granted"])
        self.assertFalse(packet["row_complete"])

    def test_classify_blockers_marks_unprepared_listening_request(self) -> None:
        blockers = MODULE.classify_blockers(
            independent_source_reference_count=2,
            listening_request_prepared=False,
            raw_dialogue_timing_pass=True,
            production_reference_authority_pass=False,
            matrix_complete=False,
        )
        listening = next(item for item in blockers if item["class"] == "LISTENING_AUTHORITY")
        self.assertIn("LISTENING_REVIEW_REQUEST_UNPREPARED", listening["codes"])
        self.assertEqual(listening["cleared_by_this_packet"], [])
        multi_ref = next(item for item in blockers if item["class"] == "MULTI_REFERENCE_CONTINUITY")
        self.assertEqual(multi_ref["codes"], ["MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE"])

    def test_classify_blockers_records_class_f_a_when_second_ref_absent(self) -> None:
        blockers = MODULE.classify_blockers(
            independent_source_reference_count=1,
            listening_request_prepared=True,
            raw_dialogue_timing_pass=False,
            production_reference_authority_pass=False,
            matrix_complete=False,
            class_f_blocker=MODULE.CLASS_F_BLOCKER_CODE,
            class_a_blocker=MODULE.CLASS_A_BLOCKER_CODE,
        )
        multi_ref = next(item for item in blockers if item["class"] == "MULTI_REFERENCE_CONTINUITY")
        self.assertIn(MODULE.CLASS_F_BLOCKER_CODE, multi_ref["codes"])
        self.assertIn(MODULE.CLASS_A_BLOCKER_CODE, multi_ref["codes"])

    def test_windows_disjoint(self) -> None:
        self.assertTrue(MODULE.windows_disjoint((0.0, 5.0), (20.4, 21.8)))
        self.assertFalse(MODULE.windows_disjoint((0.0, 5.0), (4.5, 6.0)))

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
        with self.assertRaisesRegex(MODULE.ProofError, "one-source historical truth"):
            MODULE.verify_continuity_diagnostic(evaluation)

    def test_bind_independent_source_references_finds_two_disjoint(self) -> None:
        bound = MODULE.bind_independent_source_references(ROOT)
        self.assertFalse(bound["stop"])
        self.assertEqual(bound["independent_source_reference_count"], 2)
        self.assertIsNone(bound["class_f_blocker"])
        self.assertEqual(len(bound["references"]), 2)
        self.assertTrue(bound["disjointness"]["windows_disjoint"])
        self.assertNotEqual(
            bound["references"][0]["binding"]["sha256"],
            bound["references"][1]["binding"]["sha256"],
        )

    def test_dry_run_builds_offline_packet_without_writes(self) -> None:
        packet = MODULE.build_proof_packet(ROOT, stamp="DRYRUNTESTB", write_outputs=False)
        self.assertEqual(packet["proof_tier"], "OFFLINE_PROOF_BOUNDED")
        self.assertFalse(packet["row_complete"])
        self.assertFalse(packet["decision"]["product_completion"])
        self.assertFalse(packet["decision"]["listening_authority_granted"])
        self.assertFalse(packet["boundaries"]["gpu_used"])
        self.assertFalse(packet["boundaries"]["sound_csv_written"])
        self.assertFalse(packet["boundaries"]["row075_touched"])
        self.assertFalse(packet["boundaries"]["invented_voices"])
        self.assertFalse(packet["boundaries"]["timing_waiver_granted"])
        self.assertIn("listening_review_request_payload", packet)
        self.assertIn("multi_ref_drift_leakage_matrix_payload", packet)
        self.assertIn("raw_dialogue_timing_fail_closed_waiver_payload", packet)
        self.assertFalse(packet["raw_dialogue_timing_fail_closed_waiver_payload"]["waiver_granted"])
        self.assertNotIn("INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO", packet["blocker_codes"])
        self.assertIn("MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE", packet["blocker_codes"])
        self.assertIn("RAW_DIALOGUE_TIMING_OUT_OF_TOLERANCE", packet["blocker_codes"])
        self.assertNotIn(MODULE.TIMING_DISPOSITION_UNDOCUMENTED_CODE, packet["blocker_codes"])
        self.assertEqual(
            packet["independent_source_references"]["independent_source_reference_count"],
            2,
        )
        self.assertFalse(
            (
                ROOT
                / "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-124_MULTI_REF_LISTENING_CURRENT_DELTA_DRYRUNTESTB.json"
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
