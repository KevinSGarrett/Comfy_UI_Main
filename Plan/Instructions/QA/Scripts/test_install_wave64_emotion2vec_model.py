import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/install_wave64_emotion2vec_model.py"
SPEC = importlib.util.spec_from_file_location("install_wave64_emotion2vec_model", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class Emotion2VecInstallerTests(unittest.TestCase):
    def test_expected_payload_is_exactly_pinned(self):
        self.assertEqual(MODULE.MODEL_ID, "iic/emotion2vec_plus_large")
        self.assertEqual(MODULE.MODEL_REVISION, "v2.0.5")
        self.assertEqual(
            MODULE.FILES["model.pt"]["sha256"],
            "be501a01f26fcdc7663a062dff86af839afbaef7c4de32f5e42d7e1ad2784da4",
        )
        self.assertEqual(MODULE.FILES["model.pt"]["bytes"], 1_945_790_254)

    def test_token_fix_is_revision_separated_from_model(self):
        self.assertNotEqual(MODULE.FILES["tokens.txt"]["revision"], MODULE.FILES["model.pt"]["revision"])
        self.assertEqual(MODULE.FILES["tokens.txt"]["revision"], MODULE.TOKEN_REVISION)

    def test_verify_local_requires_hash_and_size(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "asset.bin"
            path.write_bytes(b"exact")
            expected = {"bytes": 5, "sha256": MODULE.sha256(path)}
            self.assertTrue(MODULE.verify_local(path, expected))
            expected["sha256"] = "0" * 64
            self.assertFalse(MODULE.verify_local(path, expected))

    def test_download_reuses_a_verified_local_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "asset.bin"
            path.write_bytes(b"already present")
            expected = {"bytes": path.stat().st_size, "sha256": MODULE.sha256(path)}
            MODULE.download("invalid://must-not-be-contacted", path, expected)
            self.assertEqual(path.read_bytes(), b"already present")

    def test_file_inventory_uses_repository_paths(self):
        payload = {"Data": {"Files": [{"Path": "model.pt", "Sha256": "abc"}, {"Path": "example", "Type": "tree"}]}}
        inventory = MODULE.file_inventory(payload)
        self.assertEqual(inventory["model.pt"]["Sha256"], "abc")
        self.assertIn("example", inventory)


if __name__ == "__main__":
    unittest.main()
