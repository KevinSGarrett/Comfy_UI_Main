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
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            retained = base / "retained"
            source.mkdir()
            first = source / "Fabric soft (CC0).wav"
            second = source / "Impact hit metal.wav"
            _wav(first, 0.2)
            _wav(second, 0.15)
            built = INDEXER.build_index(source, retained)
            # Drop failure_manifest to mirror retained 20260715 production layout.
            (retained / "failure_manifest.json").unlink(missing_ok=True)
            packet = INDEXER.build_authority_packet(
                ROOT,
                source_root=source,
                retained_dir=retained,
                byte_hash_sample_limit=1,
            )
        self.assertFalse(packet["row_complete"])
        self.assertFalse(packet["library_authority"])
        self.assertFalse(packet["implementation_completion_claimed"])
        self.assertFalse(packet["runtime_completion_claimed"])
        self.assertEqual(packet["decision"]["row069_acceptance"], "held")
        self.assertEqual(packet["decision"]["status"], "blocked")
        self.assertTrue(packet["dependency_authority"]["all_satisfied"])
        self.assertNotIn("TRK_W64_068_DEPENDENCY_NOT_ACCEPTED", packet["blocker_codes"])
        self.assertNotIn("ROW069_PREREQUISITE_DEPENDENCY_NOT_ACCEPTED", packet["blocker_codes"])
        self.assertIn("ROW069_LIBRARY_RUNTIME_AUTHORITY_NOT_GRANTED", packet["blocker_codes"])
        self.assertIn("FULL_LIBRARY_RESUME_REPLAY_ABSENT", packet["blocker_codes"])
        self.assertIn("RETAINED_INDEX_BYTE_HASH_RECONCILIATION_SAMPLE_ONLY", packet["blocker_codes"])
        self.assertIn("CURRENT_EXTERNAL_INVENTORY_NOT_RECONCILED", packet["blocker_codes"])
        self.assertEqual(
            packet["byte_hash_reconciliation"]["status"],
            "SCAFFOLD_SAMPLE_BYTE_HASH_RECONCILED",
        )
        self.assertEqual(packet["byte_hash_reconciliation"]["checked_count"], 1)
        self.assertFalse(packet["byte_hash_reconciliation"]["complete"])
        self.assertFalse(packet["resume_replay_scaffold"]["full_library_resume_replay_complete"])
        self.assertTrue(packet["resume_replay_scaffold"]["fixture_copy_resume_proof"]["index_sha256_stable"])
        self.assertEqual(built["indexed_count"], 2)
        fixture = packet["fixture_calibration"]["summary"]
        self.assertTrue(fixture["indexed_plus_blockers_equals_discovered"])
        self.assertTrue(fixture["source_fingerprint_unchanged"])
        self.assertTrue(fixture["resume_index_sha256_match"])
        self.assertTrue(fixture["resume_failure_manifest_sha256_match"])
        self.assertEqual(fixture["exact_blocker_count"], 1)
        self.assertEqual(fixture["indexed_count"], 2)

    def test_byte_hash_reconcile_and_resume_scaffold(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            retained = base / "retained"
            source.mkdir()
            wav_a = source / "a.wav"
            wav_b = source / "b.wav"
            _wav(wav_a, 0.1)
            _wav(wav_b, 0.12)
            INDEXER.build_index(source, retained)
            full = INDEXER.reconcile_retained_index_byte_hashes(
                source,
                retained / "audio_pack_functional_index.jsonl",
                sample_limit=None,
            )
            self.assertTrue(full["complete"])
            self.assertEqual(full["status"], "FULL_LIBRARY_BYTE_HASH_RECONCILED")
            sample = INDEXER.reconcile_retained_index_byte_hashes(
                source,
                retained / "audio_pack_functional_index.jsonl",
                sample_limit=1,
            )
            self.assertFalse(sample["complete"])
            self.assertTrue(sample["scaffold_only"])
            self.assertEqual(sample["status"], "SCAFFOLD_SAMPLE_BYTE_HASH_RECONCILED")
            scaffold = INDEXER.build_resume_replay_scaffold(retained, source_root=source)
            self.assertFalse(scaffold["full_library_resume_replay_complete"])
            self.assertTrue(scaffold["fixture_copy_resume_proof"]["index_sha256_stable"])
            self.assertTrue(scaffold["fixture_copy_resume_proof"]["failure_manifest_sha256_stable"])
            self.assertEqual(scaffold["status"], "RESUME_REPLAY_SCAFFOLD_READY_FULL_LIBRARY_ABSENT")


if __name__ == "__main__":
    unittest.main()
