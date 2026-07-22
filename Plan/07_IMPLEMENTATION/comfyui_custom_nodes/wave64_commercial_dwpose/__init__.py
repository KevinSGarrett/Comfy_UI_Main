from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


MODEL_SPECS = {
    "yolox_l.onnx": (216_746_733, "7860ae79de6c89a3c1eb72ae9a2756c0ccfbe04b7791bb5880afabd97855a411"),
    "dw-ll_ucoco_384.onnx": (134_399_116, "724f4ff2439ed61afb86fb8a1951ec39c6220682803b4a8bd4f598cd913b1843"),
}
BODY_EDGES = ((0, 1), (0, 2), (1, 3), (2, 4), (5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16))
FOOT_EDGES = ((15, 17), (15, 18), (15, 19), (16, 20), (16, 21), (16, 22))
HAND_EDGES = tuple((base, base + finger * 4 + 1) for base in (91, 112) for finger in range(5)) + tuple(
    (base + finger * 4 + joint, base + finger * 4 + joint + 1)
    for base in (91, 112)
    for finger in range(5)
    for joint in range(1, 4)
)


class DWPoseContractError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verified_model_path(filename: str, model_dir: Path | None = None) -> Path:
    if filename not in MODEL_SPECS or Path(filename).name != filename:
        raise DWPoseContractError(f"unapproved model name: {filename}")
    root = (model_dir or Path(__file__).with_name("models")).resolve()
    path = (root / filename).resolve()
    if path.parent != root or not path.is_file() or path.is_symlink():
        raise DWPoseContractError(f"model must be a regular file in {root}: {filename}")
    expected_size, expected_hash = MODEL_SPECS[filename]
    if path.stat().st_size != expected_size or _sha256(path) != expected_hash:
        raise DWPoseContractError(f"model identity mismatch: {filename}")
    return path


def _nms(boxes: np.ndarray, scores: np.ndarray, threshold: float) -> list[int]:
    if not len(boxes):
        return []
    x1, y1, x2, y2 = boxes.T
    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size:
        current = int(order[0])
        keep.append(current)
        if order.size == 1:
            break
        remaining = order[1:]
        intersection = np.maximum(0.0, np.minimum(x2[current], x2[remaining]) - np.maximum(x1[current], x1[remaining])) * np.maximum(
            0.0, np.minimum(y2[current], y2[remaining]) - np.maximum(y1[current], y1[remaining])
        )
        union = areas[current] + areas[remaining] - intersection
        iou = np.divide(intersection, union, out=np.zeros_like(intersection), where=union > 0)
        order = remaining[iou <= threshold]
    return keep


def decode_yolox(prediction: np.ndarray, input_size: tuple[int, int], score_threshold: float, nms_threshold: float) -> np.ndarray:
    rows = np.asarray(prediction, dtype=np.float32).reshape(-1, prediction.shape[-1]).copy()
    input_h, input_w = input_size
    grids: list[np.ndarray] = []
    strides: list[np.ndarray] = []
    for stride in (8, 16, 32):
        height, width = input_h // stride, input_w // stride
        y, x = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
        grids.append(np.stack((x, y), axis=-1).reshape(-1, 2))
        strides.append(np.full((height * width, 1), stride, dtype=np.float32))
    grid = np.concatenate(grids).astype(np.float32)
    stride = np.concatenate(strides)
    if len(rows) != len(grid) or rows.shape[1] < 6:
        raise DWPoseContractError(f"unexpected YOLOX output shape: {rows.shape}")
    rows[:, :2] = (rows[:, :2] + grid) * stride
    rows[:, 2:4] = np.exp(np.clip(rows[:, 2:4], -20.0, 20.0)) * stride
    scores = rows[:, 4] * rows[:, 5:].max(axis=1)
    selected = scores >= score_threshold
    centers, sizes, scores = rows[selected, :2], rows[selected, 2:4], scores[selected]
    boxes = np.concatenate((centers - sizes / 2.0, centers + sizes / 2.0), axis=1)
    return boxes[_nms(boxes, scores, nms_threshold)]


