from __future__ import annotations

import importlib.util
import csv
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "apply_wave64_rows113_117_tracking.py"
SPEC = importlib.util.spec_from_file_location("tracking", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class Rows113117TrackingTests(unittest.TestCase):
    def test_status_requires_classification(self) -> None:
        with self.assertRaises(MODULE.TrackingError):
            MODULE.status_for({})

    def test_append_note_is_idempotent(self) -> None:
        path = "evidence.json"
        first = MODULE.append_note("existing", path)
        second = MODULE.append_note(first, path)
        self.assertEqual(first, second)

    def test_mirror_evidence_is_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "Plan/Instructions/QA/Evidence/Test/value.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps({"pass": True}) + "\n", encoding="utf-8")
            left, right = MODULE.mirror_evidence(root, source.relative_to(root))
            self.assertEqual(source.read_bytes(), (root / right).read_bytes())
            self.assertTrue(left.endswith("value.json"))

    def test_model_runtime_update_is_exact_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hashes = [f"{number:064x}" for number in range(1, 12)]
            proof_path = root / MODULE.LOADER_PROOF_RELATIVE
            proof_path.parent.mkdir(parents=True)
            proof_path.write_text(
                json.dumps(
                    {
                        "classification": "QWEN3_TTS_VOICEDESIGN_LOAD_PROOF_PASS_AUDIO_GENERATION_PENDING",
                        "created_at": "2026-07-15T00:00:00-05:00",
                        "model_files": [
                            {
                                "sha256": value,
                                "path": f"models/audio/tts/qwen3_tts_1_7b_voicedesign/file{index}.bin",
                            }
                            for index, value in enumerate(hashes)
                        ],
                    }
                ),
                encoding="utf-8",
            )
            registry_path = root / MODULE.MODEL_REGISTRY
            registry_path.parent.mkdir(parents=True)
            records = [
                {
                    "workflow_lane": "wave64_hyperreal_speech_rows113_117",
                    "source_model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
                    "source_model_version_id": "5ecdb67327fd37bb2e042aab12ff7391903235d3",
                    "sha256": value,
                    "record_id": f"MODEL-ACQ-{index:016X}",
                    "local_path": f"F:/offload/file{index}.bin",
                }
                for index, value in enumerate(hashes)
            ]
            registry_path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
            queue_path = root / MODULE.MODEL_QUEUE
            with queue_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["queue_id", "workflow_lane", "model_name", "local_path", "status", "evidence_path"],
                )
                writer.writeheader()
                for index, _ in enumerate(hashes):
                    writer.writerow(
                        {
                            "queue_id": f"MRQ-ACQ-{index:016X}",
                            "workflow_lane": "wave64_hyperreal_speech_rows113_117",
                            "model_name": "qwen3_tts_1_7b_voicedesign",
                            "local_path": f"F:/offload/file{index}.bin",
                            "status": "queued",
                            "evidence_path": "",
                        }
                    )
            first = MODULE.update_model_runtime_records(root)
            second = MODULE.update_model_runtime_records(root)
            self.assertEqual(first, second)
            self.assertEqual(11, first["model_registry_records_updated"])
            self.assertIn("load_proven_audio_generation_pending", registry_path.read_text(encoding="utf-8"))
            self.assertNotIn("F:/offload", registry_path.read_text(encoding="utf-8"))
            self.assertNotIn("F:/offload", queue_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
