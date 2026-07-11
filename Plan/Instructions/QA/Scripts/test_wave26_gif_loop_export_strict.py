#!/usr/bin/env python3
from __future__ import annotations

import binascii
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[4]
COMPILE_SCRIPT = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave27_frame_manifest.py"
SCORE_SCRIPT = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/score_wave27_temporal_evidence.py"
CERTIFY_SCRIPT = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/certify_wave26_gif_loop_export.py"
SCHEMA_PATH = REPO_ROOT / "Plan/08_SCHEMAS/wave26_gif_loop_export_evidence.schema.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_png(path: Path, width: int, height: int, seed: int) -> None:
    if width <= 0 or height <= 0:
        raise ValueError("PNG width/height must be positive")
    raw_rows = bytearray()
    for y in range(height):
        raw_rows.append(0)
        for x in range(width):
            r = (seed + (x * 7) + (y * 11)) % 256
            g = (seed + 31 + (x * 13) + (y * 17)) % 256
            b = (seed + 67 + (x * 19) + (y * 23)) % 256
            raw_rows.extend((r, g, b))
    compressed = zlib.compress(bytes(raw_rows), level=9)

    def _chunk(chunk_type: bytes, payload: bytes) -> bytes:
        crc = binascii.crc32(chunk_type + payload) & 0xFFFFFFFF
        return len(payload).to_bytes(4, "big") + chunk_type + payload + crc.to_bytes(4, "big")

    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + bytes([8, 2, 0, 0, 0])
    )
    data = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", compressed) + _chunk(
        b"IEND", b""
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _build_gif(
    path: Path,
    width: int,
    height: int,
    durations_ms: list[int],
    loop_count: int,
) -> None:
    if not durations_ms:
        raise ValueError("GIF must include at least one frame")
    frames: list[Image.Image] = []
    for idx, _duration in enumerate(durations_ms):
        rgba = Image.new(
            "RGBA",
            (width, height),
            (
                (idx * 53) % 255,
                (idx * 83 + 40) % 255,
                (idx * 29 + 80) % 255,
                255,
            ),
        )
        frames.append(rgba)
    palette_frames = [frame.convert("P", palette=Image.ADAPTIVE) for frame in frames]
    path.parent.mkdir(parents=True, exist_ok=True)
    palette_frames[0].save(
        path,
        save_all=True,
        append_images=palette_frames[1:],
        loop=loop_count,
        duration=durations_ms,
        optimize=False,
    )


