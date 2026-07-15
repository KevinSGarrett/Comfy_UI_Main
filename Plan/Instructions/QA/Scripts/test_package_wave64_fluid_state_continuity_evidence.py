import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/package_wave64_fluid_state_continuity_evidence.py"
SPEC = importlib.util.spec_from_file_location("package_wave64_fluid_state", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class PackageWave64FluidStateContinuityEvidenceTests(unittest.TestCase):
    def _manifests(self):
        base_boundaries = {"ec2_started": False, "aws_contacted": False, "content_based_suppression": False}
        gates = {"production_certification_pass": False, "row_complete": False}
        pair = {
            "status": "PASS_TECHNICAL_PAIR_PENDING_DIRECT_VISUAL_REVIEW",
            "runtime": {"actual_generation_count": 2, "retry_count": 0},
            "boundaries": dict(base_boundaries),
            "gates": dict(gates),
        }
        img2img = {
            "status": "PASS_IMG2IMG_TECHNICAL_PENDING_DIRECT_VISUAL_REVIEW",
            "runtime": {"actual_candidate_count": 1, "retry_count": 0},
            "boundaries": dict(base_boundaries),
            "gates": dict(gates),
        }
        masked_boundaries = {
            **base_boundaries,
            "edit_region_mask_is_not_truth": True,
            "mask_promotion": False,
        }
        masked = {
            "status": "PASS_MASKED_INPAINT_TECHNICAL_PENDING_DIRECT_VISUAL_REVIEW",
            "runtime": {"actual_candidate_count": 1, "retry_count": 0},
            "boundaries": masked_boundaries,
            "gates": dict(gates),
        }
        return pair, img2img, masked

    def test_manifest_verifier_accepts_exact_fail_closed_chain(self):
        MODULE.verify_manifests(*self._manifests())

    def test_manifest_verifier_rejects_pair_retry(self):
        pair, img2img, masked = self._manifests()
        pair["runtime"]["retry_count"] = 1
        with self.assertRaisesRegex(ValueError, "pair retry"):
            MODULE.verify_manifests(pair, img2img, masked)

    def test_manifest_verifier_rejects_mask_promotion(self):
        pair, img2img, masked = self._manifests()
        masked["boundaries"]["mask_promotion"] = True
        with self.assertRaisesRegex(ValueError, "mask promotion"):
            MODULE.verify_manifests(pair, img2img, masked)

    def test_manifest_verifier_rejects_production_certification(self):
        pair, img2img, masked = self._manifests()
        masked["gates"]["production_certification_pass"] = True
        with self.assertRaisesRegex(ValueError, "production certification"):
            MODULE.verify_manifests(pair, img2img, masked)

    def test_regional_difference_separates_inside_and_outside(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = root / "baseline.png"
            candidate = root / "candidate.png"
            mask = root / "mask.png"
            Image.new("RGB", (8, 8), (0, 0, 0)).save(baseline)
            changed = Image.new("RGB", (8, 8), (0, 0, 0))
            changed.putpixel((2, 2), (255, 255, 255))
            changed.putpixel((7, 7), (64, 64, 64))
            changed.save(candidate)
            mask_image = Image.new("L", (8, 8), 0)
            mask_image.putpixel((2, 2), 255)
            mask_image.save(mask)
            report = MODULE.regional_difference(baseline, candidate, mask)
            self.assertGreater(report["inside_edit_region_normalized_mean_absolute_difference"], report["outside_edit_region_normalized_mean_absolute_difference"])
            self.assertFalse(report["outside_region_byte_preservation_claimed"])

    def test_write_exact_produces_identical_mirrors(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = [Path(temporary) / "qa.json", Path(temporary) / "tracker.json"]
            digest = MODULE.write_exact({"ok": True}, paths)
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
            self.assertTrue(all(MODULE.sha256_file(path) == digest for path in paths))


if __name__ == "__main__":
    unittest.main()
