#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import wave
from array import array
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave30_deterministic_audio_mix.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/wave30_audio_mix_manifest.schema.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_wav(path: Path, samples: list[int], rate: int = 16000, channels: int = 1) -> None:
    data = array("h", samples)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels); wav.setsampwidth(2); wav.setframerate(rate); wav.writeframes(data.tobytes())


class DeterministicAudioMixTests(unittest.TestCase):
    def packet(self, base: Path, *, rates: tuple[int, int] = (16000, 16000), loud: bool = False) -> Path:
        base.mkdir(parents=True, exist_ok=True)
        paths = [base / "a.wav", base / "b.wav"]
        amplitude = 32767 if loud else 1000
        write_wav(paths[0], [amplitude] * (rates[0] // 4), rates[0])
        write_wav(paths[1], [500] * (rates[1] // 4), rates[1])
        events = []
        for i, (path, rate, kind, layer) in enumerate(zip(paths, rates, ("dialogue", "ambience"), ("dialogue", "ambience"))):
            events.append({
                "audio_event_id": f"e{i}", "scene_id": "scene", "shot_id": "shot", "event_type": kind,
                "sync_class": "frame_exact" if i == 0 else "ambient_free", "purpose": "test", "source_event_id": f"s{i}",
                "start_seconds": i * 0.25, "end_seconds": (i + 1) * 0.25,
                "expected_video_frame_range": {"start_frame": i * 6, "end_frame": (i + 1) * 6, "frame_rate": 24.0},
                "qa_rules": ["decode"], "layer": layer, "routing": {"bus": layer},
                "subject_binding": {"binding_type": "character", "character_id": "c"} if kind == "dialogue" else {"binding_type": "environment"},
                "artifact": {"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size,
                             "duration_seconds": 0.25, "sample_rate_hz": rate, "channels": 1,
                             "sample_width_bytes": 2, "frame_count": rate // 4},
                "synthetic_state": {"synthetic_origin": "test", "production_proof_claimed": False},
            })
        manifest = {"$schema": "https://json-schema.org/draft/2020-12/schema", "schema_name": "wave30_audio_event_manifest",
                    "event_manifest_version": 1, "run_id": "run", "scene_id": "scene", "shot_id": "shot",
                    "is_synthetic": True, "production_proof": {"runtime_proof_present": False, "audio_review_present": False, "certified_for_release": False},
                    "taxonomy_registry_path": "registry", "taxonomy_registry_sha256": "0" * 64, "audio_event_count": 2,
                    "required_lanes": ["dialogue", "ambience"], "audio_events": events,
                    "artifact_manifest": {"source_input_path": "input", "source_input_sha256": "1" * 64},
                    "av_sync_binding": {"frame_rate": 24.0, "sync_scope": "event_level"}}
        path = base / "event_manifest.json"; path.write_text(json.dumps(manifest), encoding="utf-8"); return path

    def run_builder(self, event: Path, out: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(ROOT), "--event-manifest", str(event), "--output-dir", str(out)], cwd=ROOT, text=True, capture_output=True)

    def test_builds_schema_valid_blocked_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); event = self.packet(base); out = base / "out"
            result = self.run_builder(event, out); self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((out / "mix_manifest.json").read_text())
            Draft202012Validator(json.loads(SCHEMA.read_text())).validate(manifest)
            self.assertEqual(manifest["mix_technical"]["frame_count"], 8000)
            self.assertFalse(manifest["production_state"]["runtime_proof_present"])
            self.assertEqual(manifest["promotion_decision"], "block")
            self.assertTrue((out / "mixdown.wav").is_file())
            self.assertTrue(Path(manifest["mixdown_artifact"]["path"]).is_file())
            self.assertTrue(Path(manifest["runtime_proof"]["path"]).is_file())
            self.assertTrue(Path(manifest["audio_review"]["path"]).is_file())

    def test_mixdown_bytes_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); event = self.packet(base)
            self.assertEqual(self.run_builder(event, base / "one").returncode, 0)
            self.assertEqual(self.run_builder(event, base / "two").returncode, 0)
            self.assertEqual((base / "one/mixdown.wav").read_bytes(), (base / "two/mixdown.wav").read_bytes())

    def test_rejects_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); event = self.packet(base); payload = json.loads(event.read_text())
            payload["audio_events"][0]["artifact"]["sha256"] = "f" * 64; event.write_text(json.dumps(payload))
            result = self.run_builder(event, base / "out"); self.assertEqual(result.returncode, 2); self.assertFalse((base / "out").exists())

    def test_rejects_mixed_sample_rates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); result = self.run_builder(self.packet(base, rates=(16000, 8000)), base / "out")
            self.assertEqual(result.returncode, 2); self.assertIn("share one sample rate", result.stderr)

    def test_rejects_clipping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); event = self.packet(base, loud=True); payload = json.loads(event.read_text())
            second_path = Path(payload["audio_events"][1]["artifact"]["path"])
            write_wav(second_path, [32767] * 4000)
            payload["audio_events"][1]["artifact"]["sha256"] = sha(second_path)
            payload["audio_events"][1]["artifact"]["bytes"] = second_path.stat().st_size
            payload["audio_events"][1]["event_type"] = "dialogue"
            payload["audio_events"][1]["layer"] = "dialogue"
            payload["audio_events"][1]["subject_binding"] = {"binding_type": "character", "character_id": "c2"}
            payload["audio_events"][1]["start_seconds"] = 0.0; payload["audio_events"][1]["end_seconds"] = 0.25
            payload["audio_events"][1]["expected_video_frame_range"] = {"start_frame": 0, "end_frame": 6, "frame_rate": 24.0}
            event.write_text(json.dumps(payload)); result = self.run_builder(event, base / "out")
            self.assertEqual(result.returncode, 2); self.assertIn("clip", result.stderr)

    def test_existing_output_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); out = base / "out"; out.mkdir(); marker = out / "keep"; marker.write_text("yes")
            result = self.run_builder(self.packet(base), out); self.assertEqual(result.returncode, 2); self.assertEqual(marker.read_text(), "yes")

    def test_rejects_certified_input_and_short_event_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); event = self.packet(base); payload = json.loads(event.read_text())
            payload["production_proof"]["certified_for_release"] = True; event.write_text(json.dumps(payload))
            self.assertEqual(self.run_builder(event, base / "certified").returncode, 2)

            event = self.packet(base / "fresh"); payload = json.loads(event.read_text())
            payload["audio_events"][0]["end_seconds"] = 0.249
            payload["audio_events"][0]["expected_video_frame_range"]["end_frame"] = 6
            event.write_text(json.dumps(payload))
            result = self.run_builder(event, base / "drift")
            self.assertEqual(result.returncode, 2); self.assertIn("timing mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
