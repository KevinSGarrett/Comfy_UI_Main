#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts"
COMPILE_SCRIPT = SCRIPT_DIR / "compile_wave27_frame_manifest.py"
SCORE_SCRIPT = SCRIPT_DIR / "score_wave27_temporal_evidence.py"
PREP_SCRIPT = SCRIPT_DIR / "prepare_wave27_strict_visual_review_packet.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class PrepareWave27StrictVisualReviewPacketTests(unittest.TestCase):
    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, capture_output=True, text=True, cwd=REPO_ROOT, check=False)

    def _write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _load_json(self, path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _make_frame_record(self, idx: int, artifact: Path) -> dict[str, object]:
        return {
            "frame_index": idx,
            "time_seconds": round(float(idx) * 0.05, 3),
            "source_route": "wave27_main",
            "engine_name": "ltxv",
            "shot_id": f"shot_{idx:04d}",
            "visible_characters": ["char_a"],
            "camera_state": {"lens": "35mm"},
            "qa_scores": {"identity_drift_score": 5.0, "flicker_score": 5.0},
            "repair_status": "none",
            "artifact_path": str(artifact),
            "artifact_sha256": _sha256(artifact),
        }

    def _make_score_payload(self, frame_count: int) -> dict[str, object]:
        return {
            "run_id": "run_001",
            "engine_name": "ltxv",
            "frame_count": frame_count,
            "loop_profile": "seamless_cycle",
            "identity_drift_score": 5.0,
            "flicker_score": 6.0,
            "pose_continuity_score": 93.0,
            "depth_continuity_score": 94.0,
            "contact_continuity_score": 95.0,
            "export_integrity_score": 96.0,
            "hard_failures": [],
            "repair_events": [],
        }

    def _write_prereq_evidence(
        self,
        base_dir: Path,
        category: str,
        sequence_sha256: str,
        *,
        result: str = "pass",
        evidence_type: str | None = None,
        sequence_override: str | None = None,
    ) -> dict[str, str]:
        rel_path = Path("prereq_evidence") / f"{category}.json"
        abs_path = base_dir / rel_path
        payload = {
            "evidence_type": category if evidence_type is None else evidence_type,
            "sequence_sha256": sequence_sha256 if sequence_override is None else sequence_override,
            "result": result,
            "notes": f"{category} check",
        }
        self._write_json(abs_path, payload)
        return {
            "status": "verified",
            "path": rel_path.as_posix(),
            "sha256": _sha256(abs_path),
        }

    def _base_prerequisites(self, base_dir: Path, sequence_sha256: str) -> dict[str, object]:
        prerequisites: dict[str, object] = {
            "audio_required": True,
        }
        for category in (
            "identity_detector",
            "face_detector",
            "body_silhouette_evidence",
            "hand_finger_evidence",
            "trusted_contact_mask_evidence",
            "motion_analysis",
            "object_background_camera_analysis",
            "audio_asset_evidence",
            "audio_timing_evidence",
        ):
            prerequisites[category] = self._write_prereq_evidence(
                base_dir=base_dir,
                category=category,
                sequence_sha256=sequence_sha256,
            )
        return prerequisites

    def _create_strict_manifest_and_evidence(
        self,
        tmpdir: Path,
        frame_sizes: list[tuple[int, int]],
        undecodable: bool = False,
    ) -> tuple[Path, Path]:
        tmpdir.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, object]] = []
        for idx, (width, height) in enumerate(frame_sizes):
            artifact = tmpdir / f"frame_{idx:03d}.png"
            if undecodable:
                artifact.write_bytes(f"not-an-image-{idx}".encode("utf-8"))
            else:
                image = Image.new("RGB", (width, height), color=(30 + idx, 60 + idx, 90 + idx))
                image.save(artifact, format="PNG")
            records.append(self._make_frame_record(idx, artifact))

        records_path = tmpdir / "records.json"
        self._write_json(records_path, records)
        manifest_path = tmpdir / "packet/manifest.json"
        compile_result = self._run(
            [
                sys.executable,
                str(COMPILE_SCRIPT),
                "--input",
                str(records_path),
                "--output",
                str(manifest_path),
            ]
        )
        self.assertEqual(
            compile_result.returncode,
            0,
            msg=f"compile failed\nstdout={compile_result.stdout}\nstderr={compile_result.stderr}",
        )

        score_input_path = tmpdir / "score_input.json"
        evidence_path = tmpdir / "packet/evidence/evidence.json"
        self._write_json(score_input_path, self._make_score_payload(frame_count=len(frame_sizes)))
        score_result = self._run(
            [
                sys.executable,
                str(SCORE_SCRIPT),
                "--root",
                str(REPO_ROOT),
                "--input",
                str(score_input_path),
                "--output",
                str(evidence_path),
            ]
        )
        self.assertEqual(
            score_result.returncode,
            0,
            msg=f"score failed\nstdout={score_result.stdout}\nstderr={score_result.stderr}",
        )
        return manifest_path, evidence_path

    def _run_prepare(
        self,
        manifest_path: Path,
        evidence_path: Path,
        prerequisites_payload: dict[str, object],
        out_dir: Path,
    ) -> subprocess.CompletedProcess[str]:
        prerequisites_path = out_dir.parent / "prerequisites.json"
        self._write_json(prerequisites_path, prerequisites_payload)
        return self._run(
            [
                sys.executable,
                str(PREP_SCRIPT),
                "--root",
                str(REPO_ROOT),
                "--manifest",
                str(manifest_path),
                "--evidence",
                str(evidence_path),
                "--prerequisites",
                str(prerequisites_path),
                "--out-dir",
                str(out_dir),
            ]
        )

    def _build_valid_case(
        self, tmpdir: Path, frame_sizes: list[tuple[int, int]]
    ) -> tuple[Path, Path, dict[str, object]]:
        manifest_path, evidence_path = self._create_strict_manifest_and_evidence(
            tmpdir=tmpdir,
            frame_sizes=frame_sizes,
        )
        manifest_payload = self._load_json(manifest_path)
        sequence_sha256 = str(manifest_payload["sequence_sha256"])
        prerequisites = self._base_prerequisites(
            base_dir=tmpdir,
            sequence_sha256=sequence_sha256,
        )
        return manifest_path, evidence_path, prerequisites

    def test_valid_preview_generation_and_packet_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(48, 48), (48, 48), (48, 48)]
            )
            out_dir = tmpdir / "out"
            result = self._run_prepare(manifest, evidence, prerequisites, out_dir)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            packet_path = out_dir / "visual_review_packet.json"
            self.assertTrue(packet_path.exists())
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["status"], "ready_for_visual_review")
            self.assertTrue(packet["review_assets_ready"])
            self.assertTrue(packet["prerequisites_complete"])
            self.assertFalse(packet["visual_review_complete"])
            self.assertFalse(packet["final_temporal_visual_pass"])
            self.assertFalse(packet["final_acceptance_claimed"])
            self.assertEqual(packet["decision_scope"], "review_preparation_only")
            self.assertTrue(packet["prerequisite_evidence_results"])
            self.assertEqual(len(packet["frames"]), 3)
            self.assertEqual(packet["frames"][0]["adjacent_next_index"], 1)
            self.assertAlmostEqual(
                packet["frames"][0]["adjacent_next_time_delta_seconds"],
                0.05,
                places=6,
            )
            self.assertIsNone(packet["frames"][-1]["adjacent_next_index"])
            self.assertIsNone(packet["frames"][-1]["adjacent_next_time_delta_seconds"])
            self.assertEqual(packet["preview_artifacts"]["review_playback_gif"]["durations_ms"], [50, 50, 50])

    def test_single_frame_preview_uses_default_duration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(48, 48)]
            )
            out_dir = tmpdir / "out"
            result = self._run_prepare(manifest, evidence, prerequisites, out_dir)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            packet = self._load_json(out_dir / "visual_review_packet.json")
            self.assertEqual(len(packet["frames"]), 1)
            self.assertIsNone(packet["frames"][0]["adjacent_next_index"])
            self.assertIsNone(packet["frames"][0]["adjacent_next_time_delta_seconds"])
            self.assertEqual(
                packet["preview_artifacts"]["review_playback_gif"]["durations_ms"],
                [100],
            )

    def test_manifest_frame_count_mismatch_fails_cleanly_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(48, 48), (48, 48)]
            )
            manifest_payload = self._load_json(manifest)
            manifest_payload["frame_count"] = 3
            self._write_json(manifest, manifest_payload)

            out_dir = tmpdir / "out"
            result = self._run_prepare(manifest, evidence, prerequisites, out_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("manifest.frame_count must equal", result.stderr)
            self.assertFalse(out_dir.exists())

    def test_preview_hashes_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(64, 64), (64, 64)]
            )
            out_a = tmpdir / "out_a"
            out_b = tmpdir / "out_b"
            result_a = self._run_prepare(manifest, evidence, prerequisites, out_a)
            result_b = self._run_prepare(manifest, evidence, prerequisites, out_b)
            self.assertEqual(result_a.returncode, 0, msg=result_a.stderr)
            self.assertEqual(result_b.returncode, 0, msg=result_b.stderr)

            packet_a = json.loads((out_a / "visual_review_packet.json").read_text(encoding="utf-8"))
            packet_b = json.loads((out_b / "visual_review_packet.json").read_text(encoding="utf-8"))
            self.assertEqual(
                packet_a["preview_artifacts"]["frame_grid"]["sha256"],
                packet_b["preview_artifacts"]["frame_grid"]["sha256"],
            )
            self.assertEqual(
                packet_a["preview_artifacts"]["review_playback_gif"]["sha256"],
                packet_b["preview_artifacts"]["review_playback_gif"]["sha256"],
            )

    def test_detector_fail_result_blocks_with_exit_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(40, 40), (40, 40)]
            )
            manifest_payload = self._load_json(manifest)
            prerequisites["face_detector"] = self._write_prereq_evidence(
                base_dir=tmpdir,
                category="face_detector",
                sequence_sha256=str(manifest_payload["sequence_sha256"]),
                result="fail",
            )
            out_dir = tmpdir / "out"
            result = self._run_prepare(manifest, evidence, prerequisites, out_dir)
            self.assertEqual(result.returncode, 2, msg=result.stderr)

            packet = json.loads((out_dir / "visual_review_packet.json").read_text(encoding="utf-8"))
            self.assertEqual(packet["status"], "blocked_missing_prerequisites")
            self.assertFalse(packet["prerequisites_complete"])
            self.assertNotIn("face_detector", packet["missing_prerequisite_categories"])
            self.assertIn("face_detector", packet["failed_prerequisite_categories"])
            self.assertFalse(packet["final_temporal_visual_pass"])
            self.assertFalse(packet["final_acceptance_claimed"])

    def test_detector_failure_takes_precedence_over_recorded_visual_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(40, 40), (40, 40)]
            )
            sequence_sha = str(self._load_json(manifest)["sequence_sha256"])
            prerequisites["face_detector"] = self._write_prereq_evidence(
                base_dir=tmpdir,
                category="face_detector",
                sequence_sha256=sequence_sha,
                result="fail",
            )
            prerequisites["codex_visual_verdict"] = self._write_prereq_evidence(
                base_dir=tmpdir,
                category="codex_visual_verdict",
                sequence_sha256=sequence_sha,
                result="pass",
            )

            out_dir = tmpdir / "out"
            result = self._run_prepare(manifest, evidence, prerequisites, out_dir)
            self.assertEqual(result.returncode, 2, msg=result.stderr)
            packet = self._load_json(out_dir / "visual_review_packet.json")
            self.assertEqual(packet["status"], "blocked_missing_prerequisites")
            self.assertTrue(packet["visual_review_complete"])
            self.assertNotIn("face_detector", packet["missing_prerequisite_categories"])
            self.assertIn("face_detector", packet["failed_prerequisite_categories"])
            self.assertFalse(packet["final_temporal_visual_pass"])
            self.assertFalse(packet["final_acceptance_claimed"])

    def test_audio_not_required_allowed_only_when_audio_required_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(42, 42), (42, 42)]
            )
            prerequisites["audio_required"] = False
            prerequisites["audio_asset_evidence"] = {"status": "not_required", "reason": "no audio lane"}
            prerequisites["audio_timing_evidence"] = {"status": "not_required", "reason": "no audio lane"}
            result_ok = self._run_prepare(manifest, evidence, prerequisites, tmpdir / "out_ok")
            self.assertEqual(result_ok.returncode, 0, msg=result_ok.stderr)

            bad_prerequisites = dict(prerequisites)
            bad_prerequisites["audio_required"] = True
            bad_prerequisites["audio_asset_evidence"] = {
                "status": "not_required",
                "reason": "invalid when audio required",
            }
            bad_prerequisites["audio_timing_evidence"] = {
                "status": "not_required",
                "reason": "invalid when audio required",
            }
            bad_out = tmpdir / "out_bad"
            result_bad = self._run_prepare(manifest, evidence, bad_prerequisites, bad_out)
            self.assertEqual(result_bad.returncode, 1)
            self.assertFalse((bad_out / "frame_grid.png").exists())
            self.assertFalse((bad_out / "review_playback.gif").exists())
            self.assertFalse((bad_out / "visual_review_packet.json").exists())

    def test_tampered_or_missing_verified_evidence_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(38, 38), (38, 38)]
            )
            identity_rel = Path(str(prerequisites["identity_detector"]["path"]))
            identity_abs = tmpdir / identity_rel
            identity_abs.write_text('{"tampered":true}\n', encoding="utf-8")
            out_tampered = tmpdir / "out_tampered"
            tampered_result = self._run_prepare(manifest, evidence, prerequisites, out_tampered)
            self.assertEqual(tampered_result.returncode, 1)
            self.assertFalse((out_tampered / "frame_grid.png").exists())
            self.assertFalse((out_tampered / "review_playback.gif").exists())
            self.assertFalse((out_tampered / "visual_review_packet.json").exists())

            manifest2, evidence2, prerequisites2 = self._build_valid_case(
                tmpdir=tmpdir / "missing_case", frame_sizes=[(38, 38), (38, 38)]
            )
            face_rel = Path(str(prerequisites2["face_detector"]["path"]))
            face_abs = (tmpdir / "missing_case") / face_rel
            face_abs.unlink()
            out_missing = tmpdir / "out_missing"
            missing_result = self._run_prepare(manifest2, evidence2, prerequisites2, out_missing)
            self.assertEqual(missing_result.returncode, 1)
            self.assertFalse((out_missing / "frame_grid.png").exists())

    def test_verified_evidence_with_unknown_payload_key_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(38, 38), (38, 38)]
            )
            identity_ref = prerequisites["identity_detector"]
            identity_path = tmpdir / Path(str(identity_ref["path"]))
            identity_payload = self._load_json(identity_path)
            identity_payload["unexpected"] = True
            self._write_json(identity_path, identity_payload)
            identity_ref["sha256"] = _sha256(identity_path)

            out_dir = tmpdir / "out"
            result = self._run_prepare(manifest, evidence, prerequisites, out_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("must contain exactly keys", result.stderr)
            self.assertFalse(out_dir.exists())

    def test_undecodable_and_mismatched_images_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)

            undecodable_manifest, undecodable_evidence = self._create_strict_manifest_and_evidence(
                tmpdir=tmpdir / "undecodable",
                frame_sizes=[(32, 32), (32, 32)],
                undecodable=True,
            )
            sequence_sha = str(self._load_json(undecodable_manifest)["sequence_sha256"])
            prerequisites = self._base_prerequisites(tmpdir / "undecodable", sequence_sha)
            undecodable_out = tmpdir / "undecodable_out"
            undecodable_result = self._run_prepare(
                undecodable_manifest,
                undecodable_evidence,
                prerequisites,
                undecodable_out,
            )
            self.assertEqual(undecodable_result.returncode, 1)
            self.assertFalse((undecodable_out / "frame_grid.png").exists())

            mismatch_manifest, mismatch_evidence = self._create_strict_manifest_and_evidence(
                tmpdir=tmpdir / "mismatch",
                frame_sizes=[(32, 32), (40, 32)],
            )
            mismatch_sequence = str(self._load_json(mismatch_manifest)["sequence_sha256"])
            mismatch_prereq = self._base_prerequisites(tmpdir / "mismatch", mismatch_sequence)
            mismatch_out = tmpdir / "mismatch_out"
            mismatch_result = self._run_prepare(
                mismatch_manifest,
                mismatch_evidence,
                mismatch_prereq,
                mismatch_out,
            )
            self.assertEqual(mismatch_result.returncode, 1)
            self.assertFalse((mismatch_out / "visual_review_packet.json").exists())

    def test_wrong_evidence_type_and_sequence_hash_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(44, 44), (44, 44)]
            )
            seq = str(self._load_json(manifest)["sequence_sha256"])
            prerequisites["identity_detector"] = self._write_prereq_evidence(
                base_dir=tmpdir,
                category="identity_detector",
                sequence_sha256=seq,
                evidence_type="face_detector",
            )
            out_wrong_type = tmpdir / "out_wrong_type"
            wrong_type = self._run_prepare(manifest, evidence, prerequisites, out_wrong_type)
            self.assertEqual(wrong_type.returncode, 1)
            self.assertFalse((out_wrong_type / "visual_review_packet.json").exists())

            manifest2, evidence2, prerequisites2 = self._build_valid_case(
                tmpdir=tmpdir / "seq_mismatch", frame_sizes=[(44, 44), (44, 44)]
            )
            prerequisites2["face_detector"] = self._write_prereq_evidence(
                base_dir=tmpdir / "seq_mismatch",
                category="face_detector",
                sequence_sha256=str(self._load_json(manifest2)["sequence_sha256"]),
                sequence_override="f" * 64,
            )
            out_wrong_seq = tmpdir / "out_wrong_seq"
            wrong_seq = self._run_prepare(manifest2, evidence2, prerequisites2, out_wrong_seq)
            self.assertEqual(wrong_seq.returncode, 1)
            self.assertFalse((out_wrong_seq / "visual_review_packet.json").exists())

    def test_codex_verdict_verified_results_mark_visual_review_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for verdict in ("pass", "fail", "blocked"):
                tmpdir = Path(tmp) / verdict
                manifest, evidence, prerequisites = self._build_valid_case(
                    tmpdir=tmpdir, frame_sizes=[(44, 44), (44, 44)]
                )
                sequence_sha = str(self._load_json(manifest)["sequence_sha256"])
                prerequisites["codex_visual_verdict"] = self._write_prereq_evidence(
                    base_dir=tmpdir,
                    category="codex_visual_verdict",
                    sequence_sha256=sequence_sha,
                    result=verdict,
                )
                out_dir = tmpdir / "out"
                result = self._run_prepare(manifest, evidence, prerequisites, out_dir)
                self.assertEqual(result.returncode, 0, msg=f"{verdict} stderr={result.stderr}")
                packet = self._load_json(out_dir / "visual_review_packet.json")
                self.assertEqual(packet["status"], "visual_review_recorded_pending_codex_authority")
                self.assertTrue(packet["visual_review_complete"])
                self.assertFalse(packet["final_temporal_visual_pass"])
                self.assertFalse(packet["final_acceptance_claimed"])

    def test_preexisting_nonempty_out_dir_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(32, 32), (32, 32)]
            )
            out_dir = tmpdir / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "already.txt").write_text("occupied\n", encoding="utf-8")
            result = self._run_prepare(manifest, evidence, prerequisites, out_dir)
            self.assertEqual(result.returncode, 1)
            self.assertFalse((out_dir / "visual_review_packet.json").exists())

    def test_transactional_cleanup_when_output_path_is_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(64, 64), (64, 64)]
            )
            out_path = tmpdir / "out"
            out_path.write_text("conflict\n", encoding="utf-8")
            result = self._run_prepare(manifest, evidence, prerequisites, out_path)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(out_path.is_file())
            staging_dirs = list(tmpdir.glob(".out.staging-*"))
            self.assertEqual(staging_dirs, [])

    def test_nested_output_parent_is_created_transactionally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir / "case", frame_sizes=[(48, 48), (48, 48)]
            )
            prerequisites_path = tmpdir / "case" / "prerequisites.json"
            self._write_json(prerequisites_path, prerequisites)
            out_dir = tmpdir / "fresh" / "nested" / "out"
            result = self._run(
                [
                    sys.executable,
                    str(PREP_SCRIPT),
                    "--root",
                    str(REPO_ROOT),
                    "--manifest",
                    str(manifest),
                    "--evidence",
                    str(evidence),
                    "--prerequisites",
                    str(prerequisites_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((out_dir / "visual_review_packet.json").is_file())
            self.assertTrue((out_dir / "frame_grid.png").is_file())
            self.assertTrue((out_dir / "review_playback.gif").is_file())
            self.assertEqual(list(out_dir.parent.glob(".out.staging-*")), [])

    def test_preview_downscale_preserves_original_dimensions_in_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, evidence, prerequisites = self._build_valid_case(
                tmpdir=tmpdir, frame_sizes=[(1600, 1200), (1600, 1200)]
            )
            out_dir = tmpdir / "out"
            result = self._run_prepare(manifest, evidence, prerequisites, out_dir)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            packet = self._load_json(out_dir / "visual_review_packet.json")
            self.assertEqual(packet["frames"][0]["image_width"], 1600)
            self.assertEqual(packet["frames"][0]["image_height"], 1200)
            with Image.open(out_dir / "review_playback.gif") as gif:
                self.assertLessEqual(max(gif.size), 960)
            with Image.open(out_dir / "frame_grid.png") as grid:
                self.assertLessEqual(max(grid.size), 960 * 4)


if __name__ == "__main__":
    unittest.main()
