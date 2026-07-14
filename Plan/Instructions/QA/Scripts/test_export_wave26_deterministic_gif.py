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
from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parents[4]
EXPORTER = ROOT / "Plan/07_IMPLEMENTATION/scripts/export_wave26_deterministic_gif.py"
CERTIFIER = ROOT / "Plan/07_IMPLEMENTATION/scripts/certify_wave26_gif_loop_export.py"
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave27_frame_manifest.py"
SCORER = ROOT / "Plan/07_IMPLEMENTATION/scripts/score_wave27_temporal_evidence.py"
EXPORT_SCHEMA = ROOT / "Plan/08_SCHEMAS/wave26_deterministic_gif_export.schema.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh_sequence(manifest: dict[str, Any]) -> None:
    frames = sorted(manifest["frames"], key=lambda frame: frame["frame_index"])
    payload = [{"frame_index": frame["frame_index"], "time_seconds": float(frame["time_seconds"]), "artifact_path": frame["artifact_path"], "artifact_sha256": frame["artifact_sha256"], "artifact_bytes": frame["artifact_bytes"]} for frame in frames]
    manifest["sequence_sha256"] = hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


class DeterministicGifExporterTests(unittest.TestCase):
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

    def build_packet(
        self,
        frame_count: int = 4,
        *,
        alpha: bool = False,
        corrupt_frame: int | None = None,
        frame_interval_seconds: float = 0.04,
    ) -> tuple[Path, Path]:
        inputs: list[Path] = []
        first: np.ndarray | None = None
        for index in range(frame_count):
            path = self.work / "frames" / f"frame_{index:03d}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            if index == corrupt_frame:
                path.write_bytes(b"not-an-image")
            else:
                image = np.zeros((64, 96, 4 if alpha else 3), dtype=np.uint8)
                image[:] = (30, 40 + index * 20, 80, 255) if alpha else (30, 40 + index * 20, 80)
                cv2.circle(image, (20 + index * 10, 32), 12, (220, 100, 50, 255) if alpha else (220, 100, 50), -1)
                image[56:64, 84:96] = (12, 200, 44, 255) if alpha else (12, 200, 44)
                if alpha:
                    image[0:16, 0:20, 3] = 0
                    image[4:8, 28:34] = (1, 2, 3, 255)
                if index == 0:
                    first = image.copy()
                if index == frame_count - 1 and frame_count > 1:
                    image = first.copy()
                    image[30:34, 45:49, :3] = 90
                self.assertTrue(cv2.imwrite(str(path), image))
            record = {
                "frame_index": index,
                "time_seconds": round(index * frame_interval_seconds, 6),
                "source_route": "unit", "engine_name": "unit", "shot_id": "shot",
                "visible_characters": ["subject"], "camera_state": {"mode": "static"},
                "qa_scores": {}, "repair_status": "none", "artifact_path": str(path), "artifact_sha256": sha256(path),
            }
            record_path = self.work / "inputs" / f"frame_{index:03d}.json"
            self.write_json(record_path, record)
            inputs.append(record_path)
        manifest = self.work / "packet/manifest.json"
        compiled = self.run_cmd([sys.executable, str(COMPILER), "--input", *[str(path) for path in inputs], "--output", str(manifest)])
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        score_input = self.work / "packet/score_input.json"
        self.write_json(score_input, {"run_id": "gif_export_test", "engine_name": "ltxv", "frame_count": frame_count, "loop_profile": "seamless_cycle", "identity_drift_score": 4.0, "flicker_score": 5.0, "pose_continuity_score": 94.0, "depth_continuity_score": 93.0, "contact_continuity_score": 95.0, "export_integrity_score": 96.0, "hard_failures": [], "repair_events": []})
        evidence = self.work / "packet/temporal_evidence.json"
        scored = self.run_cmd([sys.executable, str(SCORER), "--root", str(ROOT), "--input", str(score_input), "--output", str(evidence)])
        self.assertEqual(scored.returncode, 0, scored.stderr)
        return manifest, evidence

    def export(self, manifest: Path, evidence: Path, output: Path) -> subprocess.CompletedProcess[str]:
        return self.run_cmd([sys.executable, str(EXPORTER), "--manifest", str(manifest), "--temporal-evidence", str(evidence), "--output-dir", str(output), "--root", str(ROOT)])

    def test_export_is_accepted_by_existing_certifier_as_technical_only(self) -> None:
        manifest, evidence = self.build_packet()
        output = self.work / "export"
        result = self.export(manifest, evidence, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        certification = self.work / "certification.json"
        certified = self.run_cmd([sys.executable, str(CERTIFIER), "--manifest", str(manifest), "--temporal-evidence", str(evidence), "--candidate-gif", str(output / "candidate.gif"), "--output", str(certification), "--root", str(ROOT)])
        self.assertEqual(certified.returncode, 2, certified.stderr)
        payload = json.loads(certification.read_text())
        self.assertTrue(payload["technical_checks"]["technical_passed"])
        self.assertFalse(payload["decision"]["final_export_passed"])

    def test_frame_count_dimensions_timing_and_loop_metadata_match(self) -> None:
        manifest, evidence = self.build_packet()
        output = self.work / "export"
        self.assertEqual(self.export(manifest, evidence, output).returncode, 0)
        with Image.open(output / "candidate.gif") as gif:
            frames = list(ImageSequence.Iterator(gif))
            self.assertEqual(len(frames), 4)
            self.assertEqual(gif.size, (96, 64))
            self.assertEqual(gif.info["loop"], 0)
            self.assertEqual([frame.info["duration"] for frame in frames], [40, 40, 40, 40])

    def test_24fps_timing_is_centisecond_quantized_and_certifier_compatible(self) -> None:
        manifest, evidence = self.build_packet(frame_count=13, frame_interval_seconds=1.0 / 24.0)
        output = self.work / "export"
        result = self.export(manifest, evidence, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = [40, 40, 50, 40, 40, 40, 40, 50, 40, 40, 40, 40, 50]
        with Image.open(output / "candidate.gif") as gif:
            self.assertEqual(
                [frame.info["duration"] for frame in ImageSequence.Iterator(gif)],
                expected,
            )
        certification = self.work / "certification.json"
        certified = self.run_cmd(
            [
                sys.executable,
                str(CERTIFIER),
                "--manifest",
                str(manifest),
                "--temporal-evidence",
                str(evidence),
                "--candidate-gif",
                str(output / "candidate.gif"),
                "--output",
                str(certification),
                "--root",
                str(ROOT),
            ]
        )
        self.assertEqual(certified.returncode, 2, certified.stderr)
        payload = json.loads(certification.read_text())
        self.assertNotIn("duration_mismatch", payload["decision"]["blocker_codes"])

    def test_export_manifest_is_schema_valid_and_claim_bounded(self) -> None:
        manifest, evidence = self.build_packet()
        output = self.work / "export"
        self.assertEqual(self.export(manifest, evidence, output).returncode, 0)
        payload = json.loads((output / "export_manifest.json").read_text())
        jsonschema.Draft202012Validator(json.loads(EXPORT_SCHEMA.read_text())).validate(payload)
        self.assertTrue(payload["claims"]["technical_gif_export_generated"])
        self.assertTrue(payload["claims"]["manifest_timing_applied"])
        self.assertTrue(all(value is False for key, value in payload["claims"].items() if key not in {"technical_gif_export_generated", "manifest_timing_applied"}))

    def test_repeat_export_is_byte_deterministic(self) -> None:
        manifest, evidence = self.build_packet()
        first, second = self.work / "first", self.work / "second"
        self.assertEqual(self.export(manifest, evidence, first).returncode, 0)
        self.assertEqual(self.export(manifest, evidence, second).returncode, 0)
        self.assertEqual((first / "candidate.gif").read_bytes(), (second / "candidate.gif").read_bytes())
        self.assertEqual((first / "export_manifest.json").read_bytes(), (second / "export_manifest.json").read_bytes())

    def test_alpha_transparency_is_preserved(self) -> None:
        manifest, evidence = self.build_packet(alpha=True)
        output = self.work / "export"
        result = self.export(manifest, evidence, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(output / "candidate.gif") as gif:
            rgba = gif.convert("RGBA")
            self.assertEqual(rgba.getpixel((2, 2))[3], 0)
            self.assertEqual(rgba.getpixel((50, 30))[3], 255)
            self.assertEqual(rgba.getpixel((30, 5))[3], 255)

    def test_static_source_color_decodes_consistently_across_frames(self) -> None:
        manifest, evidence = self.build_packet()
        output = self.work / "export"
        self.assertEqual(self.export(manifest, evidence, output).returncode, 0)
        with Image.open(output / "candidate.gif") as gif:
            colors = [frame.convert("RGB").getpixel((90, 60)) for frame in ImageSequence.Iterator(gif)]
            self.assertTrue(all(color == colors[0] for color in colors))

    def test_single_frame_manifest_uses_bounded_default_duration(self) -> None:
        manifest, evidence = self.build_packet(frame_count=1)
        output = self.work / "export"
        result = self.export(manifest, evidence, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(output / "candidate.gif") as gif:
            self.assertEqual(gif.n_frames, 1)
            self.assertEqual(gif.info["duration"], 100)

    def test_tampered_or_nondecodable_source_is_rejected(self) -> None:
        manifest, evidence = self.build_packet(corrupt_frame=2)
        result = self.export(manifest, evidence, self.work / "export")
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot be decoded", result.stderr)

    def test_tampered_bound_source_is_rejected(self) -> None:
        manifest, evidence = self.build_packet()
        source = Path(json.loads(manifest.read_text())["frames"][1]["artifact_path"])
        source.write_bytes(b"tampered")
        result = self.export(manifest, evidence, self.work / "export")
        self.assertEqual(result.returncode, 2)
        self.assertIn("source frame binding failed", result.stderr)

    def test_unknown_loop_profile_is_rejected(self) -> None:
        manifest, evidence = self.build_packet()
        payload = json.loads(evidence.read_text())
        payload["loop_profile"] = "unknown-profile"
        self.write_json(evidence, payload)
        result = self.export(manifest, evidence, self.work / "export")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown loop profile", result.stderr)

    def test_permuted_manifest_is_normalized_like_existing_certifier(self) -> None:
        manifest, evidence = self.build_packet()
        payload = json.loads(manifest.read_text())
        payload["frames"] = [payload["frames"][2], payload["frames"][0], payload["frames"][3], payload["frames"][1]]
        self.write_json(manifest, payload)
        output = self.work / "export"
        result = self.export(manifest, evidence, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(output / "candidate.gif") as gif:
            self.assertEqual(gif.n_frames, 4)

    def test_sub_centisecond_timing_fails_before_export(self) -> None:
        manifest, evidence = self.build_packet()
        payload = json.loads(manifest.read_text())
        for index, frame in enumerate(payload["frames"]):
            frame["time_seconds"] = index * 0.005
        refresh_sequence(payload)
        self.write_json(manifest, payload)
        result = self.export(manifest, evidence, self.work / "export")
        self.assertEqual(result.returncode, 2)
        self.assertIn("at least 10ms", result.stderr)

    def test_existing_output_is_preserved(self) -> None:
        manifest, evidence = self.build_packet()
        output = self.work / "export"
        output.mkdir()
        marker = output / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        result = self.export(manifest, evidence, output)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(marker.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
