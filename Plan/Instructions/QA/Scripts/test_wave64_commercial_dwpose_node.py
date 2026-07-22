from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[4]
NODE = ROOT / "Plan/07_IMPLEMENTATION/comfyui_custom_nodes/wave64_commercial_dwpose/__init__.py"
LOCK = ROOT / "Plan/07_IMPLEMENTATION/comfyui_custom_nodes/wave64_commercial_dwpose/runtime_lock.json"


def _module():
    spec = importlib.util.spec_from_file_location("wave64_commercial_dwpose", NODE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_node_identity_lock_and_forbidden_runtime_paths(tmp_path: Path) -> None:
    module = _module()
    model = tmp_path / "model.onnx"
    model.write_bytes(b"approved")
    module.MODEL_SPECS = {"model.onnx": (len(b"approved"), module._sha256(model))}
    assert module.verified_model_path("model.onnx", tmp_path) == model
    with pytest.raises(module.DWPoseContractError, match="unapproved"):
        module.verified_model_path("../model.onnx", tmp_path)
    model.write_bytes(b"drifted")
    with pytest.raises(module.DWPoseContractError, match="identity mismatch"):
        module.verified_model_path("model.onnx", tmp_path)
    source = NODE.read_text(encoding="utf-8")
    for forbidden in ("torch.load", "torch.jit.load", "pickle", "subprocess", "pip install", "requests", "urllib"):
        assert forbidden not in source
    assert set(module.NODE_CLASS_MAPPINGS) == {"Wave64CommercialDWPosePreprocessor"}
    required = list(module.Wave64CommercialDWPosePreprocessor.INPUT_TYPES()["required"])
    assert required == ["image", "detect_hand", "detect_body", "detect_face", "resolution", "bbox_detector", "pose_estimator", "scale_stick_for_xinsr_cn"]
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    assert lock["authority"]["wheelhouse_hash_replay"] is True
    assert lock["authority"]["environment_created"] is False
    assert lock["forbidden_distributions"] == ["onnxruntime"]
    assert len(lock["wheels"]) == 6
    assert all(len(item["sha256"]) == 64 and item["bytes"] > 0 for item in lock["wheels"])


def test_yolox_decode_nms_and_shape_gate() -> None:
    module = _module()
    prediction = np.zeros((1, 8400, 6), dtype=np.float32)
    prediction[0, 0, 4:] = 0.9
    prediction[0, 1, 4:] = 0.8
    boxes = module.decode_yolox(prediction, (640, 640), 0.5, 0.45)
    assert boxes.shape == (2, 4)
    with pytest.raises(module.DWPoseContractError, match="unexpected YOLOX"):
        module.decode_yolox(np.zeros((1, 10, 6), dtype=np.float32), (640, 640), 0.5, 0.45)


def test_simcc_openpose_and_render_contract() -> None:
    module = _module()
    simcc_x = np.zeros((1, 133, 576), dtype=np.float32)
    simcc_y = np.zeros((1, 133, 768), dtype=np.float32)
    simcc_x[:, :, 100] = 0.9
    simcc_y[:, :, 200] = 0.8
    points = module.decode_simcc(simcc_x, simcc_y, np.array((10, 20, 298, 404), dtype=np.float32))
    assert points.shape == (133, 3)
    assert np.allclose(points[0], (60, 120, 0.8))
    record = module._openpose_record(points, 0.3)
    assert len(record["pose_keypoints_2d"]) == 17 * 3
    assert len(record["face_keypoints_2d"]) == 68 * 3
    assert len(record["hand_left_keypoints_2d"]) == 21 * 3
    assert len(record["hand_right_keypoints_2d"]) == 21 * 3
    rendered = module.render_pose(320, 480, [points], 0.3)
    assert rendered.shape == (480, 320, 3)
    assert rendered.dtype == np.float32
    assert rendered.max() > 0
    assert module._resize_dimensions(640, 480, 1024) == (1344, 1024)
    filtered = module._filter_keypoints(points, include_hand=False, include_body=True, include_face=False)
    assert np.all(filtered[23:133, 2] == 0)
    assert np.all(filtered[0:23, 2] > 0)
