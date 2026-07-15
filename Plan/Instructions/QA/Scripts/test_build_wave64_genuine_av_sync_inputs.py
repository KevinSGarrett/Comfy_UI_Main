#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
import wave
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_genuine_av_sync_inputs.py"
SPEC = importlib.util.spec_from_file_location("build_wave64_genuine_av_sync_inputs", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_wav(path: Path, *, rate: int, channels: int, frames: int) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\0\0" * channels * frames)


class GenuineAvSyncInputBuilderTests(unittest.TestCase):
    def fixture(self, base: Path) -> Path:
        base.mkdir(parents=True)
        source_video = base / "source.mkv"
        mux = base / "mux.mkv"
        strict_audio = base / "strict.wav"
        foley = base / "foley.wav"
        ambience = base / "ambience.wav"
        source_video.write_bytes(b"source-video")
        mux.write_bytes(b"mux")
        write_wav(strict_audio, rate=16000, channels=1, frames=32640)
        write_wav(foley, rate=48000, channels=2, frames=97920)
        write_wav(ambience, rate=48000, channels=2, frames=97920)

        def output(path: Path) -> dict[str, object]:
            return {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}

        manifest = {
            "is_synthetic": False,
            "promotion_claimed": False,
            "run_id": "run",
            "scene_id": "scene",
            "shot_id": "shot",
            "take_id": "take",
            "outputs": {
                "strict_source_video": output(source_video),
                "strict_sync_audio": output(strict_audio),
                "strict_sync_mux": output(mux),
                "foley_stem": output(foley),
                "ambience_stem": output(ambience),
            },
            "pcm_technical": {
                "strict_sync_audio": MODULE.wav_metrics(strict_audio),
                "foley_stem": MODULE.wav_metrics(foley),
                "ambience_stem": MODULE.wav_metrics(ambience),
            },
            "sync": {"video_frame_rate": 24.0, "foley_anchor_frame": 26, "foley_anchor_seconds": 1.08},
        }
        path = base / "delivery_manifest.json"
        path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        return path

    def test_builds_schema_valid_fail_closed_inputs(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            base = Path(temporary)
            manifest = self.fixture(base / "source")
            output = base / "result"
            result = MODULE.build_inputs(
                root=ROOT,
                delivery_manifest_path=manifest,
                output_dir=output,
                loudness_override={"integrated_lufs": -18.2, "true_peak_dbtp": -3.1},
            )
            event = json.loads((output / "wave30_event_manifest.json").read_text(encoding="utf-8"))
            mix = json.loads((output / "wave30_mix_manifest.json").read_text(encoding="utf-8"))
            anchor = json.loads((output / "anchor_measurement_proof.json").read_text(encoding="utf-8"))
            event_schema = json.loads((ROOT / MODULE.EVENT_SCHEMA).read_text(encoding="utf-8"))
            mix_schema = json.loads((ROOT / MODULE.MIX_SCHEMA).read_text(encoding="utf-8"))
            Draft202012Validator(event_schema).validate(event)
            Draft202012Validator(mix_schema).validate(mix)
            self.assertEqual(
                result["classification"],
                "GENUINE_AV_SYNC_TECHNICAL_INPUTS_BUILT_CONTACT_ANCHOR_AUTHORITY_BLOCKED",
            )
            self.assertEqual(anchor["anchors"], [])
            self.assertEqual(event["audio_events"][0]["subject_binding"]["binding_type"], "none")
            self.assertEqual(event["audio_events"][0]["sync_class"], "ambient_free")
            self.assertEqual(event["audio_events"][0]["event_type"], "room_tone")
            self.assertFalse(mix["production_state"]["certified_for_release"])
            self.assertFalse(result["boundaries"]["independent_playback_review_present"])
            self.assertFalse(result["boundaries"]["ownerless_sync_anchor_allowed_by_schema"])

    def test_rejects_hash_mismatch_and_output_clobber(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            base = Path(temporary)
            manifest = self.fixture(base / "source")
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["outputs"]["strict_sync_mux"]["sha256"] = "0" * 64
            manifest.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                MODULE.build_inputs(
                    root=ROOT,
                    delivery_manifest_path=manifest,
                    output_dir=base / "bad",
                    loudness_override={"integrated_lufs": -18.0, "true_peak_dbtp": -3.0},
                )
            manifest = self.fixture(base / "second")
            output = base / "existing"
            output.mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                MODULE.build_inputs(
                    root=ROOT,
                    delivery_manifest_path=manifest,
                    output_dir=output,
                    loudness_override={"integrated_lufs": -18.0, "true_peak_dbtp": -3.0},
                )

    def test_rejects_synthetic_or_inconsistent_anchor(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            base = Path(temporary)
            manifest = self.fixture(base / "source")
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["is_synthetic"] = True
            manifest.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-synthetic"):
                MODULE.build_inputs(
                    root=ROOT,
                    delivery_manifest_path=manifest,
                    output_dir=base / "synthetic",
                    loudness_override={"integrated_lufs": -18.0, "true_peak_dbtp": -3.0},
                )
            manifest = self.fixture(base / "second")
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["sync"]["foley_anchor_seconds"] = 0.1
            manifest.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frame/time"):
                MODULE.build_inputs(
                    root=ROOT,
                    delivery_manifest_path=manifest,
                    output_dir=base / "bad-anchor",
                    loudness_override={"integrated_lufs": -18.0, "true_peak_dbtp": -3.0},
                )

    def test_parses_ffmpeg_loudnorm_json(self) -> None:
        stderr = 'prefix {\n"input_i" : "-18.42",\n"input_tp" : "-3.27"\n} suffix'
        self.assertEqual(
            MODULE.parse_loudnorm(stderr),
            {"integrated_lufs": -18.42, "true_peak_dbtp": -3.27},
        )

    def test_hash_binds_explicit_final_mux_override(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            base = Path(temporary)
            manifest = self.fixture(base / "source")
            override = base / "frame-aligned.mkv"
            override.write_bytes(b"frame-aligned-mux")
            output = base / "result"
            result = MODULE.build_inputs(
                root=ROOT,
                delivery_manifest_path=manifest,
                output_dir=output,
                final_mux_override=override,
                loudness_override={"integrated_lufs": -18.0, "true_peak_dbtp": -3.0},
            )
            anchor = json.loads((output / "anchor_measurement_proof.json").read_text(encoding="utf-8"))
            self.assertTrue(result["final_mux_override_used"])
            self.assertEqual(result["verified_artifacts"]["mux_sha256"], sha256(override))
            self.assertEqual(anchor["mux_sha256"], sha256(override))


if __name__ == "__main__":
    unittest.main()
