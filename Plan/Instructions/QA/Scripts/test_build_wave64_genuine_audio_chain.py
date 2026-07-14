import importlib.util
import json
import math
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_genuine_audio_chain.py"
SPEC = importlib.util.spec_from_file_location("build_wave64_genuine_audio_chain", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class BuildWave64GenuineAudioChainTests(unittest.TestCase):
    def _args(self, base: Path):
        inputs = {}
        for name in ("ffmpeg", "source_video", "voice_source", "foley_source"):
            path = base / name
            path.write_bytes(b"fixture")
            inputs[name] = str(path)
        return SimpleNamespace(
            **inputs,
            output_dir=str(base / "output"),
            duration=2.04,
            voice_start=20.4,
            voice_end=21.8,
            voice_delay=0.22,
            foley_delay=1.08,
            run_id="run",
            scene_id="scene",
            shot_id="shot",
            take_id="take",
            voice_source_page="https://example.test/voice",
            voice_license="public domain",
            voice_license_url="https://example.test/license",
            voice_transcript="line",
            transcript_method="fixture",
            foley_source_page="https://example.test/foley",
            foley_license="CC0-1.0",
            foley_creator="creator",
            foley_pack_license="CC-BY-4.0",
            foley_pack_terms_path="F:/terms.pdf",
            foley_pack_terms_sha256="a" * 64,
            foley_attribution="SFX: Pack | creator",
        )

    def test_ambience_is_deterministic_stereo_pcm(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.wav"
            second = Path(temporary) / "second.wav"
            MODULE.write_ambience(first, 0.1)
            MODULE.write_ambience(second, 0.1)
            self.assertEqual(MODULE.sha256(first), MODULE.sha256(second))
            metadata = MODULE.inspect_pcm(first)
            self.assertEqual(metadata["sample_rate_hz"], 48000)
            self.assertEqual(metadata["channels"], 2)
            self.assertEqual(metadata["sample_width_bytes"], 2)
            self.assertTrue(math.isclose(metadata["duration_seconds"], 0.1))

    def test_binding_uses_exact_bytes_and_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "asset.bin"
            path.write_bytes(b"exact")
            result = MODULE.binding(path, "fixture")
            self.assertEqual(result["bytes"], 5)
            self.assertEqual(result["role"], "fixture")
            self.assertEqual(result["sha256"], MODULE.sha256(path))

    def test_parses_last_loudnorm_record(self):
        output = 'noise\n{"input_i":"-20.00","input_tp":"-2.50","input_lra":"1.00","input_thresh":"-30.00","normalization_type":"dynamic"}\n'
        result = MODULE.parse_loudnorm(output)
        self.assertEqual(result["integrated_lufs"], -20.0)
        self.assertEqual(result["true_peak_dbtp"], -2.5)
        self.assertEqual(result["normalization_type"], "dynamic")

    def test_missing_loudnorm_record_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            MODULE.parse_loudnorm("no measurement")

    def test_build_refuses_to_clobber_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            args = self._args(base)
            Path(args.output_dir).mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                MODULE.build(args)

    def test_build_rejects_invalid_duration_before_ffmpeg(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            args = self._args(base)
            args.duration = 0
            with self.assertRaisesRegex(ValueError, "durations must be positive"):
                MODULE.build(args)

    def test_build_rejects_missing_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            args = self._args(base)
            Path(args.foley_source).unlink()
            with self.assertRaisesRegex(ValueError, "foley source is not a file"):
                MODULE.build(args)

    def test_build_cleans_temp_directory_when_ffmpeg_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            args = self._args(base)
            with mock.patch.object(MODULE, "run", side_effect=ValueError("ffmpeg failed")):
                with self.assertRaisesRegex(ValueError, "ffmpeg failed"):
                    MODULE.build(args)
            self.assertFalse(Path(args.output_dir).exists())
            self.assertEqual([path for path in base.iterdir() if path.name.startswith(".output.tmp-")], [])


if __name__ == "__main__":
    unittest.main()