def decode_simcc(simcc_x: np.ndarray, simcc_y: np.ndarray, crop_box: np.ndarray, split_ratio: float = 2.0) -> np.ndarray:
    x = np.asarray(simcc_x).squeeze(0)
    y = np.asarray(simcc_y).squeeze(0)
    if x.ndim != 2 or y.ndim != 2 or x.shape[0] != 133 or y.shape[0] != 133:
        raise DWPoseContractError(f"unexpected SimCC output shapes: {x.shape}, {y.shape}")
    x_index, y_index = x.argmax(axis=1), y.argmax(axis=1)
    confidence = np.minimum(x[np.arange(133), x_index], y[np.arange(133), y_index])
    crop_x1, crop_y1, crop_x2, crop_y2 = crop_box.astype(np.float32)
    points = np.empty((133, 3), dtype=np.float32)
    points[:, 0] = crop_x1 + (x_index / split_ratio) * (crop_x2 - crop_x1) / (x.shape[1] / split_ratio)
    points[:, 1] = crop_y1 + (y_index / split_ratio) * (crop_y2 - crop_y1) / (y.shape[1] / split_ratio)
    points[:, 2] = confidence
    return points


def _openpose_record(points: np.ndarray, threshold: float) -> dict[str, Any]:
    def flatten(start: int, end: int) -> list[float]:
        values: list[float] = []
        for x, y, score in points[start:end]:
            values.extend((float(x), float(y), float(score) if score >= threshold else 0.0))
        return values

    return {
        "pose_keypoints_2d": flatten(0, 17),
        "face_keypoints_2d": flatten(23, 91),
        "hand_left_keypoints_2d": flatten(91, 112),
        "hand_right_keypoints_2d": flatten(112, 133),
    }


def render_pose(width: int, height: int, people: list[np.ndarray], threshold: float) -> np.ndarray:
    canvas = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(canvas)
    for points in people:
        for start, end in BODY_EDGES + FOOT_EDGES + HAND_EDGES:
            if points[start, 2] >= threshold and points[end, 2] >= threshold:
                draw.line((float(points[start, 0]), float(points[start, 1]), float(points[end, 0]), float(points[end, 1])), fill=(80, 220, 255), width=3)
        for x, y, score in points:
            if score >= threshold:
                draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 120, 80))
    return np.asarray(canvas, dtype=np.float32) / 255.0


def _resize_dimensions(width: int, height: int, resolution: int) -> tuple[int, int]:
    scale = resolution / min(width, height)
    target_width = max(64, round((width * scale) / 64) * 64)
    target_height = max(64, round((height * scale) / 64) * 64)
    return target_width, target_height


def _filter_keypoints(points: np.ndarray, include_hand: bool, include_body: bool, include_face: bool) -> np.ndarray:
    filtered = points.copy()
    if not include_body:
        filtered[0:23, 2] = 0
    if not include_face:
        filtered[23:91, 2] = 0
    if not include_hand:
        filtered[91:133, 2] = 0
    return filtered


