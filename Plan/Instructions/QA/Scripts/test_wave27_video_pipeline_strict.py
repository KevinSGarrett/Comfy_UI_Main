#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts"
SCHEMA_DIR = REPO_ROOT / "Plan/08_SCHEMAS"
COMPILE_SCRIPT = SCRIPT_DIR / "compile_wave27_frame_manifest.py"
SCORE_SCRIPT = SCRIPT_DIR / "score_wave27_temporal_evidence.py"
VALIDATE_SCRIPT = SCRIPT_DIR / "run_wave27_local_validation.py"
FRAME_SCHEMA = SCHEMA_DIR / "wave27_frame_manifest.schema.json"
TEMPORAL_SCHEMA = SCHEMA_DIR / "wave27_temporal_evidence.schema.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class Wave27VideoPipelineStrictTests(unittest.TestCase):
    def _run(self, args: list[str], expect_ok: bool) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(args, capture_output=True, text=True, cwd=REPO_ROOT, check=False)
        if expect_ok and result.returncode != 0:
            self.fail(
                "Command failed unexpectedly:\n"
                f"cmd={' '.join(args)}\n"
                f"stdout={result.stdout}\n"
                f"stderr={result.stderr}"
            )
        if not expect_ok and result.returncode == 0:
            self.fail(
                "Command succeeded unexpectedly:\n"
                f"cmd={' '.join(args)}\n"
                f"stdout={result.stdout}\n"
                f"stderr={result.stderr}"
            )
        return result

    def _write_json(self, path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _frame_record(self, index: int, artifact_path: Path, artifact_sha: str) -> dict[str, object]:
        return {
            "frame_index": index,
            "time_seconds": float(index) * 0.04,
            "source_route": "wave27_main",
            "engine_name": "ltxv",
            "shot_id": f"shot_{index:04d}",
            "visible_characters": ["char_a"],
            "camera_state": {"lens": "35mm"},
            "qa_scores": {"identity_drift_score": 5.0, "flicker_score": 10.0},
            "repair_status": "none",
            "artifact_path": str(artifact_path),
            "artifact_sha256": artifact_sha,
        }

    def _score_payload(self, **overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "run_id": "run_001",
            "engine_name": "ltxv",
            "frame_count": 2,
            "loop_profile": "seamless_cycle",
            "identity_drift_score": 5.0,
            "flicker_score": 10.0,
            "pose_continuity_score": 93.0,
            "depth_continuity_score": 94.0,
            "contact_continuity_score": 95.0,
            "export_integrity_score": 96.0,
            "hard_failures": [],
            "repair_events": [],
        }
        payload.update(overrides)
        return payload

    def _build_valid_packet(self, tmpdir: Path) -> tuple[Path, Path]:
        artifact0 = tmpdir / "frame_000.png"
        artifact1 = tmpdir / "frame_001.png"
        artifact0.write_bytes(b"frame0")
        artifact1.write_bytes(b"frame1")

        in0 = tmpdir / "frame0.json"
        in1 = tmpdir / "frame1.json"
        self._write_json(in0, self._frame_record(0, artifact0, _sha256(artifact0)))
        self._write_json(in1, self._frame_record(1, artifact1, _sha256(artifact1)))

        manifest = tmpdir / "packet" / "manifest.json"
        self._run(
            [
                sys.executable,
                str(COMPILE_SCRIPT),
                "--input",
                str(in1),
                str(in0),
                "--output",
                str(manifest),
            ],
            expect_ok=True,
        )

        score_input = tmpdir / "score_input.json"
        self._write_json(
            score_input,
            {
                "run_id": "run_001",
                "engine_name": "ltxv",
                "frame_count": 2,
                "loop_profile": "seamless_cycle",
                "identity_drift_score": 5.0,
                "flicker_score": 10.0,
                "pose_continuity_score": 93.0,
                "depth_continuity_score": 94.0,
                "contact_continuity_score": 95.0,
                "export_integrity_score": 96.0,
                "hard_failures": [],
                "repair_events": [],
            },
        )
        evidence = tmpdir / "packet" / "evidence" / "evidence.json"
        self._run(
            [
                sys.executable,
                str(SCORE_SCRIPT),
                "--root",
                str(REPO_ROOT),
                "--input",
                str(score_input),
                "--output",
                str(evidence),
            ],
            expect_ok=True,
        )
        return manifest, evidence

    def _validate_strict(self, manifest: Path, evidence: Path, expect_ok: bool) -> subprocess.CompletedProcess[str]:
        return self._run(
            [
                sys.executable,
                str(VALIDATE_SCRIPT),
                "--root",
                str(REPO_ROOT),
                "--strict-packet",
                "--manifest",
                str(manifest),
                "--evidence",
                str(evidence),
                "--frame-schema",
                str(FRAME_SCHEMA),
                "--evidence-schema",
                str(TEMPORAL_SCHEMA),
            ],
            expect_ok=expect_ok,
        )

    def test_pack_integrity_mode_supports_repo_and_plan_root(self) -> None:
        repo_result = self._run(
            [sys.executable, str(VALIDATE_SCRIPT), "--root", str(REPO_ROOT)],
            expect_ok=True,
        )
        report = json.loads(repo_result.stdout)
        checked_paths = {entry["path"] for entry in report["checks"]["pack_integrity"]}
        for required_name in (
            "wave27_video_engine_registry.json",
            "wave27_video_route_selection_rules.json",
            "wave27_main_flow_video_routing_inventory.json",
        ):
            self.assertTrue(any(path.endswith(required_name) for path in checked_paths))
        self._run(
            [sys.executable, str(VALIDATE_SCRIPT), "--root", str(REPO_ROOT / "Plan")],
            expect_ok=True,
        )

    def test_valid_six_dimension_strict_packet_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence = self._build_valid_packet(tmpdir)
            validation = self._validate_strict(manifest, evidence, expect_ok=True)
            report = json.loads(validation.stdout)
            self.assertEqual(report["status"], "pass")
            manifest, evidence = self._build_valid_packet(tmpdir)
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual([frame["frame_index"] for frame in manifest_data["frames"]], [0, 1])
            self.assertIn("sequence_sha256", manifest_data)
            evidence_data = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertEqual(evidence_data["promotion_decision"], "promote")
            self.assertFalse(evidence_data["loop_export"]["final_export_ready"])
            self.assertFalse(evidence_data["loop_export"]["final_export_passed"])

    def test_validator_rejects_artifact_hash_mutation_at_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence = self._build_valid_packet(tmpdir)
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            artifact_path = (manifest.parent / manifest_data["frames"][0]["artifact_path"]).resolve()
            artifact_path.write_bytes(b"mutated-data")
            self._validate_strict(manifest, evidence, expect_ok=False)

    def test_validator_rejects_frame_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence = self._build_valid_packet(tmpdir)
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            manifest_data["frame_count"] = 1
            self._write_json(manifest, manifest_data)
            self._validate_strict(manifest, evidence, expect_ok=False)

    def test_validator_rejects_list_order_and_timestamp_and_sequence_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence = self._build_valid_packet(tmpdir)
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            manifest_data["frames"][0], manifest_data["frames"][1] = (
                manifest_data["frames"][1],
                manifest_data["frames"][0],
            )
            manifest_data["frames"][1]["time_seconds"] = manifest_data["frames"][0]["time_seconds"]
            manifest_data["sequence_sha256"] = "0" * 64
            self._write_json(manifest, manifest_data)
            self._validate_strict(manifest, evidence, expect_ok=False)

    def test_compiler_rejects_duplicate_gap_empty_and_output_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            artifact0 = tmpdir / "frame0.png"
            artifact2 = tmpdir / "frame2.png"
            empty_artifact = tmpdir / "empty.png"
            artifact0.write_bytes(b"frame0")
            artifact2.write_bytes(b"frame2")
            empty_artifact.write_bytes(b"")

            record0 = self._frame_record(0, artifact0, _sha256(artifact0))
            cases = {
                "duplicate": [record0, dict(record0)],
                "gap": [record0, self._frame_record(2, artifact2, _sha256(artifact2))],
                "empty": [self._frame_record(0, empty_artifact, _sha256(empty_artifact))],
            }
            for name, records in cases.items():
                with self.subTest(name=name):
                    payload = tmpdir / f"{name}.json"
                    output = tmpdir / f"{name}_manifest.json"
                    self._write_json(payload, records)
                    self._run(
                        [
                            sys.executable,
                            str(COMPILE_SCRIPT),
                            "--input",
                            str(payload),
                            "--output",
                            str(output),
                        ],
                        expect_ok=False,
                    )

            overwrite_input = tmpdir / "overwrite.json"
            self._write_json(overwrite_input, record0)
            original_bytes = artifact0.read_bytes()
            self._run(
                [
                    sys.executable,
                    str(COMPILE_SCRIPT),
                    "--input",
                    str(overwrite_input),
                    "--output",
                    str(artifact0),
                ],
                expect_ok=False,
            )
            self.assertEqual(artifact0.read_bytes(), original_bytes)

    def test_validator_returns_structured_failure_for_malformed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence = self._build_valid_packet(tmpdir)
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            manifest_data["frames"][0] = {"frame_index": 0}
            self._write_json(manifest, manifest_data)
            result = self._validate_strict(manifest, evidence, expect_ok=False)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "fail")
            self.assertGreater(report["error_count"], 0)

    def test_scoring_rejects_unknown_engine_hard_failure_and_input_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            cases = {
                "engine": {"engine_name": "unknown_engine"},
                "hard_failure": {"hard_failures": ["unknown_failure"]},
                "input_field": {"misspelled_score": 99},
            }
            for name, overrides in cases.items():
                with self.subTest(name=name):
                    score_input = tmpdir / f"{name}.json"
                    output = tmpdir / f"{name}_evidence.json"
                    self._write_json(score_input, self._score_payload(**overrides))
                    self._run(
                        [
                            sys.executable,
                            str(SCORE_SCRIPT),
                            "--root",
                            str(REPO_ROOT),
                            "--input",
                            str(score_input),
                            "--output",
                            str(output),
                        ],
                        expect_ok=False,
                    )

    def test_scoring_rejects_mismatched_repair_action_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            score_input = tmpdir / "score_input.json"
            output = tmpdir / "evidence.json"
            self._write_json(
                score_input,
                self._score_payload(
                    frame_count=1,
                    repair_events=[
                        {
                            "frame_index": 0,
                            "action": "frame_local_identity_repair",
                            "event_type": "short_span_repair",
                            "status": "applied",
                        }
                    ],
                ),
            )
            self._run(
                [
                    sys.executable,
                    str(SCORE_SCRIPT),
                    "--root",
                    str(REPO_ROOT),
                    "--input",
                    str(score_input),
                    "--output",
                    str(output),
                ],
                expect_ok=False,
            )

    def test_validator_rejects_false_structural_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence = self._build_valid_packet(tmpdir)
            evidence_data = json.loads(evidence.read_text(encoding="utf-8"))
            evidence_data["loop_export"]["structural_gate_passed"] = False
            self._write_json(evidence, evidence_data)
            self._validate_strict(manifest, evidence, expect_ok=False)

    def test_scoring_rejects_unknown_repair_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            score_input = tmpdir / "score_input.json"
            output = tmpdir / "evidence.json"
            self._write_json(
                score_input,
                {
                    "run_id": "run_bad_action",
                    "engine_name": "ltxv",
                    "frame_count": 1,
                    "loop_profile": "seamless_cycle",
                    "identity_drift_score": 5.0,
                    "flicker_score": 5.0,
                    "pose_continuity_score": 90.0,
                    "depth_continuity_score": 90.0,
                    "contact_continuity_score": 90.0,
                    "export_integrity_score": 90.0,
                    "hard_failures": [],
                    "repair_events": [
                        {"frame_index": 0, "action": "not_in_policy", "status": "applied"}
                    ],
                },
            )
            self._run(
                [
                    sys.executable,
                    str(SCORE_SCRIPT),
                    "--root",
                    str(REPO_ROOT),
                    "--input",
                    str(score_input),
                    "--output",
                    str(output),
                ],
                expect_ok=False,
            )

    def test_scoring_rejects_unknown_loop_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            score_input = tmpdir / "score_input.json"
            output = tmpdir / "evidence.json"
            self._write_json(
                score_input,
                {
                    "run_id": "run_bad_loop",
                    "engine_name": "ltxv",
                    "frame_count": 1,
                    "loop_profile": "unknown_profile",
                    "identity_drift_score": 5.0,
                    "flicker_score": 5.0,
                    "pose_continuity_score": 90.0,
                    "depth_continuity_score": 90.0,
                    "contact_continuity_score": 90.0,
                    "export_integrity_score": 90.0,
                    "hard_failures": [],
                    "repair_events": [],
                },
            )
            self._run(
                [
                    sys.executable,
                    str(SCORE_SCRIPT),
                    "--root",
                    str(REPO_ROOT),
                    "--input",
                    str(score_input),
                    "--output",
                    str(output),
                ],
                expect_ok=False,
            )

    def test_hard_fail_forces_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            score_input = tmpdir / "score_input.json"
            output = tmpdir / "evidence.json"
            self._write_json(
                score_input,
                {
                    "run_id": "run_hard_fail",
                    "engine_name": "ltxv",
                    "frame_count": 1,
                    "loop_profile": "seamless_cycle",
                    "identity_drift_score": 1.0,
                    "flicker_score": 1.0,
                    "pose_continuity_score": 99.0,
                    "depth_continuity_score": 99.0,
                    "contact_continuity_score": 99.0,
                    "export_integrity_score": 99.0,
                    "hard_failures": ["identity_swap"],
                    "repair_events": [],
                },
            )
            self._run(
                [
                    sys.executable,
                    str(SCORE_SCRIPT),
                    "--root",
                    str(REPO_ROOT),
                    "--input",
                    str(score_input),
                    "--output",
                    str(output),
                ],
                expect_ok=True,
            )
            evidence = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(evidence["promotion_decision"], "block")

    def test_applied_repair_can_promote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            score_input = tmpdir / "score_input.json"
            output = tmpdir / "evidence.json"
            self._write_json(
                score_input,
                {
                    "run_id": "run_repair_promote",
                    "engine_name": "ltxv",
                    "frame_count": 1,
                    "loop_profile": "seamless_cycle",
                    "identity_drift_score": 2.0,
                    "flicker_score": 3.0,
                    "pose_continuity_score": 97.0,
                    "depth_continuity_score": 98.0,
                    "contact_continuity_score": 96.0,
                    "export_integrity_score": 99.0,
                    "hard_failures": [],
                    "repair_events": [
                        {
                            "frame_index": 0,
                            "action": "frame_local_identity_repair",
                            "status": "applied",
                        }
                    ],
                },
            )
            self._run(
                [
                    sys.executable,
                    str(SCORE_SCRIPT),
                    "--root",
                    str(REPO_ROOT),
                    "--input",
                    str(score_input),
                    "--output",
                    str(output),
                ],
                expect_ok=True,
            )
            evidence = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(evidence["promotion_decision"], "promote")

    def test_failed_repair_forces_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            score_input = tmpdir / "score_input.json"
            output = tmpdir / "evidence.json"
            self._write_json(
                score_input,
                {
                    "run_id": "run_failed_repair",
                    "engine_name": "ltxv",
                    "frame_count": 1,
                    "loop_profile": "seamless_cycle",
                    "identity_drift_score": 1.0,
                    "flicker_score": 1.0,
                    "pose_continuity_score": 98.0,
                    "depth_continuity_score": 98.0,
                    "contact_continuity_score": 98.0,
                    "export_integrity_score": 98.0,
                    "hard_failures": [],
                    "repair_events": [
                        {
                            "frame_index": 0,
                            "action": "frame_local_identity_repair",
                            "status": "failed",
                        }
                    ],
                },
            )
            self._run(
                [
                    sys.executable,
                    str(SCORE_SCRIPT),
                    "--root",
                    str(REPO_ROOT),
                    "--input",
                    str(score_input),
                    "--output",
                    str(output),
                ],
                expect_ok=True,
            )
            evidence = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(evidence["repair_policy_consistent"])
            self.assertEqual(evidence["promotion_decision"], "block")

    def test_validator_rejects_non_finite_json_and_final_export_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence = self._build_valid_packet(tmpdir)
            evidence_data = json.loads(evidence.read_text(encoding="utf-8"))
            evidence_data["loop_export"]["final_export_passed"] = True
            self._write_json(evidence, evidence_data)
            self._validate_strict(manifest, evidence, expect_ok=False)

            bad_evidence = tmpdir / "bad_nonfinite.json"
            bad_evidence.write_text(
                '{"schema_name":"wave27_temporal_evidence","evidence_version":1,"run_id":"x","engine_name":"y","frame_count":1,"loop_profile":"seamless_cycle","identity_drift_score":NaN}',
                encoding="utf-8",
            )
            self._validate_strict(manifest, bad_evidence, expect_ok=False)


if __name__ == "__main__":
    unittest.main()
