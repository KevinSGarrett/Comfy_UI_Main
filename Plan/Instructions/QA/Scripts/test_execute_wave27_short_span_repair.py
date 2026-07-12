from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import cv2
import jsonschema
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
EXECUTOR = ROOT / "Plan/07_IMPLEMENTATION/scripts/execute_wave27_short_span_repair.py"
PLANNER = ROOT / "Plan/07_IMPLEMENTATION/scripts/plan_wave27_frame_repair_ledger.py"
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave27_frame_manifest.py"
SCORER = ROOT / "Plan/07_IMPLEMENTATION/scripts/score_wave27_temporal_evidence.py"
EXECUTION_SCHEMA = ROOT / "Plan/08_SCHEMAS/wave27_short_span_repair_execution.schema.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ShortSpanRepairExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cmd(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)

    def write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def frame_record(self, index: int, artifact: Path, camera: str = "static") -> dict[str, Any]:
        return {
            "frame_index": index, "time_seconds": round(index * 0.04, 2),
            "source_route": "wave27_main", "engine_name": "ltxv", "shot_id": "shot_test",
            "visible_characters": ["char_a"], "camera_state": {"mode": camera},
            "qa_scores": {"flicker_score": 4.0, "overall_temporal_score": 95.0},
            "repair_status": "none", "artifact_path": str(artifact), "artifact_sha256": sha256(artifact),
        }

    def build_packet(self, defects: list[dict[str, Any]], *, corrupt_frame: int | None = None, boundary_camera_mismatch: bool = False, interior_camera_mismatch: bool = False, alpha: bool = False, grayscale: bool = False) -> tuple[Path, Path, Path, Path]:
        inputs: list[Path] = []
        for index in range(6):
            artifact = self.work / "src" / f"frame_{index:03d}.png"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            if index == corrupt_frame:
                artifact.write_bytes(b"not-an-image")
            else:
                frame = np.zeros((72, 96) if grayscale else (72, 96, 4 if alpha else 3), dtype=np.uint8)
                frame[:] = 20 + index * 8 if grayscale else ((20 + index * 8, 30, 50, 140 + index) if alpha else (20 + index * 8, 30, 50))
                cv2.rectangle(frame, (8 + index * 5, 20), (28 + index * 5, 48), 220 if grayscale else ((220, 180, 60, 210) if alpha else (220, 180, 60)), -1)
                if index in {2, 3, 4}:
                    frame[10:25, 10:40] = 250 if grayscale else ((250, 20 * index, 240, 180) if alpha else (250, 20 * index, 240))
                self.assertTrue(cv2.imwrite(str(artifact), frame))
            mismatch = (boundary_camera_mismatch and index == 5) or (interior_camera_mismatch and index == 3)
            record = self.frame_record(index, artifact, "mismatch" if mismatch else "static")
            record_path = self.work / "inputs" / f"frame_{index:03d}.json"
            self.write_json(record_path, record)
            inputs.append(record_path)
        manifest = self.work / "packet/manifest.json"
        compiled = self.run_cmd([sys.executable, str(COMPILER), "--input", *[str(path) for path in inputs], "--output", str(manifest)])
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        score_input = self.work / "packet/score_input.json"
        self.write_json(score_input, {"run_id": "executor_test", "engine_name": "ltxv", "frame_count": 6, "loop_profile": "seamless_cycle", "identity_drift_score": 4.0, "flicker_score": 5.0, "pose_continuity_score": 94.0, "depth_continuity_score": 93.0, "contact_continuity_score": 95.0, "export_integrity_score": 96.0, "hard_failures": [], "repair_events": []})
        evidence = self.work / "packet/evidence.json"
        scored = self.run_cmd([sys.executable, str(SCORER), "--root", str(ROOT), "--input", str(score_input), "--output", str(evidence)])
        self.assertEqual(scored.returncode, 0, scored.stderr)
        manifest_data = json.loads(manifest.read_text())
        defect_report = self.work / "packet/defects.json"
        self.write_json(defect_report, {"schema_name": "wave27_frame_defect_report", "report_version": 1, "frame_count": 6, "manifest_sequence_sha256": manifest_data["sequence_sha256"], "temporal_evidence_sha256": sha256(evidence), "defects": defects})
        ledger = self.work / "packet/ledger.json"
        planned = self.run_cmd([sys.executable, str(PLANNER), "--manifest", str(manifest), "--evidence", str(evidence), "--defect-report", str(defect_report), "--output-ledger", str(ledger)])
        self.assertEqual(planned.returncode, 2, planned.stderr)
        return manifest, evidence, defect_report, ledger

    def execute(self, ledger: Path, output: Path) -> subprocess.CompletedProcess[str]:
        return self.run_cmd([sys.executable, str(EXECUTOR), "--repair-ledger", str(ledger), "--output-dir", str(output), "--root", str(ROOT)])

    def standard_defects(self) -> list[dict[str, Any]]:
        return [{"frame_index": index, "failure": "isolated_flicker"} for index in (2, 3, 4)]

    def test_candidate_is_generated_and_existing_planner_verifies_it(self) -> None:
        manifest, evidence, defects, ledger = self.build_packet(self.standard_defects())
        output = self.work / "candidate"
        result = self.execute(ledger, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        verified = self.work / "verified_ledger.json"
        checked = self.run_cmd([sys.executable, str(PLANNER), "--manifest", str(manifest), "--evidence", str(evidence), "--defect-report", str(defects), "--candidate-manifest", str(output / "candidate_manifest.json"), "--output-ledger", str(verified)])
        self.assertEqual(checked.returncode, 0, checked.stderr)
        ledger_data = json.loads(verified.read_text())
        self.assertEqual(ledger_data["planning_status"], "repair_plan_candidate_verified")
        self.assertEqual(ledger_data["candidate_validation"]["target_frame_delta_count"], 3)
        self.assertEqual(ledger_data["candidate_validation"]["preserved_frame_verification_count"], 3)

    def test_passing_frames_are_byte_preserved_and_targets_change(self) -> None:
        manifest, _, _, ledger = self.build_packet(self.standard_defects())
        source = json.loads(manifest.read_text())
        output = self.work / "candidate"
        self.assertEqual(self.execute(ledger, output).returncode, 0)
        candidate = json.loads((output / "candidate_manifest.json").read_text())
        for index in (0, 1, 5):
            self.assertEqual((output / candidate["frames"][index]["artifact_path"]).read_bytes(), Path(source["frames"][index]["artifact_path"]).read_bytes())
        for index in (2, 3, 4):
            self.assertNotEqual(candidate["frames"][index]["artifact_sha256"], source["frames"][index]["artifact_sha256"])
            self.assertEqual(candidate["frames"][index]["repair_status"], "repaired")

    def test_execution_evidence_is_schema_valid_and_claim_bounded(self) -> None:
        _, _, _, ledger = self.build_packet(self.standard_defects())
        output = self.work / "candidate"
        self.assertEqual(self.execute(ledger, output).returncode, 0)
        execution = json.loads((output / "repair_execution.json").read_text())
        jsonschema.Draft202012Validator(json.loads(EXECUTION_SCHEMA.read_text())).validate(execution)
        self.assertTrue(execution["claims"]["technical_candidate_generated"])
        self.assertTrue(execution["claims"]["passing_frames_preserved"])
        self.assertTrue(all(value is False for key, value in execution["claims"].items() if key not in {"technical_candidate_generated", "passing_frames_preserved"}))

    def test_repeat_execution_is_byte_deterministic(self) -> None:
        _, _, _, ledger = self.build_packet(self.standard_defects())
        first, second = self.work / "first", self.work / "second"
        self.assertEqual(self.execute(ledger, first).returncode, 0)
        self.assertEqual(self.execute(ledger, second).returncode, 0)
        for relative in ["candidate_manifest.json", "repair_execution.json", *[f"frames/frame_{index:06d}.png" for index in range(6)]]:
            self.assertEqual((first / relative).read_bytes(), (second / relative).read_bytes())

    def test_identity_and_rerun_actions_are_rejected(self) -> None:
        cases = [
            [{"frame_index": 2, "failure": "single_frame_identity_drift"}],
            [{"frame_index": 2, "failure": "persistent_shot_instability"}],
        ]
        for case_index, defects in enumerate(cases):
            with self.subTest(case=case_index):
                case_dir = self.work / f"case-{case_index}"
                case_dir.mkdir()
                original = self.work
                self.work = case_dir
                try:
                    _, _, _, ledger = self.build_packet(defects)
                    result = self.execute(ledger, case_dir / "candidate")
                    self.assertEqual(result.returncode, 2)
                finally:
                    self.work = original

    def test_edge_span_without_two_boundaries_is_rejected(self) -> None:
        _, _, _, ledger = self.build_packet([{"frame_index": 0, "failure": "isolated_flicker"}])
        result = self.execute(ledger, self.work / "candidate")
        self.assertEqual(result.returncode, 2)
        self.assertIn("boundaries", result.stderr)

    def test_nondecodable_bound_source_frame_is_rejected(self) -> None:
        _, _, _, ledger = self.build_packet(self.standard_defects(), corrupt_frame=3)
        result = self.execute(ledger, self.work / "candidate")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not decodable", result.stderr)

    def test_boundary_metadata_mismatch_is_rejected(self) -> None:
        _, _, _, ledger = self.build_packet(self.standard_defects(), boundary_camera_mismatch=True)
        result = self.execute(ledger, self.work / "candidate")
        self.assertEqual(result.returncode, 2)
        self.assertIn("protected camera_state", result.stderr)

    def test_interior_metadata_mismatch_is_rejected(self) -> None:
        _, _, _, ledger = self.build_packet(self.standard_defects(), interior_camera_mismatch=True)
        result = self.execute(ledger, self.work / "candidate")
        self.assertEqual(result.returncode, 2)
        self.assertIn("repair interior differs in protected camera_state", result.stderr)

    def test_overlapping_spans_are_rejected(self) -> None:
        _, _, _, ledger = self.build_packet(self.standard_defects())
        payload = json.loads(ledger.read_text())
        payload["repair_spans"].append(json.loads(json.dumps(payload["repair_spans"][0])))
        self.write_json(ledger, payload)
        result = self.execute(ledger, self.work / "candidate")
        self.assertEqual(result.returncode, 2)
        self.assertIn("repair spans overlap", result.stderr)

    def test_alpha_channel_is_preserved_for_repaired_and_passing_frames(self) -> None:
        _, _, _, ledger = self.build_packet(self.standard_defects(), alpha=True)
        output = self.work / "candidate"
        result = self.execute(ledger, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        candidate = json.loads((output / "candidate_manifest.json").read_text())
        for frame in candidate["frames"]:
            image = cv2.imread(str(output / frame["artifact_path"]), cv2.IMREAD_UNCHANGED)
            self.assertEqual(image.shape[2], 4)
        execution = json.loads((output / "repair_execution.json").read_text())
        self.assertEqual(execution["image_format"]["channel_count"], 4)

    def test_grayscale_channel_is_preserved_for_repaired_and_passing_frames(self) -> None:
        _, _, _, ledger = self.build_packet(self.standard_defects(), grayscale=True)
        output = self.work / "candidate"
        result = self.execute(ledger, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        candidate = json.loads((output / "candidate_manifest.json").read_text())
        for frame in candidate["frames"]:
            image = cv2.imread(str(output / frame["artifact_path"]), cv2.IMREAD_UNCHANGED)
            self.assertEqual(image.ndim, 2)
        execution = json.loads((output / "repair_execution.json").read_text())
        self.assertEqual(execution["image_format"]["channel_count"], 1)

    def test_tampered_source_manifest_is_rejected(self) -> None:
        manifest, _, _, ledger = self.build_packet(self.standard_defects())
        manifest.write_text(manifest.read_text().replace("wave27_main", "tampered", 1), encoding="utf-8")
        result = self.execute(ledger, self.work / "candidate")
        self.assertEqual(result.returncode, 2)
        self.assertIn("SHA256 binding mismatch", result.stderr)

    def test_existing_output_is_preserved(self) -> None:
        _, _, _, ledger = self.build_packet(self.standard_defects())
        output = self.work / "candidate"
        output.mkdir()
        marker = output / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        result = self.execute(ledger, output)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(marker.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
