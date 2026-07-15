import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION/scripts/run_wave64_openslr31_speaker_identity_validation.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_wave64_openslr31_speaker_identity_validation", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class FakeAuthority:
    @staticmethod
    def select_threshold(labels, scores):
        return 0.5, {
            "threshold": 0.5,
            "true_positive_rate": 1.0,
            "false_positive_rate": 0.0,
            "balanced_accuracy": 1.0,
            "training_constraints_pass": True,
        }

    @staticmethod
    def rates(labels, scores, threshold):
        positives = [score for label, score in zip(labels, scores) if label]
        negatives = [score for label, score in zip(labels, scores) if not label]
        return {
            "threshold": threshold,
            "true_positive_rate": sum(score >= threshold for score in positives) / len(positives),
            "false_positive_rate": sum(score >= threshold for score in negatives) / len(negatives),
            "balanced_accuracy": 1.0,
        }


class FakeEvaluator:
    @staticmethod
    def similarity(left, right):
        return 0.9 if left[0] == right[0] else 0.1


def make_dataset(root: Path, bad_filename: bool = False):
    counts = []
    for index in range(MODULE.EXPECTED_SPEAKER_COUNT):
        speaker_id = str(100 + index)
        chapter_id = str(200 + index)
        chapter = root / speaker_id / chapter_id
        chapter.mkdir(parents=True)
        utterance_count = 42 if index < 23 else 41
        counts.append(utterance_count)
        for utterance in range(utterance_count):
            file_speaker = "999" if bad_filename and index == 0 and utterance == 0 else speaker_id
            (chapter / f"{file_speaker}-{chapter_id}-{utterance:04d}.flac").write_bytes(
                f"{speaker_id}-{utterance}".encode("ascii")
            )
    assert sum(counts) == MODULE.EXPECTED_UTTERANCE_COUNT


class OpenSLR31SpeakerIdentityValidationTests(unittest.TestCase):
    def test_select_spread_is_deterministic_and_includes_ends(self):
        items = [Path(str(index)) for index in range(11)]
        selected = MODULE.select_spread(items, 6)
        self.assertEqual(selected, [Path("0"), Path("2"), Path("4"), Path("6"), Path("8"), Path("10")])

    def test_discover_speakers_verifies_counts_and_selects_six(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_dataset(root)
            speakers, utterances = MODULE.discover_speakers(root, 6)
            self.assertEqual(len(speakers), 26)
            self.assertEqual(utterances, 1089)
            self.assertTrue(all(len(speaker["selected"]) == 6 for speaker in speakers))

    def test_discover_speakers_rejects_filename_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_dataset(root, bad_filename=True)
            with self.assertRaisesRegex(ValueError, "does not bind speaker/chapter identity"):
                MODULE.discover_speakers(root, 6)

    def test_discover_speakers_rejects_nonnumeric_speaker_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_dataset(root)
            (root / "speaker-x").mkdir()
            with self.assertRaisesRegex(ValueError, "numeric speaker IDs"):
                MODULE.discover_speakers(root, 6)

    def test_partition_is_thirteen_by_thirteen_without_overlap(self):
        speakers = [{"speaker_id": str(index)} for index in range(26)]
        calibration, validation = MODULE.partition_speakers(speakers)
        self.assertEqual(len(calibration), 13)
        self.assertEqual(len(validation), 13)
        self.assertFalse(
            {item["speaker_id"] for item in calibration}
            & {item["speaker_id"] for item in validation}
        )

    def test_pair_examples_are_exhaustive(self):
        speakers = [{"speaker_id": "a"}, {"speaker_id": "b"}]
        embeddings = {
            "a": [("a", 0), ("a", 1), ("a", 2)],
            "b": [("b", 0), ("b", 1), ("b", 2)],
        }
        labels, scores = MODULE.pair_examples(speakers, embeddings, FakeEvaluator())
        self.assertEqual(sum(labels), 6)
        self.assertEqual(len(labels) - sum(labels), 9)
        self.assertEqual(scores.count(0.9), 6)
        self.assertEqual(scores.count(0.1), 9)

    def test_threshold_validation_passes_disjoint_metrics(self):
        result = MODULE.evaluate_threshold(
            [True, True, False, False],
            [0.9, 0.8, 0.2, 0.1],
            [True, True, False, False],
            [0.85, 0.75, 0.25, 0.15],
            FakeAuthority(),
        )
        self.assertTrue(result["speaker_disjoint_validation_pass"])
        self.assertTrue(result["threshold_deployment_allowed_for_chain_specific_evaluation"])

    def test_threshold_validation_fails_high_held_out_fpr(self):
        result = MODULE.evaluate_threshold(
            [True, True, False, False],
            [0.9, 0.8, 0.2, 0.1],
            [True, True, False, False],
            [0.85, 0.75, 0.65, 0.15],
            FakeAuthority(),
        )
        self.assertFalse(result["speaker_disjoint_validation_pass"])

    def test_resource_page_requires_license_and_archive_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            page = Path(temporary) / "page.html"
            page.write_text(
                "<html><body>Mini LibriSpeech ASR corpus CC BY 4.0 dev-clean-2.tar.gz</body></html>",
                encoding="utf-8",
            )
            binding = MODULE.verify_resource_page(page, MODULE.digest(page))
            self.assertEqual(binding["url"], MODULE.RESOURCE_URL)
            page.write_text("<html>Mini LibriSpeech ASR corpus</html>", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing required declarations"):
                MODULE.verify_resource_page(page, MODULE.digest(page))

    def test_previous_manifest_preserves_blocked_prior_threshold(self):
        payload = {
            "artifact_type": "wave64_cv3_speaker_identity_calibration",
            "chain_specific_evaluation": {
                "speaker_similarity": 0.99,
                "threshold_deployment_allowed": False,
                "binding": {"source": "test"},
            },
        }
        result = MODULE.validate_previous_manifest(payload)
        self.assertEqual(result["speaker_similarity"], 0.99)
        payload["chain_specific_evaluation"]["threshold_deployment_allowed"] = True
        with self.assertRaisesRegex(ValueError, "preserve its blocked threshold"):
            MODULE.validate_previous_manifest(payload)


if __name__ == "__main__":
    unittest.main()
