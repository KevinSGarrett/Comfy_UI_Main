import sys
import unittest
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from composite_fixed_image_e2e_repair import evaluate, source_preserving_composite


class SourcePreservingCompositeTests(unittest.TestCase):
    def test_restores_black_outside_mask_and_keeps_repair_delta(self):
        source = np.full((64, 64, 3), 100, dtype=np.uint8)
        generated = np.zeros_like(source)
        generated[24:40, 24:40] = 140
        mask = np.zeros((64, 64), dtype=np.uint8)
        mask[24:40, 24:40] = 255

        repaired, hard_mask = source_preserving_composite(
            source, generated, mask, blur_radius=0
        )
        self.assertTrue(np.array_equal(repaired[0, 0], source[0, 0]))
        self.assertTrue(np.array_equal(repaired[30, 30], generated[30, 30]))

        metrics = evaluate(
            source,
            generated,
            repaired,
            hard_mask,
            {
                "minimum_inside_mask_mae": 0.1,
                "maximum_outside_mask_mae": 0.0,
                "minimum_outside_mask_ssim": 1.0,
                "minimum_whole_image_ssim": 0.9,
            },
        )
        self.assertTrue(metrics["technical_pass"])
        self.assertEqual(metrics["outside_mask_mae"], 0.0)
        self.assertGreater(metrics["inside_mask_mae"], 0.1)
        self.assertGreater(metrics["raw_generated_outside_mask_black_pixel_ratio"], 0.99)

    def test_dimension_mismatch_fails_closed(self):
        source = np.zeros((32, 32, 3), dtype=np.uint8)
        generated = np.zeros((16, 16, 3), dtype=np.uint8)
        mask = np.zeros((32, 32), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "dimensions differ"):
            source_preserving_composite(source, generated, mask, blur_radius=0)


if __name__ == "__main__":
    unittest.main()