class Wave26GifLoopExportStrictTests(unittest.TestCase):
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
            "shot_id": "shot_wave26",
            "visible_characters": ["char_a"],
            "camera_state": {"resolution": "1x1", "lens": "35mm"},
            "qa_scores": {
                "identity_drift_score": 2.0,
                "flicker_score": 3.0,
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

    def _build_manifest_and_evidence(
        self,
        tmpdir: Path,
        frame_count: int = 3,
        loop_profile: str = "seamless_cycle",
        width: int = 1,
        height: int = 1,
    ) -> tuple[Path, Path]:
        inputs: list[Path] = []
        for idx in range(frame_count):
            frame_path = tmpdir / "frames" / f"f_{idx:03d}.png"
            _write_png(frame_path, width=width, height=height, seed=idx + 1)
            payload = self._frame_record(idx, frame_path)
            record_path = tmpdir / "inputs" / f"r_{idx:03d}.json"
            self._write_json(record_path, payload)
            inputs.append(record_path)

        manifest_path = tmpdir / "packet" / "manifest.json"
        compile_cmd = [sys.executable, str(COMPILE_SCRIPT), "--input"] + [str(p) for p in inputs] + [
            "--output",
            str(manifest_path),
        ]
        compile_result = self._run(compile_cmd)
        self.assertEqual(compile_result.returncode, 0, compile_result.stderr)

        evidence_input = tmpdir / "packet" / "evidence_input.json"
        self._write_json(
            evidence_input,
            {
                "run_id": "wave26_gif_test",
                "engine_name": "ltxv",
                "frame_count": frame_count,
                "loop_profile": loop_profile,
                "identity_drift_score": 3.0,
                "flicker_score": 4.0,
                "pose_continuity_score": 95.0,
                "depth_continuity_score": 95.0,
                "contact_continuity_score": 95.0,
                "export_integrity_score": 95.0,
                "hard_failures": [],
                "repair_events": [],
            },
        )
        evidence_path = tmpdir / "packet" / "temporal_evidence.json"
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
        return manifest_path, evidence_path

    def _write_bound_proofs(
        self,
        manifest_path: Path,
        temporal_path: Path,
        candidate_gif: Path,
        output_dir: Path,
        *,
        runtime_binding_sha_override: str | None = None,
        visual_binding_sha_override: str | None = None,
        runtime_attestation_sha_override: str | None = None,
        visual_attestation_sha_override: str | None = None,
    ) -> dict[str, Any]:
        candidate_sha = _sha256(candidate_gif)
        manifest_sha = _sha256(manifest_path)
        temporal_sha = _sha256(temporal_path)

        runtime_payload = {
            "runtime_ready": True,
            "runtime_proof_present": True,
            "generation_executed": True,
            "production_proof": True,
            "candidate_gif_sha256": runtime_binding_sha_override or candidate_sha,
            "manifest_sha256": manifest_sha,
            "temporal_evidence_sha256": temporal_sha,
        }
        runtime_path = output_dir / "runtime_proof.json"
        self._write_json(runtime_path, runtime_payload)
        runtime_sha = _sha256(runtime_path)

        visual_payload = {
            "review_method": "loop_playback_review",
            "no_visible_pop_passed": True,
            "intentional_cadence_passed": True,
            "identity_preservation_passed": True,
            "background_continuity_passed": True,
            "contact_deformation_continuity": "ping_pong_compatible",
            "candidate_gif_sha256": visual_binding_sha_override or candidate_sha,
            "manifest_sha256": manifest_sha,
            "temporal_evidence_sha256": temporal_sha,
        }
        visual_path = output_dir / "visual_review.json"
        self._write_json(visual_path, visual_payload)
        visual_sha = _sha256(visual_path)

        return {
            "synthetic_input": False,
            "runtime_proof_path": str(runtime_path),
            "runtime_proof_sha256": runtime_attestation_sha_override or runtime_sha,
            "visual_review_path": str(visual_path),
            "visual_review_sha256": visual_attestation_sha_override or visual_sha,
        }

    def _run_certifier(
        self,
        manifest_path: Path,
        evidence_path: Path,
        candidate_gif: Path,
        output_path: Path,
        attestation: dict[str, Any] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        cmd = [
            sys.executable,
            str(CERTIFY_SCRIPT),
            "--root",
            str(REPO_ROOT),
            "--manifest",
            str(manifest_path),
            "--temporal-evidence",
            str(evidence_path),
            "--candidate-gif",
            str(candidate_gif),
            "--output",
            str(output_path),
        ]
        if attestation is not None:
            attestation_path = output_path.parent / "attestation.json"
            self._write_json(attestation_path, attestation)
            cmd.extend(["--attestation", str(attestation_path)])
        return self._run(cmd)

    def _validate_schema(self, evidence_path: Path) -> dict[str, Any]:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(evidence)
        return evidence

    def test_positive_synthetic_technical_verification_is_blocked_by_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, temporal = self._build_manifest_and_evidence(tmpdir, frame_count=3)
            gif_path = tmpdir / "cand" / "ok.gif"
            _build_gif(gif_path, width=1, height=1, durations_ms=[40, 40, 40], loop_count=0)
            output = tmpdir / "out" / "evidence.json"
            result = self._run_certifier(manifest, temporal, gif_path, output)
            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = self._validate_schema(output)
            self.assertTrue(evidence["technical_checks"]["technical_passed"])
            self.assertTrue(evidence["decision"]["blocked"])
            self.assertIn("runtime_proof_absent", evidence["decision"]["blocker_codes"])
            self.assertIn("visual_playback_review_absent_or_failed", evidence["decision"]["blocker_codes"])
            self.assertFalse(evidence["decision"]["final_export_passed"])

    def test_missing_candidate_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, temporal = self._build_manifest_and_evidence(tmpdir, frame_count=3)
            output = tmpdir / "out" / "evidence.json"
            result = self._run_certifier(manifest, temporal, tmpdir / "none.gif", output)
            self.assertEqual(result.returncode, 2)
            evidence = self._validate_schema(output)
            self.assertIn("candidate_missing", evidence["decision"]["blocker_codes"])

    def test_invalid_gif_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, temporal = self._build_manifest_and_evidence(tmpdir, frame_count=2)
            bad_gif = tmpdir / "cand" / "bad.gif"
            _build_gif(bad_gif, width=1, height=1, durations_ms=[40, 40], loop_count=0)
            broken = bytearray(bad_gif.read_bytes())
            broken[-1] = 0x00
            bad_gif.write_bytes(bytes(broken))
            output = tmpdir / "o.json"
            result = self._run_certifier(manifest, temporal, bad_gif, output)
            self.assertEqual(result.returncode, 2)
            evidence = self._validate_schema(output)
            self.assertIn("candidate_decode_failed", evidence["decision"]["blocker_codes"])

    def test_unknown_profile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, temporal = self._build_manifest_and_evidence(tmpdir, frame_count=2)
            payload = json.loads(temporal.read_text(encoding="utf-8"))
            payload["loop_profile"] = "unknown_profile"
            temporal.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            gif_path = tmpdir / "cand" / "ok.gif"
            _build_gif(gif_path, width=1, height=1, durations_ms=[40, 40], loop_count=0)
            output = tmpdir / "o.json"
            result = self._run_certifier(manifest, temporal, gif_path, output)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.exists())

    def test_tampered_source_hash_binding_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, temporal = self._build_manifest_and_evidence(tmpdir, frame_count=3)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["frames"][1]["artifact_sha256"] = "0" * 64
            manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            gif_path = tmpdir / "cand" / "ok.gif"
            _build_gif(gif_path, width=1, height=1, durations_ms=[40, 40, 40], loop_count=0)
            output = tmpdir / "o.json"
            result = self._run_certifier(manifest, temporal, gif_path, output)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.exists())

    def test_frame_count_duration_and_loop_mismatch_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, temporal = self._build_manifest_and_evidence(tmpdir, frame_count=3)
            mismatch_gif = tmpdir / "cand" / "mismatch.gif"
            _build_gif(mismatch_gif, width=1, height=1, durations_ms=[40, 80], loop_count=1)
            output = tmpdir / "o.json"
            result = self._run_certifier(manifest, temporal, mismatch_gif, output)
            self.assertEqual(result.returncode, 2)
            evidence = self._validate_schema(output)
            blockers = set(evidence["decision"]["blocker_codes"])
            self.assertIn("frame_count_mismatch", blockers)
            self.assertIn("duration_mismatch", blockers)
            self.assertIn("loop_count_mismatch", blockers)

    def test_dimension_mismatch_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, temporal = self._build_manifest_and_evidence(
                tmpdir, frame_count=3, width=2, height=2
            )
            gif_path = tmpdir / "cand" / "wrong_dims.gif"
            _build_gif(gif_path, width=1, height=1, durations_ms=[40, 40, 40], loop_count=0)
            output = tmpdir / "o.json"
            result = self._run_certifier(manifest, temporal, gif_path, output)
            self.assertEqual(result.returncode, 2)
            evidence = self._validate_schema(output)
            self.assertIn("dimension_mismatch", evidence["decision"]["blocker_codes"])

    def test_invalid_lzw_payload_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, temporal = self._build_manifest_and_evidence(tmpdir, frame_count=2)
            gif_path = tmpdir / "cand" / "corrupt_lzw.gif"
            _build_gif(gif_path, width=1, height=1, durations_ms=[40, 40], loop_count=0)
            data = bytearray(gif_path.read_bytes())
            image_sep = data.find(b"\x2C")
            self.assertNotEqual(image_sep, -1)
            lzw_min_code_offset = image_sep + 10
            data[lzw_min_code_offset] = 0x00
            gif_path.write_bytes(bytes(data))
            output = tmpdir / "o.json"
            result = self._run_certifier(manifest, temporal, gif_path, output)
            self.assertEqual(result.returncode, 2)
            evidence = self._validate_schema(output)
            self.assertIn("candidate_decode_failed", evidence["decision"]["blocker_codes"])

    def test_synthetic_cannot_assert_runtime_or_visual_proof_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, temporal = self._build_manifest_and_evidence(tmpdir, frame_count=3)
            gif_path = tmpdir / "cand" / "ok.gif"
            _build_gif(gif_path, width=1, height=1, durations_ms=[40, 40, 40], loop_count=0)
            output = tmpdir / "o.json"
            result = self._run_certifier(
                manifest,
                temporal,
                gif_path,
                output,
                attestation={
                    "synthetic_input": True,
                    "runtime_proof_path": str(tmpdir / "fake_runtime.json"),
                    "runtime_proof_sha256": "0" * 64,
                    "visual_review_path": str(tmpdir / "fake_visual.json"),
                    "visual_review_sha256": "1" * 64,
                },
            )
            self.assertEqual(result.returncode, 2)
            evidence = self._validate_schema(output)
            self.assertIn(
                "synthetic_input_cannot_claim_runtime_or_visual_proof",
                evidence["decision"]["blocker_codes"],
            )
            self.assertFalse(evidence["decision"]["final_export_passed"])
            self.assertFalse(evidence["runtime_proof"]["verified"])
            self.assertFalse(evidence["visual_review"]["verified"])

    def test_boolean_only_fake_proof_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, temporal = self._build_manifest_and_evidence(tmpdir, frame_count=2)
            gif_path = tmpdir / "cand" / "ok.gif"
            _build_gif(gif_path, width=1, height=1, durations_ms=[40, 40], loop_count=0)
            output = tmpdir / "o.json"
            result = self._run_certifier(
                manifest,
                temporal,
                gif_path,
                output,
                attestation={"synthetic_input": False},
            )
            self.assertEqual(result.returncode, 2)
            evidence = self._validate_schema(output)
            blockers = set(evidence["decision"]["blocker_codes"])
            self.assertIn("runtime_proof_absent", blockers)
            self.assertIn("visual_playback_review_absent_or_failed", blockers)

    def test_runtime_proof_hash_and_binding_mismatch_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, temporal = self._build_manifest_and_evidence(tmpdir, frame_count=2)
            gif_path = tmpdir / "cand" / "ok.gif"
            _build_gif(gif_path, width=1, height=1, durations_ms=[40, 40], loop_count=0)
            output = tmpdir / "o.json"
            attestation = self._write_bound_proofs(
                manifest,
                temporal,
                gif_path,
                output.parent,
                runtime_binding_sha_override="f" * 64,
                runtime_attestation_sha_override="0" * 64,
            )
            result = self._run_certifier(manifest, temporal, gif_path, output, attestation=attestation)
            self.assertEqual(result.returncode, 2)
            evidence = self._validate_schema(output)
            blockers = set(evidence["decision"]["blocker_codes"])
            self.assertIn("runtime_proof_hash_mismatch", blockers)
            self.assertIn("runtime_proof_binding_mismatch", blockers)
            self.assertFalse(evidence["runtime_proof"]["verified"])
            self.assertFalse(evidence["runtime_proof"]["runtime_ready"])
            self.assertFalse(evidence["runtime_proof"]["runtime_proof_present"])
            self.assertFalse(evidence["runtime_proof"]["generation_executed"])
            self.assertFalse(evidence["runtime_proof"]["production_proof"])

    def test_visual_proof_hash_and_binding_mismatch_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            manifest, temporal = self._build_manifest_and_evidence(tmpdir, frame_count=2)
            gif_path = tmpdir / "cand" / "ok.gif"
            _build_gif(gif_path, width=1, height=1, durations_ms=[40, 40], loop_count=0)
            output = tmpdir / "o.json"
            attestation = self._write_bound_proofs(
                manifest,
                temporal,
                gif_path,
                output.parent,
                visual_binding_sha_override="e" * 64,
                visual_attestation_sha_override="1" * 64,
            )
            result = self._run_certifier(manifest, temporal, gif_path, output, attestation=attestation)
            self.assertEqual(result.returncode, 2)
            evidence = self._validate_schema(output)
            blockers = set(evidence["decision"]["blocker_codes"])
            self.assertIn("visual_proof_hash_mismatch", blockers)
            self.assertIn("visual_proof_binding_mismatch", blockers)
            self.assertFalse(evidence["visual_review"]["verified"])
            self.assertFalse(evidence["visual_review"]["visual_loop_review_passed"])
            self.assertFalse(evidence["visual_review"]["no_visible_pop_passed"])
            self.assertFalse(evidence["visual_review"]["intentional_cadence_passed"])
            self.assertFalse(evidence["visual_review"]["identity_preservation_passed"])
            self.assertFalse(evidence["visual_review"]["background_continuity_passed"])
            self.assertFalse(evidence["visual_review"]["contact_deformation_continuity"])


if __name__ == "__main__":
    unittest.main()
