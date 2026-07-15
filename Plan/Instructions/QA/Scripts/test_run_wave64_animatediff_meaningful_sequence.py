from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_animatediff_meaningful_sequence.py"
REQUIREMENTS = ROOT / "Workflows/video_generation/animatediff_fallback_meaningful_sequence/runtime_requirements.json"
spec = importlib.util.spec_from_file_location("run_wave64_animatediff_meaningful_sequence", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def save_webp(path: Path, frames: list[Image.Image]) -> None:
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=125, loop=0, lossless=True)


class MeaningfulSequenceEvaluatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.requirements = json.loads(REQUIREMENTS.read_text(encoding="utf-8"))
        self.requirements["sequence_scope"].update({"width": 32, "height": 48, "frame_count": 16})

    def test_stable_moving_sequence_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = []
            for index in range(16):
                frame = Image.new("RGB", (32, 48), (55, 70, 85))
                for x in range(4 + index, 12 + index):
                    for y in range(8, 36):
                        frame.putpixel((x, y), (190, 170, 150))
                frames.append(frame)
            artifact = root / "stable.webp"
            save_webp(artifact, frames)
            result = module.evaluate_artifact(artifact, self.requirements, root / "out")
            self.assertTrue(result["technical_pass"], result["failed_checks"])

    def test_terminal_corruption_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = [Image.new("RGB", (32, 48), (80 + index, 90, 100)) for index in range(15)]
            frames.append(Image.new("RGB", (32, 48), (255, 255, 255)))
            artifact = root / "corrupt.webp"
            save_webp(artifact, frames)
            result = module.evaluate_artifact(artifact, self.requirements, root / "out")
            self.assertFalse(result["technical_pass"])
            self.assertIn("no_terminal_discontinuity", result["failed_checks"])

    def test_wrong_frame_count_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = [Image.new("RGB", (32, 48), (80 + index, 90, 100)) for index in range(15)]
            artifact = root / "short.webp"
            save_webp(artifact, frames)
            result = module.evaluate_artifact(artifact, self.requirements, root / "out")
            self.assertFalse(result["technical_pass"])
            self.assertIn("frame_count_exact", result["failed_checks"])

    def test_single_frame_cannot_pass_pairwise_continuity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "single.webp"
            save_webp(artifact, [Image.new("RGB", (32, 48), (0, 0, 0))])
            result = module.evaluate_artifact(artifact, self.requirements, root / "out")
            self.assertFalse(result["checks"]["no_adjacent_discontinuity"])
            self.assertFalse(result["checks"]["no_terminal_discontinuity"])


if __name__ == "__main__":
    unittest.main()
