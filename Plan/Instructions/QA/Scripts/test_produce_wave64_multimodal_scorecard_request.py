#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_multimodal_scorecard_request.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/wave64_multimodal_scorecard_request.schema.json"


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


class MultimodalRequestProducerTests(unittest.TestCase):
    def build(self, base: Path, *, synthetic: bool = True) -> dict[str, Path]:
        base.mkdir(parents=True, exist_ok=True)
        lineage = {"run_id": "run_001", "scene_id": "scene_001", "shot_id": "shot_001", "take_id": "take_001", "is_synthetic": synthetic}
        paths = {
            "image_review": base / "image.json",
            "video_review": base / "video.json",
            "strict_audio_report": base / "strict_audio.json",
            "global_audio_report": base / "global_audio.json",
            "av_sync_report": base / "av_sync.json",
            "artifact_manifest": base / "manifest.json",
            "release_gate_decision": base / "release.json",
            "output": base / "request.json",
            "output_report": base / "report.json",
        }
        write_json(paths["image_review"], {"evidence_id": "ITEM-W64-033", "tracker_id": "TRK-W64-018", "item_id": "ITEM-W64-018", "lineage": lineage})
        write_json(paths["video_review"], {"evidence_id": "ITEM-W64-033", "tracker_id": "TRK-W64-021", "item_id": "ITEM-W64-021", "lineage": lineage})
        write_json(paths["strict_audio_report"], {"schema_name": "wave64_strict_audio_review_report", "run_id": "run_001", "is_synthetic": synthetic})
        write_json(paths["global_audio_report"], {"schema_name": "wave64_global_audio_review_report", "review_run_id": "run_001", "is_synthetic": synthetic})
        write_json(paths["av_sync_report"], {"schema_name": "wave64_av_sync_certification_report", **lineage})
        write_json(paths["artifact_manifest"], {"release_id": "release_001"})
        write_json(paths["release_gate_decision"], {"release_id": "release_001"})
        return paths

    def args(self, paths: dict[str, Path]) -> list[str]:
        result: list[str] = []
        for name in (
            "image_review", "video_review", "strict_audio_report", "global_audio_report",
            "av_sync_report", "artifact_manifest", "release_gate_decision",
        ):
            result.extend((f"--{name.replace('_', '-')}", str(paths[name])))
        result.extend((
            "--artifact-id", "ITEM-W64-033", "--run-id", "run_001", "--scene-id", "scene_001",
            "--shot-id", "shot_001", "--take-id", "take_001", "--generation-test-method", "strict_fixture",
            "--synthetic", "--authority-id", "fixture_auth", "--bundle-id", "fixture_bundle",
            "--caller-claimed-approval-decision", "approved", "--output-report", str(paths["output_report"]),
            "--output", str(paths["output"]), "--root", str(ROOT),
        ))
        return result

    def run_cli(self, paths: dict[str, Path], *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), *self.args(paths), *extra], cwd=ROOT, text=True, capture_output=True)

    def test_emits_schema_valid_request_with_exact_bindings(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build(Path(temporary))
            result = self.run_cli(paths)
            self.assertEqual(result.returncode, 0, result.stdout)
            request = json.loads(paths["output"].read_text(encoding="utf-8"))
            Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(request)
            self.assertTrue(request["is_synthetic"])
            self.assertEqual(request["production_authority_claim"]["authority_id"], "fixture_auth")

    def test_rejects_image_identity_and_lineage_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build(Path(temporary))
            image = json.loads(paths["image_review"].read_text())
            image["tracker_id"] = "wrong"
            write_json(paths["image_review"], image)
            self.assertEqual(self.run_cli(paths).returncode, 2)
            paths = self.build(Path(temporary) / "lineage")
            video = json.loads(paths["video_review"].read_text())
            video["lineage"]["shot_id"] = "wrong"
            write_json(paths["video_review"], video)
            self.assertEqual(self.run_cli(paths).returncode, 2)

    def test_rejects_audio_and_av_lineage_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build(Path(temporary))
            strict = json.loads(paths["strict_audio_report"].read_text())
            strict["run_id"] = "wrong"
            write_json(paths["strict_audio_report"], strict)
            self.assertEqual(self.run_cli(paths).returncode, 2)
            paths = self.build(Path(temporary) / "av")
            av = json.loads(paths["av_sync_report"].read_text())
            av["take_id"] = "wrong"
            write_json(paths["av_sync_report"], av)
            self.assertEqual(self.run_cli(paths).returncode, 2)

    def test_rejects_release_mismatch_duplicate_input_and_duplicate_key(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build(Path(temporary))
            write_json(paths["release_gate_decision"], {"release_id": "wrong"})
            self.assertEqual(self.run_cli(paths).returncode, 2)
            paths = self.build(Path(temporary) / "duplicate_input")
            paths["video_review"] = paths["image_review"]
            self.assertEqual(self.run_cli(paths).returncode, 2)
            paths = self.build(Path(temporary) / "duplicate_key")
            paths["strict_audio_report"].write_text('{"schema_name":"wave64_strict_audio_review_report","schema_name":"x"}', encoding="utf-8")
            self.assertEqual(self.run_cli(paths).returncode, 2)

    def test_rejects_output_collisions_without_clobbering(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build(Path(temporary))
            paths["output"].write_text("sentinel", encoding="utf-8")
            self.assertEqual(self.run_cli(paths).returncode, 2)
            self.assertEqual(paths["output"].read_text(), "sentinel")
            paths = self.build(Path(temporary) / "report")
            paths["output_report"].write_text("sentinel", encoding="utf-8")
            self.assertEqual(self.run_cli(paths).returncode, 2)

    def test_production_input_requires_exact_non_synthetic_authority(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build(Path(temporary))
            self.assertEqual(self.run_cli(paths, "--production-input").returncode, 2)
            paths = self.build(Path(temporary) / "non_synthetic", synthetic=False)
            args = self.args(paths)
            args.remove("--synthetic")
            result = subprocess.run([sys.executable, str(SCRIPT), *args, "--production-input"], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("exact production authority object is required", result.stdout)


if __name__ == "__main__":
    unittest.main()
