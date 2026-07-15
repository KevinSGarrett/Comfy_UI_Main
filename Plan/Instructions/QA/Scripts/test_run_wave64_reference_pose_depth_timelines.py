from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_reference_pose_depth_timelines.py"
REQUIREMENTS_PATH = ROOT / "Workflows/video_generation/reference_pose_depth_timeline/runtime_requirements.json"
spec = importlib.util.spec_from_file_location("run_wave64_reference_pose_depth_timelines", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def source_record(index: int, path: Path) -> dict:
    return {
        "frame_id": f"frame-{index}",
        "frame_index": index,
        "frame_path_or_asset_id": path.name,
        "timestamp_seconds": index / 24,
        "png_sha256": module.sha256(path),
    }


def make_pose_frame(width: int, height: int, valid_body: int = 18) -> dict:
    body = []
    for index in range(18):
        body.extend([20.0 + index, 30.0 + index, 1.0 if index < valid_body else 0.0])
    return {
        "people": [
            {
                "pose_keypoints_2d": body,
                "face_keypoints_2d": [],
                "hand_left_keypoints_2d": [],
                "hand_right_keypoints_2d": [],
            }
        ],
        "canvas_width": width,
        "canvas_height": height,
    }


class ReferencePoseDepthTimelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.requirements = json.loads(REQUIREMENTS_PATH.read_text(encoding="utf-8"))
        self.requirements["source_scope"].update(
            {"frame_count": 3, "width": 32, "height": 48}
        )
        self.requirements["workflow"]["resolution"] = 32
        self.requirements["technical_thresholds"].update(
            {"minimum_unique_pose_hashes": 3, "minimum_unique_depth_hashes": 3}
        )

    def _images(self, root: Path, kind: str, blank: bool = False) -> list[Path]:
        paths = []
        for index in range(3):
            path = root / f"{kind}_{index}.png"
            image = Image.new("RGB", (32, 48), "black")
            if not blank:
                draw = ImageDraw.Draw(image)
                draw.rectangle((4 + index, 5, 20 + index, 40), fill=(40 + 40 * index, 120, 220))
                draw.line((0, 10 + index, 31, 35), fill=(255, 255, 255), width=2)
            image.save(path)
            paths.append(path)
        return paths

    def test_workflow_batches_all_inputs_before_single_preprocessors(self) -> None:
        workflow = module.build_workflow(
            [f"stage/frame_{index:06d}.png" for index in range(49)],
            "out/run",
            self.requirements["workflow"],
        )
        classes = [node["class_type"] for node in workflow.values()]
        self.assertEqual(classes.count("LoadImage"), 49)
        self.assertEqual(classes.count("ImageBatch"), 48)
        self.assertEqual(classes.count("DWPreprocessor"), 1)
        self.assertEqual(classes.count("DepthAnythingV2Preprocessor"), 1)
        self.assertEqual(workflow[module.POSE_NODE_ID]["inputs"]["image"], ["147", 0])
        self.assertEqual(workflow[module.DEPTH_NODE_ID]["inputs"]["image"], ["147", 0])

    def test_preprocessor_dimensions_follow_short_edge_contract(self) -> None:
        self.assertEqual(
            module.expected_preprocessor_dimensions(
                {"width": 480, "height": 640}, 640
            ),
            (640, 853),
        )

    def test_scaled_render_and_source_canvas_contract_pass_together(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = self._images(root, "scaled_source")
            pose_paths = []
            depth_paths = []
            for kind, paths in (("scaled_pose", pose_paths), ("scaled_depth", depth_paths)):
                for index in range(3):
                    path = root / f"{kind}_{index}.png"
                    image = Image.new("RGB", (64, 96), "black")
                    draw = ImageDraw.Draw(image)
                    draw.rectangle((8 + index, 10, 42 + index, 82), fill=(80, 150, 230))
                    draw.line((0, 18 + index, 63, 70), fill="white", width=3)
                    image.save(path)
                    paths.append(path)
            requirements = json.loads(json.dumps(self.requirements))
            requirements["workflow"]["resolution"] = 64
            result = module.evaluate_timelines(
                [source_record(i, path) for i, path in enumerate(sources)],
                pose_paths,
                depth_paths,
                [make_pose_frame(32, 48) for _ in range(3)],
                requirements,
                root / "scaled_output",
            )
            self.assertTrue(result["checks"]["pose_preprocessor_dimensions_exact"])
            self.assertTrue(result["checks"]["depth_preprocessor_dimensions_exact"])
            self.assertTrue(result["checks"]["pose_canvas_dimensions_exact"])
            self.assertEqual(
                result["coordinate_contract"]["render_to_source_transform"][
                    "source_x_per_render_x"
                ],
                0.5,
            )
            self.assertTrue(result["technical_pass"], result["failed_checks"])

    def test_source_validation_rejects_hash_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "frame.png"
            Image.new("RGB", (32, 48), "red").save(path)
            records = [source_record(0, path)]
            records[0]["png_sha256"] = "0" * 64
            scope = {"frame_count": 1, "width": 32, "height": 48}
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                module.validate_source_frames(records, root, scope)

    def test_source_validation_rejects_noncontiguous_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = []
            for index in range(2):
                path = root / f"frame_{index}.png"
                Image.new("RGB", (32, 48), "red").save(path)
                paths.append(path)
            records = [source_record(1, paths[1]), source_record(0, paths[0])]
            scope = {"frame_count": 2, "width": 32, "height": 48}
            with self.assertRaisesRegex(ValueError, "ordered and contiguous"):
                module.validate_source_frames(records, root, scope)

    def test_valid_pose_and_depth_timelines_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_paths = self._images(root, "source")
            pose_paths = self._images(root, "pose")
            depth_paths = self._images(root, "depth")
            records = [source_record(index, path) for index, path in enumerate(source_paths)]
            result = module.evaluate_timelines(
                records,
                pose_paths,
                depth_paths,
                [make_pose_frame(32, 48) for _ in range(3)],
                self.requirements,
                root / "output",
            )
            self.assertTrue(result["technical_pass"], result["failed_checks"])

    def test_missing_person_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = self._images(root, "source")
            poses = self._images(root, "pose")
            depths = self._images(root, "depth")
            frames = [make_pose_frame(32, 48) for _ in range(3)]
            frames[1]["people"] = []
            result = module.evaluate_timelines(
                [source_record(i, p) for i, p in enumerate(sources)],
                poses,
                depths,
                frames,
                self.requirements,
                root / "output",
            )
            self.assertFalse(result["technical_pass"])
            self.assertIn("one_person_each_frame", result["failed_checks"])
            self.assertIn("body_keypoints_each_frame", result["failed_checks"])

    def test_insufficient_body_keypoints_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = self._images(root, "source")
            poses = self._images(root, "pose")
            depths = self._images(root, "depth")
            frames = [make_pose_frame(32, 48), make_pose_frame(32, 48, 5), make_pose_frame(32, 48)]
            result = module.evaluate_timelines(
                [source_record(i, p) for i, p in enumerate(sources)],
                poses,
                depths,
                frames,
                self.requirements,
                root / "output",
            )
            self.assertIn("body_keypoints_each_frame", result["failed_checks"])

    def test_blank_depth_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = self._images(root, "source")
            poses = self._images(root, "pose")
            depths = self._images(root, "depth", blank=True)
            result = module.evaluate_timelines(
                [source_record(i, p) for i, p in enumerate(sources)],
                poses,
                depths,
                [make_pose_frame(32, 48) for _ in range(3)],
                self.requirements,
                root / "output",
            )
            self.assertIn("depth_render_nonblank", result["failed_checks"])

    def test_wrong_pose_count_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = self._images(root, "source")
            poses = self._images(root, "pose")[:2]
            depths = self._images(root, "depth")
            result = module.evaluate_timelines(
                [source_record(i, p) for i, p in enumerate(sources)],
                poses,
                depths,
                [make_pose_frame(32, 48) for _ in range(3)],
                self.requirements,
                root / "output",
            )
            self.assertIn("pose_output_count_exact", result["failed_checks"])


if __name__ == "__main__":
    unittest.main()
