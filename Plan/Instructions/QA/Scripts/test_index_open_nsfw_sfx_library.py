import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/index_open_nsfw_sfx_library.py"
SPEC = importlib.util.spec_from_file_location("index_open_nsfw_sfx_library", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class IndexOpenNsfwSfxLibraryTests(unittest.TestCase):
    def test_license_classification(self):
        self.assertEqual(MODULE._license_from_path("Fabric (CC0)/a.wav"), "CC0-1.0")
        self.assertEqual(MODULE._license_from_path("Fabric (CC4.0 ATTRIBUTION)/a.wav"), "CC-BY-4.0")
        self.assertEqual(MODULE._license_from_path("Dry (No Attribution)/a.wav"), "pack_claimed_no_attribution")
        self.assertEqual(MODULE._license_from_path("Other/a.wav"), "open_nsfw_sfx_pack_terms")

    def test_builds_deterministic_sorted_non_git_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            (source / "OpenNSFW SFX/Fabric (CC0)").mkdir(parents=True)
            (source / "OpenNSFW SFX/Fabric (CC0)/z.wav").write_bytes(b"wave-z")
            (source / "OpenNSFW SFX/Fabric (CC0)/a.mp3").write_bytes(b"mp3-a")
            (source / "OpenNSFW SFX/Fabric (CC0)/_readme_and_license.txt").write_text("CC0", encoding="utf-8")
            (source / "OpenNSFW SFX/Fabric (CC0)/ignored.bin").write_bytes(b"x")
            output = base / "index"
            summary = MODULE.build_index(source, output)
            self.assertEqual(summary["audio_file_count"], 2)
            self.assertFalse(summary["source_files_modified"])
            records = [json.loads(line) for line in (output / "audio_asset_index.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([record["extension"] for record in records], [".mp3", ".wav"])
            self.assertEqual({record["category"] for record in records}, {"Fabric (CC0)"})
            self.assertTrue(all(record["license_classification"] == "CC0-1.0" for record in records))
            self.assertTrue(all(record["content_based_suppression"] is False for record in records))

    def test_refuses_to_clobber_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            output = base / "output"
            output.mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                MODULE.build_index(source, output)


if __name__ == "__main__":
    unittest.main()