class Wave64CommercialDWPosePreprocessor:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {"required": {"image": ("IMAGE",), "detect_hand": (["enable", "disable"],), "detect_body": (["enable", "disable"],), "detect_face": (["enable", "disable"],), "resolution": ("INT", {"default": 512, "min": 64, "max": 4096, "step": 64}), "bbox_detector": (tuple(MODEL_SPECS)[:1],), "pose_estimator": (tuple(MODEL_SPECS)[1:],), "scale_stick_for_xinsr_cn": (["disable", "enable"],)}}

    RETURN_TYPES = ("IMAGE", "POSE_KEYPOINT")
    FUNCTION = "estimate_pose"
    CATEGORY = "Wave64/Commercial Pose"

    def estimate_pose(self, image: Any, detect_hand: str = "enable", detect_body: str = "enable", detect_face: str = "enable", resolution: int = 512, bbox_detector: str = "yolox_l.onnx", pose_estimator: str = "dw-ll_ucoco_384.onnx", scale_stick_for_xinsr_cn: str = "disable", **kwargs: Any) -> dict[str, Any]:
        del kwargs
        import onnxruntime as ort
        import torch

        overlay = os.environ.get("WAVE64_DWPOSE_OVERLAY_SITE_PACKAGES")
        if not overlay or not Path(ort.__file__).resolve().is_relative_to(Path(overlay).resolve()):
            raise DWPoseContractError("ONNX Runtime must resolve from the qualified Wave64 overlay")
        if scale_stick_for_xinsr_cn != "disable":
            raise DWPoseContractError("xinsr stick scaling is not qualified by this replacement contract")
        if ort.__version__ != "1.27.0" or "CUDAExecutionProvider" not in ort.get_available_providers():
            raise DWPoseContractError("exact ONNX Runtime 1.27.0 CUDA provider is required")
        detector_path = verified_model_path(bbox_detector)
        pose_path = verified_model_path(pose_estimator)
        sessions = [ort.InferenceSession(str(path), providers=["CUDAExecutionProvider"]) for path in (detector_path, pose_path)]
        detector, pose = sessions
        rendered: list[np.ndarray] = []
        records: list[dict[str, Any]] = []
        for frame in image.detach().cpu().numpy():
            rgb = np.clip(frame[..., :3] * 255.0, 0, 255).astype(np.uint8)
            source_height, source_width = rgb.shape[:2]
            width, height = _resize_dimensions(source_width, source_height, resolution)
            rgb = np.asarray(Image.fromarray(rgb).resize((width, height), Image.Resampling.BILINEAR))
            detector_input = detector.get_inputs()[0]
            input_h, input_w = (int(detector_input.shape[-2]), int(detector_input.shape[-1]))
            scale = min(input_w / width, input_h / height)
            resized = Image.fromarray(rgb).resize((round(width * scale), round(height * scale)), Image.Resampling.BILINEAR)
            letterbox = np.full((input_h, input_w, 3), 114, dtype=np.uint8)
            letterbox[: resized.height, : resized.width] = np.asarray(resized)
            detector_tensor = letterbox.transpose(2, 0, 1)[None].astype(np.float32)
            boxes = decode_yolox(detector.run(None, {detector_input.name: detector_tensor})[0], (input_h, input_w), 0.3, 0.45) / scale
            people: list[np.ndarray] = []
            pose_input = pose.get_inputs()[0]
            pose_h, pose_w = int(pose_input.shape[-2]), int(pose_input.shape[-1])
            for box in boxes:
                x1, y1, x2, y2 = box
                center_x, center_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                crop_w, crop_h = max(x2 - x1, 1.0) * 1.25, max(y2 - y1, 1.0) * 1.25
                if crop_w / crop_h > pose_w / pose_h:
                    crop_h = crop_w * pose_h / pose_w
                else:
                    crop_w = crop_h * pose_w / pose_h
                crop_box = np.array((max(0, center_x - crop_w / 2), max(0, center_y - crop_h / 2), min(width, center_x + crop_w / 2), min(height, center_y + crop_h / 2)), dtype=np.float32)
                crop = Image.fromarray(rgb).crop(tuple(crop_box)).resize((pose_w, pose_h), Image.Resampling.BILINEAR)
                pose_tensor = np.asarray(crop, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
                pose_tensor = (pose_tensor - np.array((0.485, 0.456, 0.406), dtype=np.float32)[None, :, None, None]) / np.array((0.229, 0.224, 0.225), dtype=np.float32)[None, :, None, None]
                outputs = pose.run(None, {pose_input.name: pose_tensor})
                if len(outputs) != 2:
                    raise DWPoseContractError("pose model must expose exactly two SimCC outputs")
                simcc_x, simcc_y = sorted(outputs, key=lambda value: value.shape[-1])
                people.append(
                    _filter_keypoints(
                        decode_simcc(simcc_x, simcc_y, crop_box),
                        include_hand=detect_hand == "enable",
                        include_body=detect_body == "enable",
                        include_face=detect_face == "enable",
                    )
                )
            rendered.append(render_pose(width, height, people, 0.3))
            records.append({"canvas_width": width, "canvas_height": height, "people": [_openpose_record(person, 0.3) for person in people]})
        return {"ui": {"openpose_json": [json.dumps(records, indent=2)]}, "result": (torch.from_numpy(np.stack(rendered)), records)}


NODE_CLASS_MAPPINGS = {"Wave64CommercialDWPosePreprocessor": Wave64CommercialDWPosePreprocessor}
NODE_DISPLAY_NAME_MAPPINGS = {"Wave64CommercialDWPosePreprocessor": "Wave64 Commercial DWPose (hash-pinned ONNX)"}

__all__ = ["DWPoseContractError", "NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "Wave64CommercialDWPosePreprocessor", "decode_simcc", "decode_yolox", "render_pose", "verified_model_path"]
