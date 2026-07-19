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
            self.assertEqual(summary["indexed_count"], 3)
            self.assertEqual(summary["exact_blocker_count"], 0)
            self.assertTrue(summary["indexed_plus_blockers_equals_discovered"])
            self.assertEqual(summary["unique_audio_sha256_count"], 2)
            self.assertEqual(summary["duplicate_audio_file_count"], 1)
            self.assertTrue(summary["source_inventory_fingerprint"]["unchanged"])
            self.assertTrue((output / "failure_manifest.json").is_file())
            failure = json.loads((output / "failure_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(failure["exact_blocker_count"], 0)
            self.assertTrue(failure["indexed_plus_blockers_equals_discovered"])
            resumed = INDEXER.build_index(source, output, resume=True)
            self.assertEqual(resumed["index"]["sha256"], summary["index"]["sha256"])
            self.assertEqual(
                resumed["failure_manifest"]["sha256"],
                summary["failure_manifest"]["sha256"],
            )
            selected = SELECTOR.select_assets(
                output / "audio_pack_functional_index.jsonl",
                {"event_type": "clothing_foley"},
                5,
            )
            self.assertEqual(len(selected), 2)
            self.assertTrue(all(item["sha256"] == selected[0]["sha256"] for item in selected))
            records = [
                json.loads(line)
                for line in (output / "audio_pack_functional_index.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertTrue(any("[--]" in record["relative_path"] for record in records))
            self.assertTrue(all(record["content_based_suppression"] is False for record in records))

    def test_empty_file_becomes_exact_blocker_and_reconciles(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            good = source / "Fabric soft (CC0).wav"
            empty = source / "empty_blocker.wav"
            _wav(good, 0.2)
            empty.write_bytes(b"")
            output = base / "index"
            summary = INDEXER.build_index(source, output)
            self.assertEqual(summary["audio_file_count"], 2)
            self.assertEqual(summary["indexed_count"], 1)
            self.assertEqual(summary["exact_blocker_count"], 1)
            self.assertTrue(summary["indexed_plus_blockers_equals_discovered"])
            failure = json.loads((output / "failure_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(failure["blockers"][0]["code"], "INDEX_EMPTY_OR_UNREADABLE")
            self.assertEqual(failure["blockers"][0]["relative_path"], "empty_blocker.wav")
            INDEXER._validate_failure_manifest(failure)

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

    def test_authority_packet_remains_fail_closed(self):
        packet = INDEXER.build_authority_packet(ROOT)
        self.assertFalse(packet["row_complete"])
        self.assertFalse(packet["library_authority"])
        self.assertFalse(packet["implementation_completion_claimed"])
        self.assertFalse(packet["runtime_completion_claimed"])
        self.assertEqual(packet["decision"]["row069_acceptance"], "held")
        self.assertEqual(packet["decision"]["status"], "blocked")
        self.assertIn("ROW069_LIBRARY_RUNTIME_AUTHORITY_NOT_GRANTED", packet["blocker_codes"])
        self.assertIn("FULL_LIBRARY_RESUME_REPLAY_ABSENT", packet["blocker_codes"])
        self.assertIn("TRK_W64_068_DEPENDENCY_NOT_ACCEPTED", packet["blocker_codes"])
        self.assertIn("ROW069_PREREQUISITE_DEPENDENCY_NOT_ACCEPTED", packet["blocker_codes"])
        self.assertIn("RETAINED_INDEX_BYTE_HASH_RECONCILIATION_ABSENT", packet["blocker_codes"])
        fixture = packet["fixture_calibration"]["summary"]
        self.assertTrue(fixture["indexed_plus_blockers_equals_discovered"])
        self.assertTrue(fixture["source_fingerprint_unchanged"])
        self.assertTrue(fixture["resume_index_sha256_match"])
        self.assertTrue(fixture["resume_failure_manifest_sha256_match"])
        self.assertEqual(fixture["exact_blocker_count"], 1)
        self.assertEqual(fixture["indexed_count"], 2)


if __name__ == "__main__":
    unittest.main()
