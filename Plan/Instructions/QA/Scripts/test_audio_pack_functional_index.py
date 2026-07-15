import json
import struct
import tempfile
import unittest
import wave
from pathlib import Path

import importlib.util


ROOT = Path(__file__).resolve().parents[4]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


INDEXER = _load("functional_index", ROOT / "Plan/07_IMPLEMENTATION/scripts/build_audio_pack_functional_index.py")
SELECTOR = _load("functional_selector", ROOT / "Plan/07_IMPLEMENTATION/scripts/select_audio_pack_assets.py")


def _wav(path: Path, seconds: float) -> None:
    frames = int(16000 * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(struct.pack("<h", 0) * frames)


class AudioPackFunctionalIndexTests(unittest.TestCase):
    def test_classification_uses_wave30_wave31_terms(self):
        self.assertEqual(INDEXER._classify_event("Pack/Fabric rustle soft.wav"), "clothing_foley")
        self.assertEqual(INDEXER._intensity("Pack/Fabric rustle soft.wav"), "low")
        self.assertEqual(INDEXER._sync_class("impact"), "frame_exact")

    def test_build_resume_hash_dedupe_and_select(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            first = source / "Fabric soft loop (CC0).wav"
            second = source / "Fabric soft duplicate (CC0).wav"
            bracketed = source / "Literal [--] folder/Literal [--++] sound.wav"
            bracketed.parent.mkdir(parents=True)
            _wav(first, 0.5)
            second.write_bytes(first.read_bytes())
            _wav(bracketed, 0.25)
            output = base / "index"
            summary = INDEXER.build_index(source, output)
            self.assertEqual(summary["audio_file_count"], 3)
            self.assertEqual(summary["unique_audio_sha256_count"], 2)
            self.assertEqual(summary["duplicate_audio_file_count"], 1)
            resumed = INDEXER.build_index(source, output, resume=True)
            self.assertEqual(resumed["index"]["sha256"], summary["index"]["sha256"])
            selected = SELECTOR.select_assets(output / "audio_pack_functional_index.jsonl", {"event_type": "clothing_foley"}, 5)
            self.assertEqual(len(selected), 2)
            self.assertTrue(all(item["sha256"] == selected[0]["sha256"] for item in selected))
            records = [json.loads(line) for line in (output / "audio_pack_functional_index.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any("[--]" in record["relative_path"] for record in records))
            self.assertTrue(all(record["content_based_suppression"] is False for record in records))

    def test_refuses_existing_output_without_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            _wav(source / "a.wav", 0.1)
            output = base / "index"
            INDEXER.build_index(source, output)
            with self.assertRaisesRegex(ValueError, "already exists"):
                INDEXER.build_index(source, output)


if __name__ == "__main__":
    unittest.main()
