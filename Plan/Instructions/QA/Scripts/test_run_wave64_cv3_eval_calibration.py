import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/run_wave64_cv3_eval_calibration.py"
SPEC = importlib.util.spec_from_file_location("run_wave64_cv3_eval_calibration", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class CV3EvalCalibrationTests(unittest.TestCase):
    def test_normalized_wer(self):
        self.assertEqual(MODULE.normalized_wer("We move on the beat.", "we move on the beat"), 0.0)
        self.assertEqual(MODULE.normalized_wer("We move on the beat.", "we move on the B"), 0.2)

    def test_normalized_wer_rejects_empty_expected_text(self):
        with self.assertRaisesRegex(ValueError, "empty tokens"):
            MODULE.normalized_wer("...", "anything")

    def test_parse_kaldi_map_preserves_order_and_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "map.scp"
            path.write_text("uttid_1 one two\nuttid_2 three\n", encoding="utf-8")
            self.assertEqual(MODULE.parse_kaldi_map(path), [("uttid_1", "one two"), ("uttid_2", "three")])

    def test_parse_kaldi_map_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "map.scp"
            path.write_text("same one\nsame two\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate Kaldi key"):
                MODULE.parse_kaldi_map(path)

    def test_require_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "asset.bin"
            path.write_bytes(b"exact")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                MODULE.require_hash(path, "0" * 64, "fixture")

    def test_percentile_rank(self):
        self.assertEqual(MODULE.percentile_rank([1.0, 2.0, 3.0, 4.0], 2.5), 0.5)

    def test_percentile_rank_requires_values(self):
        with self.assertRaisesRegex(ValueError, "requires calibration values"):
            MODULE.percentile_rank([], 2.0)

    def test_true_median_averages_even_middle_values(self):
        self.assertEqual(MODULE.true_median([4.0, 1.0, 3.0, 2.0]), 2.5)
        self.assertEqual(MODULE.true_median([3.0, 1.0, 2.0]), 2.0)

    def test_verify_whisper_metadata_rejects_unbound_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.safetensors.metadata"
            path.write_text(f"{MODULE.WHISPER_REVISION}\nwrong\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                MODULE.verify_whisper_metadata(path)

    def test_candidate_lineage_binds_packet_contract_text_and_media(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = (root / "line.wav").resolve()
            candidate.write_bytes(b"candidate")
            candidate_sha256 = MODULE.sha256(candidate)
            packet = root / "packet.json"
            packet.write_text(
                json.dumps(
                    {
                        "result": "pass",
                        "execution_passed": True,
                        "verified_media": {"media_path": str(candidate), "sha256": candidate_sha256},
                        "timeline_conformance": {"speech_truncated": False},
                    }
                ),
                encoding="utf-8",
            )
            contract = root / "contract.json"
            contract.write_text(
                json.dumps(
                    {
                        "lines": [
                            {
                                "line_id": "L001",
                                "character_id": "C01",
                                "voice_profile_id": "voice",
                                "text": "Bound text.",
                                "output_file": str(candidate),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            binding = MODULE.bind_candidate_lineage(
                candidate,
                candidate_sha256,
                packet,
                MODULE.sha256(packet),
                contract,
                MODULE.sha256(contract),
            )
            self.assertEqual(binding["expected_text"], "Bound text.")

    def test_candidate_lineage_rejects_contract_media_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = (root / "line.wav").resolve()
            candidate.write_bytes(b"candidate")
            candidate_sha256 = MODULE.sha256(candidate)
            packet = root / "packet.json"
            packet.write_text(
                json.dumps(
                    {
                        "result": "pass",
                        "execution_passed": True,
                        "verified_media": {"media_path": str(candidate), "sha256": candidate_sha256},
                        "timeline_conformance": {"speech_truncated": False},
                    }
                ),
                encoding="utf-8",
            )
            contract = root / "contract.json"
            contract.write_text(
                json.dumps({"lines": [{"text": "Wrong file.", "output_file": str(root / "other.wav")}]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "exactly one line"):
                MODULE.bind_candidate_lineage(
                    candidate,
                    candidate_sha256,
                    packet,
                    MODULE.sha256(packet),
                    contract,
                    MODULE.sha256(contract),
                )


if __name__ == "__main__":
    unittest.main()
