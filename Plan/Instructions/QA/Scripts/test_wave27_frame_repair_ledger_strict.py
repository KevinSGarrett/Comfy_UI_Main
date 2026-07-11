#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/plan_wave27_frame_repair_ledger.py"
COMPILE_SCRIPT = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave27_frame_manifest.py"
SCORE_SCRIPT = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/score_wave27_temporal_evidence.py"
LEDGER_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave27_frame_repair_ledger.schema.json"

_SCRIPT_SPEC = importlib.util.spec_from_file_location("wave27_repair_ledger_script", SCRIPT)
if _SCRIPT_SPEC is None or _SCRIPT_SPEC.loader is None:
    raise RuntimeError("unable to load ledger script module for helper tests")
LEDGER_MODULE = importlib.util.module_from_spec(_SCRIPT_SPEC)
_SCRIPT_SPEC.loader.exec_module(LEDGER_MODULE)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class Wave27FrameRepairLedgerStrictTests(unittest.TestCase):
    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, capture_output=True, text=True, cwd=REPO_ROOT, check=False)

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _frame_record(self, idx: int, artifact: Path) -> dict[str, Any]:
        return {
            "frame_index": idx,
            "time_seconds": round(float(idx) * 0.04, 2),
            "source_route": "wave27_main",
            "engine_name": "ltxv",
            "shot_id": "shot_test",
            "visible_characters": ["char_a"],
            "camera_state": {"resolution": "512x512", "lens": "35mm"},
            "qa_scores": {
                "identity_drift_score": 3.0,
                "flicker_score": 4.0,
                "pose_continuity_score": 95.0,
                "depth_continuity_score": 95.0,
                "contact_continuity_score": 95.0,
                "export_integrity_score": 95.0,
                "overall_temporal_score": 95.0,
            },
            "repair_status": "none",
            "artifact_path": str(artifact),
            "artifact_sha256": _sha256(artifact),
        }

    def _build_packet(self, tmpdir: Path, frame_count: int = 6) -> tuple[Path, Path, list[Path]]:
        artifacts: list[Path] = []
        inputs: list[Path] = []
        for idx in range(frame_count):
            artifact = tmpdir / "src" / f"frame_{idx:03d}.png"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_bytes(f"src-frame-{idx}".encode("utf-8"))
            artifacts.append(artifact)
            record_path = tmpdir / "inputs" / f"frame_{idx:03d}.json"
            self._write_json(record_path, self._frame_record(idx, artifact))
            inputs.append(record_path)

        manifest_path = tmpdir / "packet" / "manifest.json"
        compile_cmd = [sys.executable, str(COMPILE_SCRIPT), "--input"] + [str(p) for p in inputs] + [
            "--output",
            str(manifest_path),
        ]
        compile_result = self._run(compile_cmd)
        self.assertEqual(compile_result.returncode, 0, compile_result.stderr)

        evidence_input = tmpdir / "packet" / "score_input.json"
        self._write_json(
            evidence_input,
            {
                "run_id": "wave27_ledger_test",
                "engine_name": "ltxv",
                "frame_count": frame_count,
                "loop_profile": "seamless_cycle",
                "identity_drift_score": 4.0,
                "flicker_score": 5.0,
                "pose_continuity_score": 94.0,
                "depth_continuity_score": 93.0,
                "contact_continuity_score": 95.0,
                "export_integrity_score": 96.0,
                "hard_failures": [],
                "repair_events": [],
            },
        )
        evidence_path = tmpdir / "packet" / "evidence.json"
        score_result = self._run(
            [
                sys.executable,
                str(SCORE_SCRIPT),
                "--root",
                str(REPO_ROOT),
                "--input",
                str(evidence_input),
                "--output",
                str(evidence_path),
            ]
        )
        self.assertEqual(score_result.returncode, 0, score_result.stderr)
        return manifest_path, evidence_path, artifacts

    def _make_defect_report(
        self,
        manifest_path: Path,
        evidence_path: Path,
        defects: list[dict[str, Any]],
        frame_count_override: int | None = None,
        manifest_seq_override: str | None = None,
        evidence_sha_override: str | None = None,
    ) -> dict[str, Any]:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        frame_count = manifest["frame_count"] if frame_count_override is None else frame_count_override
        manifest_seq = (
            manifest["sequence_sha256"]
            if manifest_seq_override is None
            else manifest_seq_override
        )
        evidence_sha = _sha256(evidence_path) if evidence_sha_override is None else evidence_sha_override
        return {
            "schema_name": "wave27_frame_defect_report",
            "report_version": 1,
            "frame_count": frame_count,
            "manifest_sequence_sha256": manifest_seq,
            "temporal_evidence_sha256": evidence_sha,
            "defects": defects,
        }

    def _run_ledger(
        self,
        manifest_path: Path,
        evidence_path: Path,
        defect_report_path: Path,
        output_path: Path,
        candidate_path: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--manifest",
            str(manifest_path),
            "--evidence",
            str(evidence_path),
            "--defect-report",
            str(defect_report_path),
            "--output-ledger",
            str(output_path),
        ]
        if candidate_path is not None:
            cmd.extend(["--candidate-manifest", str(candidate_path)])
        return self._run(cmd)

    def _refresh_manifest_sequence(self, manifest_payload: dict[str, Any]) -> None:
        payload = []
        for frame in manifest_payload["frames"]:
            payload.append(
                {
                    "frame_index": frame["frame_index"],
                    "time_seconds": float(frame["time_seconds"]),
                    "artifact_path": frame["artifact_path"],
                    "artifact_sha256": frame["artifact_sha256"],
                    "artifact_bytes": frame["artifact_bytes"],
                }
            )
        manifest_payload["sequence_sha256"] = hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).hexdigest()

    def _build_candidate_manifest(
        self, tmpdir: Path, source_manifest: Path, replacements: dict[int, bytes] | None = None
    ) -> Path:
        data = json.loads(source_manifest.read_text(encoding="utf-8"))
        replacements = replacements or {}
        for frame in data["frames"]:
            idx = frame["frame_index"]
            source_artifact = Path(frame["artifact_path"])
            candidate_artifact = tmpdir / "candidate" / f"frame_{idx:03d}.png"
            candidate_artifact.parent.mkdir(parents=True, exist_ok=True)
            if idx in replacements:
                candidate_artifact.write_bytes(replacements[idx])
            else:
                candidate_artifact.write_bytes(source_artifact.read_bytes())
            frame["artifact_path"] = str(candidate_artifact)
            frame["artifact_sha256"] = _sha256(candidate_artifact)
            frame["artifact_bytes"] = candidate_artifact.stat().st_size

        self._refresh_manifest_sequence(data)
        out = tmpdir / "candidate" / "manifest.json"
        self._write_json(out, data)
        return out

    def test_no_defect_exit_0_and_all_final_flags_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=4)
            defects = self._make_defect_report(manifest, evidence, defects=[])
            defect_path = tmpdir / "defects.json"
            self._write_json(defect_path, defects)
            ledger_path = tmpdir / "ledger.json"
            result = self._run_ledger(manifest, evidence, defect_path, ledger_path)
            self.assertEqual(result.returncode, 0)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["failed_frames"], [])
            self.assertEqual(ledger["repair_spans"], [])
            self.assertEqual(ledger["planning_status"], "repair_not_required")
            self.assertEqual(ledger["candidate_validation"]["status"], "no_repair_required")
            self.assertEqual(ledger["candidate_validation"]["target_frame_deltas"], [])
            self.assertTrue(all(value is False for value in ledger["final_flags"].values()))

            schema = json.loads(LEDGER_SCHEMA.read_text(encoding="utf-8"))
            validator = Draft202012Validator(schema)
            validator.validate(ledger)
            contradictory = json.loads(json.dumps(ledger))
            contradictory["planning_status"] = "repair_plan_candidate_verified"
            self.assertTrue(list(validator.iter_errors(contradictory)))

    def test_nonempty_defects_without_candidate_exit_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=4)
            defect_path = tmpdir / "defects.json"
            self._write_json(
                defect_path,
                self._make_defect_report(
                    manifest,
                    evidence,
                    defects=[{"frame_index": 2, "failure": "isolated_flicker"}],
                ),
            )
            result = self._run_ledger(manifest, evidence, defect_path, tmpdir / "ledger.json")
            self.assertEqual(result.returncode, 2)

    def test_invalid_taxonomy_index_binding_and_hash_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=4)
            cases = [
                [
                    {"frame_index": 0, "failure": "unknown_failure"},
                ],
                [
                    {"frame_index": 99, "failure": "isolated_flicker"},
                ],
            ]
            for defects in cases:
                defect_path = tmpdir / f"defect_{len(defects)}_{defects[0]['frame_index']}.json"
                self._write_json(defect_path, self._make_defect_report(manifest, evidence, defects=defects))
                result = self._run_ledger(manifest, evidence, defect_path, tmpdir / "out.json")
                self.assertEqual(result.returncode, 1)

            bad_bindings = self._make_defect_report(
                manifest,
                evidence,
                defects=[],
                manifest_seq_override="0" * 64,
                evidence_sha_override="f" * 64,
            )
            bad_bindings_path = tmpdir / "bad_bindings.json"
            self._write_json(bad_bindings_path, bad_bindings)
            result = self._run_ledger(manifest, evidence, bad_bindings_path, tmpdir / "out2.json")
            self.assertEqual(result.returncode, 1)

    def test_duplicate_defects_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=3)
            defect_path = tmpdir / "defects.json"
            self._write_json(
                defect_path,
                self._make_defect_report(
                    manifest,
                    evidence,
                    defects=[
                        {"frame_index": 1, "failure": "isolated_flicker"},
                        {"frame_index": 1, "failure": "isolated_flicker"},
                    ],
                ),
            )
            result = self._run_ledger(manifest, evidence, defect_path, tmpdir / "ledger.json")
            self.assertEqual(result.returncode, 1)

    def test_single_identity_and_flicker_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=4)
            defect_path = tmpdir / "defects.json"
            self._write_json(
                defect_path,
                self._make_defect_report(
                    manifest,
                    evidence,
                    defects=[
                        {"frame_index": 0, "failure": "single_frame_identity_drift"},
                        {"frame_index": 2, "failure": "isolated_flicker"},
                    ],
                ),
            )
            ledger_path = tmpdir / "ledger.json"
            result = self._run_ledger(manifest, evidence, defect_path, ledger_path)
            self.assertEqual(result.returncode, 2)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            actions = {span["start_frame_index"]: span["recommended_action"] for span in ledger["repair_spans"]}
            self.assertEqual(actions[0], "frame_local_identity_repair")
            self.assertEqual(actions[2], "frame_local_visual_repair")

    def test_span_2_to_5_routing_and_gt5_or_persistent_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=8)
            defect_path = tmpdir / "defects.json"
            self._write_json(
                defect_path,
                self._make_defect_report(
                    manifest,
                    evidence,
                    defects=[
                        {"frame_index": 1, "failure": "isolated_flicker"},
                        {"frame_index": 2, "failure": "isolated_flicker"},
                        {"frame_index": 3, "failure": "isolated_flicker"},
                        {"frame_index": 4, "failure": "isolated_flicker"},
                        {"frame_index": 5, "failure": "isolated_flicker"},
                        {"frame_index": 6, "failure": "persistent_shot_instability"},
                    ],
                ),
            )
            ledger_path = tmpdir / "ledger.json"
            result = self._run_ledger(manifest, evidence, defect_path, ledger_path)
            self.assertEqual(result.returncode, 2)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(len(ledger["repair_spans"]), 1)
            self.assertEqual(ledger["repair_spans"][0]["recommended_action"], "rerun_shot")

    def test_three_frame_contiguous_span_routes_to_short_span_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=6)
            defect_path = tmpdir / "defects.json"
            self._write_json(
                defect_path,
                self._make_defect_report(
                    manifest,
                    evidence,
                    defects=[
                        {"frame_index": 1, "failure": "isolated_flicker"},
                        {"frame_index": 2, "failure": "isolated_flicker"},
                        {"frame_index": 3, "failure": "isolated_flicker"},
                    ],
                ),
            )
            ledger_path = tmpdir / "ledger.json"
            result = self._run_ledger(manifest, evidence, defect_path, ledger_path)
            self.assertEqual(result.returncode, 2)
            span = json.loads(ledger_path.read_text(encoding="utf-8"))["repair_spans"][0]
            self.assertEqual(span["frame_indices"], [1, 2, 3])
            self.assertEqual(span["recommended_action"], "short_span_repair")
            self.assertEqual(span["reason"], "contiguous_span_2_to_5")

    def test_deterministic_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=4)
            defects = [
                {"frame_index": 2, "failure": "isolated_flicker"},
                {"frame_index": 1, "failure": "single_frame_identity_drift"},
            ]
            defect_path = tmpdir / "defects.json"
            self._write_json(defect_path, self._make_defect_report(manifest, evidence, defects=defects))
            out1 = tmpdir / "out1.json"
            out2 = tmpdir / "out2.json"
            r1 = self._run_ledger(manifest, evidence, defect_path, out1)
            r2 = self._run_ledger(manifest, evidence, defect_path, out2)
            self.assertEqual(r1.returncode, 2)
            self.assertEqual(r2.returncode, 2)
            self.assertEqual(out1.read_text(encoding="utf-8"), out2.read_text(encoding="utf-8"))

    def test_candidate_binding_hashes_and_target_deltas_and_preserved_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=5)
            defect_path = tmpdir / "defects.json"
            self._write_json(
                defect_path,
                self._make_defect_report(
                    manifest,
                    evidence,
                    defects=[
                        {"frame_index": 2, "failure": "isolated_flicker"},
                    ],
                ),
            )
            candidate = self._build_candidate_manifest(tmpdir, manifest, replacements={2: b"repaired-frame-2"})
            candidate_payload = json.loads(candidate.read_text(encoding="utf-8"))
            target = candidate_payload["frames"][2]
            target["source_route"] = "frame_repair_route"
            target["engine_name"] = "repair_engine"
            target["qa_scores"] = {"flicker_score": 98.0}
            target["repair_status"] = "repaired"
            self._write_json(candidate, candidate_payload)
            result = self._run_ledger(
                manifest, evidence, defect_path, tmpdir / "ledger.json", candidate_path=candidate
            )
            self.assertEqual(result.returncode, 0)
            ledger = json.loads((tmpdir / "ledger.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["planning_status"], "repair_plan_candidate_verified")
            self.assertEqual(ledger["candidate_validation"]["status"], "candidate_verified_technical_only")
            self.assertEqual(ledger["candidate_validation"]["candidate_manifest_path"], str(candidate))
            self.assertEqual(ledger["candidate_validation"]["candidate_manifest_sha256"], _sha256(candidate))
            candidate_manifest_payload = json.loads(candidate.read_text(encoding="utf-8"))
            self.assertEqual(
                ledger["candidate_validation"]["candidate_manifest_sequence_sha256"],
                candidate_manifest_payload["sequence_sha256"],
            )
            self.assertEqual(ledger["candidate_validation"]["target_frame_delta_count"], 1)
            self.assertEqual(
                ledger["candidate_validation"]["preserved_frame_verification_count"],
                4,
            )
            delta = ledger["candidate_validation"]["target_frame_deltas"][0]
            self.assertEqual(delta["frame_index"], 2)
            self.assertTrue(delta["artifact_changed"])
            self.assertTrue(delta["protected_metadata_unchanged"])
            self.assertEqual(delta["candidate_source_route"], "frame_repair_route")
            self.assertTrue(delta["source_route_changed"])
            self.assertEqual(delta["candidate_engine_name"], "repair_engine")
            self.assertTrue(delta["engine_name_changed"])
            self.assertEqual(delta["candidate_qa_scores"], {"flicker_score": 98.0})
            self.assertTrue(delta["qa_scores_changed"])
            self.assertEqual(delta["candidate_repair_status"], "repaired")
            self.assertTrue(delta["repair_status_changed"])
            preserved_frame_indices = {
                record["frame_index"]
                for record in ledger["candidate_validation"]["preserved_frame_verifications"]
            }
            self.assertEqual(preserved_frame_indices, {0, 1, 3, 4})
            self.assertIn("normalized_defects_sha256", ledger["source_bindings"])
            self.assertNotIn("defect_report_sequence_sha256", ledger["source_bindings"])
            self.assertTrue(all(value is False for value in ledger["final_flags"].values()))

    def test_zero_defect_candidate_must_not_introduce_delta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=5)
            defect_path = tmpdir / "defects.json"
            self._write_json(
                defect_path,
                self._make_defect_report(
                    manifest,
                    evidence,
                    defects=[],
                ),
            )
            candidate = self._build_candidate_manifest(tmpdir / "candidate", manifest, replacements={})
            result = self._run_ledger(manifest, evidence, defect_path, tmpdir / "o1.json", candidate_path=candidate)
            self.assertEqual(result.returncode, 0)
            ledger = json.loads((tmpdir / "o1.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["planning_status"], "repair_not_required")
            self.assertEqual(ledger["candidate_validation"]["status"], "no_repair_required")
            self.assertEqual(ledger["candidate_validation"]["target_frame_delta_count"], 0)
            self.assertEqual(
                ledger["candidate_validation"]["preserved_frame_verification_count"],
                5,
            )

            mutated_candidate = self._build_candidate_manifest(
                tmpdir / "candidate2", manifest, replacements={1: b"mutated-no-defect"}
            )
            r2 = self._run_ledger(
                manifest, evidence, defect_path, tmpdir / "o2.json", candidate_path=mutated_candidate
            )
            self.assertEqual(r2.returncode, 1)

    def test_passing_metadata_drift_rejected_all_protected_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=5)
            defect_path = tmpdir / "defects.json"
            self._write_json(
                defect_path,
                self._make_defect_report(
                    manifest,
                    evidence,
                    defects=[{"frame_index": 2, "failure": "isolated_flicker"}],
                ),
            )

            cases: list[tuple[str, Any]] = [
                ("frame_index", 99),
                ("source_route", "changed_route"),
                ("engine_name", "new_engine"),
                ("shot_id", "shot_other"),
                ("visible_characters", ["char_b"]),
                ("camera_state", {"resolution": "640x640", "lens": "35mm"}),
                (
                    "qa_scores",
                    {
                        "identity_drift_score": 1.0,
                        "flicker_score": 1.0,
                        "pose_continuity_score": 99.0,
                        "depth_continuity_score": 99.0,
                        "contact_continuity_score": 99.0,
                        "export_integrity_score": 99.0,
                        "overall_temporal_score": 99.0,
                    },
                ),
                ("repair_status", "repaired"),
                ("time_seconds", 12.34),
            ]
            for idx, (field, value) in enumerate(cases):
                candidate = self._build_candidate_manifest(
                    tmpdir / f"case_{idx}",
                    manifest,
                    replacements={2: b"changed-target"},
                )
                payload = json.loads(candidate.read_text(encoding="utf-8"))
                payload["frames"][0][field] = value
                self._refresh_manifest_sequence(payload)
                self._write_json(candidate, payload)
                result = self._run_ledger(
                    manifest, evidence, defect_path, tmpdir / f"drift_{idx}.json", candidate_path=candidate
                )
                self.assertEqual(result.returncode, 1, f"field {field} should be protected on passing frames")

    def test_target_protected_metadata_drift_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=5)
            defect_path = tmpdir / "defects.json"
            self._write_json(
                defect_path,
                self._make_defect_report(
                    manifest,
                    evidence,
                    defects=[{"frame_index": 2, "failure": "isolated_flicker"}],
                ),
            )
            cases: list[tuple[str, Any]] = [
                ("frame_index", 9),
                ("shot_id", "new_shot"),
                ("visible_characters", ["char_z"]),
                ("camera_state", {"resolution": "1024x1024", "lens": "50mm"}),
                ("time_seconds", 5.0),
            ]
            for idx, (field, value) in enumerate(cases):
                candidate = self._build_candidate_manifest(
                    tmpdir / f"target_case_{idx}",
                    manifest,
                    replacements={2: b"changed-target"},
                )
                payload = json.loads(candidate.read_text(encoding="utf-8"))
                payload["frames"][2][field] = value
                self._refresh_manifest_sequence(payload)
                self._write_json(candidate, payload)
                result = self._run_ledger(
                    manifest, evidence, defect_path, tmpdir / f"target_drift_{idx}.json", candidate_path=candidate
                )
                self.assertEqual(result.returncode, 1, f"field {field} should be protected on target frames")

            unchanged_target = self._build_candidate_manifest(tmpdir / "unchanged_target", manifest, replacements={})
            r_unchanged = self._run_ledger(
                manifest, evidence, defect_path, tmpdir / "unchanged_target_out.json", candidate_path=unchanged_target
            )
            self.assertEqual(r_unchanged.returncode, 1)

            changed_passing = self._build_candidate_manifest(
                tmpdir / "changed_passing", manifest, replacements={0: b"changed-passing", 2: b"changed-target"}
            )
            r2 = self._run_ledger(
                manifest, evidence, defect_path, tmpdir / "changed_passing_out.json", candidate_path=changed_passing
            )
            self.assertEqual(r2.returncode, 1)

    def test_tampered_candidate_artifact_and_existing_output_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, _ = self._build_packet(tmpdir, frame_count=5)
            defect_path = tmpdir / "defects.json"
            self._write_json(
                defect_path,
                self._make_defect_report(
                    manifest,
                    evidence,
                    defects=[{"frame_index": 3, "failure": "isolated_flicker"}],
                ),
            )

            candidate = self._build_candidate_manifest(tmpdir / "candidate", manifest, replacements={3: b"repair"})
            candidate_data = json.loads(candidate.read_text(encoding="utf-8"))
            tamper_path = Path(candidate_data["frames"][3]["artifact_path"])
            tamper_path.write_bytes(b"tampered-after-hash")
            self._write_json(candidate, candidate_data)
            result = self._run_ledger(
                manifest, evidence, defect_path, tmpdir / "ledger1.json", candidate_path=candidate
            )
            self.assertEqual(result.returncode, 1)

            output = tmpdir / "existing.json"
            output.write_text("keep-me\n", encoding="utf-8")
            result2 = self._run_ledger(manifest, evidence, defect_path, output)
            self.assertEqual(result2.returncode, 1)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep-me\n")

    def test_transactional_write_cleans_temp_on_publish_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            output = tmpdir / "out.json"
            before = set(tmpdir.iterdir())
            publish_call = "rename" if LEDGER_MODULE.os.name == "nt" else "link"
            with mock.patch.object(
                LEDGER_MODULE.os,
                publish_call,
                side_effect=PermissionError("blocked"),
            ):
                with self.assertRaises(PermissionError):
                    LEDGER_MODULE._write_transactional_json(output, {"k": "v"})
            after = set(tmpdir.iterdir())
            self.assertEqual(before, after)
            self.assertFalse(output.exists())

    def test_ledger_schema_is_draft202012_valid(self) -> None:
        schema = json.loads(LEDGER_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)


if __name__ == "__main__":
    unittest.main()
