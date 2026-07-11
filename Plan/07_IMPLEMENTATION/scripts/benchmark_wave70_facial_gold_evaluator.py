#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage


ALLOWED_TRANSFORMS = ("identity", "resize", "pad", "crop", "horizontal_flip")
LAPA_REQUIRED_IDS = {str(index) for index in range(11)}
CELEB_SKIN_UNION_SOURCES = ("skin", "l_brow", "r_brow", "l_eye", "r_eye", "nose", "mouth", "u_lip", "l_lip")
REGISTERED_BISENET_NECK_MODEL_SHA256 = "468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_path(path: Path) -> str:
    if path.is_file():
        return sha256_file(path)
    if path.is_dir():
        digest = hashlib.sha256()
        for child in sorted(entry for entry in path.rglob("*") if entry.is_file()):
            rel = child.relative_to(path).as_posix().encode("utf-8")
            digest.update(rel)
            digest.update(b"\0")
            digest.update(sha256_file(child).encode("ascii"))
            digest.update(b"\n")
        return digest.hexdigest()
    raise FileNotFoundError(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def to_abs_path(project_root: Path, maybe_path: str) -> Path:
    candidate = Path(maybe_path.replace("\\", "/"))
    if candidate.is_absolute():
        return candidate.resolve()
    return (project_root / candidate).resolve()


def parse_size(raw: Any) -> tuple[int, int]:
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValueError("size_must_be_[width,height]")
    width = int(raw[0])
    height = int(raw[1])
    if width <= 0 or height <= 0:
        raise ValueError("size_values_must_be_positive")
    return width, height


def ensure_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def image_to_bool_mask(path: Path) -> np.ndarray:
    image = Image.open(path).convert("L")
    array = np.asarray(image, dtype=np.uint8)
    return array > 0


def image_to_indexed(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L"), dtype=np.uint8)


def resize_mask_nearest(mask: np.ndarray, width: int, height: int) -> np.ndarray:
    image = Image.fromarray(np.where(mask, 255, 0).astype(np.uint8), mode="L")
    resized = image.resize((width, height), Image.Resampling.NEAREST)
    return np.asarray(resized, dtype=np.uint8) > 0


def resize_indexed_nearest(indexed: np.ndarray, width: int, height: int) -> np.ndarray:
    image = Image.fromarray(indexed.astype(np.uint8), mode="L")
    resized = image.resize((width, height), Image.Resampling.NEAREST)
    return np.asarray(resized, dtype=np.uint8)


def validate_transform_chain(
    transforms: list[dict[str, Any]], source_size: tuple[int, int]
) -> tuple[bool, str, tuple[int, int]]:
    current_size = source_size
    for transform in transforms:
        op = str(transform.get("op", "")).strip()
        if op not in ALLOWED_TRANSFORMS:
            return False, f"unknown_transform:{op}", current_size
        if op == "horizontal_flip":
            size = parse_size(transform.get("size", list(current_size)))
            if size != current_size:
                return False, "horizontal_flip_size_mismatch", current_size
            continue
        from_size = parse_size(transform.get("from_size"))
        to_size = parse_size(transform.get("to_size"))
        if from_size != current_size:
            return False, f"transform_from_size_mismatch:{op}", current_size
        if op == "identity" and to_size != from_size:
            return False, "identity_size_mismatch", current_size
        if op == "pad":
            expected = (
                from_size[0] + int(transform.get("left", 0)) + int(transform.get("right", 0)),
                from_size[1] + int(transform.get("top", 0)) + int(transform.get("bottom", 0)),
            )
            if min(int(transform.get(key, 0)) for key in ("left", "top", "right", "bottom")) < 0:
                return False, "pad_values_must_be_nonnegative", current_size
            if to_size != expected:
                return False, "pad_dimension_mismatch", current_size
        if op == "crop":
            x = int(transform.get("x", -1))
            y = int(transform.get("y", -1))
            if x < 0 or y < 0 or x + to_size[0] > from_size[0] or y + to_size[1] > from_size[1]:
                return False, "crop_bounds_invalid", current_size
        current_size = to_size
    return True, "ok", current_size


def transform_output_size(transforms: list[dict[str, Any]], source_size: tuple[int, int]) -> tuple[int, int]:
    current_size = source_size
    for transform in transforms:
        if transform["op"] == "horizontal_flip":
            continue
        current_size = parse_size(transform["to_size"])
    return current_size


def invert_mask_to_source(mask: np.ndarray, transforms: list[dict[str, Any]], source_size: tuple[int, int]) -> np.ndarray:
    current = mask
    final_size = transform_output_size(transforms, source_size)
    if current.shape != (final_size[1], final_size[0]):
        raise ValueError(
            f"prediction_dimension_mismatch:{current.shape[1]}x{current.shape[0]}!={final_size[0]}x{final_size[1]}"
        )
    for transform in reversed(transforms):
        op = transform["op"]
        if op == "identity":
            continue
        if op == "horizontal_flip":
            current = np.fliplr(current)
            continue
        from_w, from_h = parse_size(transform["from_size"])
        to_w, to_h = parse_size(transform["to_size"])
        if current.shape != (to_h, to_w):
            raise ValueError(f"prediction_dimension_mismatch:{current.shape[1]}x{current.shape[0]}!={to_w}x{to_h}")
        if op == "resize":
            current = resize_mask_nearest(current, from_w, from_h)
            continue
        if op == "pad":
            left = int(transform.get("left", 0))
            top = int(transform.get("top", 0))
            right = int(transform.get("right", 0))
            bottom = int(transform.get("bottom", 0))
            expected_h = from_h + top + bottom
            expected_w = from_w + left + right
            if (to_w, to_h) != (expected_w, expected_h):
                raise ValueError("pad_dimension_mismatch")
            current = current[top : top + from_h, left : left + from_w]
            continue
        if op == "crop":
            x = int(transform.get("x", 0))
            y = int(transform.get("y", 0))
            canvas = np.zeros((from_h, from_w), dtype=bool)
            x_end = min(from_w, x + to_w)
            y_end = min(from_h, y + to_h)
            crop_x0 = max(0, -x)
            crop_y0 = max(0, -y)
            target_x0 = max(0, x)
            target_y0 = max(0, y)
            h = y_end - target_y0
            w = x_end - target_x0
            if h > 0 and w > 0:
                canvas[target_y0:y_end, target_x0:x_end] = current[crop_y0 : crop_y0 + h, crop_x0 : crop_x0 + w]
            current = canvas
            continue
        raise ValueError(f"unsupported_transform:{op}")
    if current.shape != (source_size[1], source_size[0]):
        raise ValueError("transform_inversion_did_not_restore_source_dimensions")
    return current


def invert_points_to_source(points: np.ndarray, transforms: list[dict[str, Any]], source_size: tuple[int, int]) -> np.ndarray:
    current = points.astype(np.float64)
    for transform in reversed(transforms):
        op = transform["op"]
        if op == "identity":
            continue
        if op == "horizontal_flip":
            width, _ = parse_size(transform["size"])
            current[:, 0] = (width - 1) - current[:, 0]
            continue
        from_w, from_h = parse_size(transform["from_size"])
        to_w, to_h = parse_size(transform["to_size"])
        if op == "resize":
            sx = from_w / to_w
            sy = from_h / to_h
            current[:, 0] *= sx
            current[:, 1] *= sy
            continue
        if op == "pad":
            left = float(transform.get("left", 0))
            top = float(transform.get("top", 0))
            current[:, 0] -= left
            current[:, 1] -= top
            continue
        if op == "crop":
            x = float(transform.get("x", 0))
            y = float(transform.get("y", 0))
            current[:, 0] += x
            current[:, 1] += y
            continue
        raise ValueError(f"unsupported_transform:{op}")
    current[:, 0] = np.clip(current[:, 0], 0.0, float(source_size[0] - 1))
    current[:, 1] = np.clip(current[:, 1], 0.0, float(source_size[1] - 1))
    return current


def boundary_f_score(gold: np.ndarray, pred: np.ndarray, tolerance: int = 1) -> float:
    if not np.any(gold) and not np.any(pred):
        return 1.0
    structure = ndimage.generate_binary_structure(2, 1)
    gold_boundary = np.logical_xor(gold, ndimage.binary_erosion(gold, structure=structure, border_value=0))
    pred_boundary = np.logical_xor(pred, ndimage.binary_erosion(pred, structure=structure, border_value=0))
    if tolerance > 0:
        gold_d = ndimage.binary_dilation(gold_boundary, iterations=tolerance)
        pred_d = ndimage.binary_dilation(pred_boundary, iterations=tolerance)
    else:
        gold_d = gold_boundary
        pred_d = pred_boundary
    tp = float(np.count_nonzero(np.logical_and(pred_boundary, gold_d)))
    fp = float(np.count_nonzero(np.logical_and(pred_boundary, np.logical_not(gold_d))))
    fn = float(np.count_nonzero(np.logical_and(gold_boundary, np.logical_not(pred_d))))
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    if precision + recall == 0.0:
        return 0.0
    return float(2.0 * precision * recall / (precision + recall))


def binary_metrics(gold: np.ndarray, pred: np.ndarray, boundary_tolerance: int) -> dict[str, Any]:
    tp = int(np.count_nonzero(np.logical_and(gold, pred)))
    fp = int(np.count_nonzero(np.logical_and(np.logical_not(gold), pred)))
    fn = int(np.count_nonzero(np.logical_and(gold, np.logical_not(pred))))
    tn = int(np.count_nonzero(np.logical_and(np.logical_not(gold), np.logical_not(pred))))
    union = tp + fp + fn
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    dice_den = (2 * tp) + fp + fn
    gold_empty = not np.any(gold)
    pred_empty = not np.any(pred)
    if gold_empty and pred_empty:
        empty_category = "gold_empty_pred_empty"
    elif gold_empty:
        empty_category = "gold_empty_pred_nonempty"
    elif pred_empty:
        empty_category = "gold_nonempty_pred_empty"
    else:
        empty_category = "gold_nonempty_pred_nonempty"
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "iou": (tp / union) if union else 1.0,
        "dice": (2 * tp / dice_den) if dice_den else 1.0,
        "precision": precision,
        "recall": recall,
        "boundary_f_score": boundary_f_score(gold, pred, tolerance=boundary_tolerance),
        "empty_category": empty_category,
    }


def parse_landmarks_txt(path: Path) -> np.ndarray:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError("empty_landmark_file")
    try:
        declared_count = int(lines[0])
    except ValueError as exc:
        raise ValueError("landmark_count_header_missing") from exc
    pairs: list[list[float]] = []
    for raw in lines[1:]:
        stripped = raw.strip()
        if not stripped:
            continue
        pieces = stripped.split()
        if len(pieces) != 2:
            raise ValueError("invalid_landmark_txt_row")
        pairs.append([float(pieces[0]), float(pieces[1])])
    if len(pairs) != declared_count:
        raise ValueError(f"landmark_count_mismatch_header:{declared_count}!={len(pairs)}")
    return np.asarray(pairs, dtype=np.float64)


def parse_landmarks_prediction(path: Path) -> np.ndarray:
    payload = load_json(path)
    if not isinstance(payload, list):
        raise ValueError("predicted_landmarks_not_list")
    points: list[list[float]] = []
    for point in payload:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError("predicted_landmark_bad_point")
        points.append([float(point[0]), float(point[1])])
    if not points:
        raise ValueError("predicted_landmarks_empty")
    return np.asarray(points, dtype=np.float64)


def nme_with_normalization(
    gold_points: np.ndarray, pred_points: np.ndarray, norm_pair: list[int]
) -> tuple[float, float]:
    if len(norm_pair) != 2:
        raise ValueError("normalization_pair_must_have_two_indices")
    i0 = int(norm_pair[0])
    i1 = int(norm_pair[1])
    if i0 < 0 or i1 < 0 or i0 >= len(gold_points) or i1 >= len(gold_points):
        raise ValueError("normalization_indices_out_of_range")
    norm = float(np.linalg.norm(gold_points[i0] - gold_points[i1]))
    if norm <= 0.0:
        raise ValueError("normalization_distance_must_be_positive")
    per_point = np.linalg.norm(gold_points - pred_points, axis=1)
    return float(np.mean(per_point) / norm), norm


def build_rollups(sample_results: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    class_buckets: dict[str, list[dict[str, Any]]] = {}
    landmark_values: list[float] = []
    leakage_values: list[float] = []
    for sample in sample_results:
        evaluation = sample.get("evaluation", {})
        for class_result in evaluation.get("classes", []):
            class_key = str(class_result.get("class_name", class_result.get("class_id")))
            class_buckets.setdefault(class_key, []).append(class_result)
            leakage_values.append(float(class_result.get("protected_neighbor_leakage", 0.0)))
        landmark_result = evaluation.get("landmarks")
        if isinstance(landmark_result, dict) and landmark_result.get("nme") is not None:
            landmark_values.append(float(landmark_result["nme"]))
    per_class: dict[str, Any] = {}
    metric_names = ("iou", "dice", "precision", "recall", "boundary_f_score")
    for class_key, entries in sorted(class_buckets.items()):
        empty_counts: dict[str, int] = {}
        for entry in entries:
            category = str(entry["metrics"]["empty_category"])
            empty_counts[category] = empty_counts.get(category, 0) + 1
        per_class[class_key] = {
            "sample_count": len(entries),
            "mean_metrics": {
                metric: float(np.mean([float(entry["metrics"][metric]) for entry in entries]))
                for metric in metric_names
            },
            "mean_protected_neighbor_leakage": float(
                np.mean([float(entry.get("protected_neighbor_leakage", 0.0)) for entry in entries])
            ),
            "empty_class_accounting": empty_counts,
        }
    landmark_summary = {
        "sample_count": len(landmark_values),
        "mean_nme": float(np.mean(landmark_values)) if landmark_values else None,
        "max_nme": max(landmark_values) if landmark_values else None,
    }
    leakage_summary = {
        "class_sample_count": len(leakage_values),
        "mean_protected_neighbor_leakage": float(np.mean(leakage_values)) if leakage_values else None,
        "max_protected_neighbor_leakage": max(leakage_values) if leakage_values else None,
    }
    return per_class, landmark_summary, leakage_summary


def detect_gold_leakage_strings(data: Any, gold_roots: list[Path]) -> list[str]:
    hits: list[str] = []

    def walk(obj: Any, trail: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                lower = str(key).lower()
                if lower.endswith("gold_path") or lower == "gold_path":
                    hits.append(f"{trail}.{key}:gold_path_field")
                walk(value, f"{trail}.{key}")
            return
        if isinstance(obj, list):
            for index, value in enumerate(obj):
                walk(value, f"{trail}[{index}]")
            return
        if isinstance(obj, str):
            lowered = obj.lower().replace("\\", "/")
            if "mask-anno" in lowered or "/labels/" in lowered or "/landmarks/" in lowered:
                hits.append(f"{trail}:annotation_like_path")
            candidate = Path(obj.replace("\\", "/"))
            for root in gold_roots:
                root_norm = str(root.resolve()).lower().replace("\\", "/")
                candidate_norm = str(candidate).lower()
                if candidate_norm.startswith(root_norm):
                    hits.append(f"{trail}:inside_gold_root")

    walk(data, "$")
    return sorted(set(hits))


def validate_celeb_composition(project_root: Path, sample: dict[str, Any], pred_dir: Path) -> None:
    composition = sample.get("composition")
    if composition is None:
        return
    if not isinstance(composition, dict) or composition.get("enabled") is not True:
        raise ValueError("composition_contract_invalid")
    if composition.get("composition_rule_id") != "celeb_skin_nested_union_v1":
        raise ValueError("composition_rule_unknown")
    if composition.get("target_class") != "skin":
        raise ValueError("composition_target_invalid")
    if tuple(composition.get("union_sources", [])) != CELEB_SKIN_UNION_SOURCES:
        raise ValueError("composition_union_sources_invalid")
    base_dir = to_abs_path(project_root, str(composition.get("base_prediction_path", "")))
    if not base_dir.is_dir() or sha256_path(base_dir) != composition.get("base_prediction_sha256"):
        raise ValueError("composition_base_prediction_hash_mismatch")
    input_hashes = composition.get("composition_input_hashes")
    if not isinstance(input_hashes, dict) or set(input_hashes) != set(CELEB_SKIN_UNION_SOURCES):
        raise ValueError("composition_input_hashes_invalid")
    union: np.ndarray | None = None
    for class_name in CELEB_SKIN_UNION_SOURCES:
        base_path = base_dir / f"{class_name}.png"
        if not base_path.is_file() or sha256_file(base_path) != input_hashes[class_name]:
            raise ValueError(f"composition_input_hash_mismatch:{class_name}")
        mask = image_to_bool_mask(base_path)
        union = mask if union is None else np.logical_or(union, mask)
    if input_hashes["skin"] != composition.get("base_skin_sha256_preserved"):
        raise ValueError("composition_base_skin_hash_mismatch")
    composed_path = pred_dir / "skin.png"
    if not composed_path.is_file() or sha256_file(composed_path) != composition.get("composition_output_sha256"):
        raise ValueError("composition_output_hash_mismatch")
    if union is None or not np.array_equal(union, image_to_bool_mask(composed_path)):
        raise ValueError("composition_output_not_reproducible")
    for base_path in base_dir.glob("*.png"):
        if base_path.stem == "skin":
            continue
        output_path = pred_dir / base_path.name
        if not output_path.is_file() or sha256_file(base_path) != sha256_file(output_path):
            raise ValueError(f"composition_non_target_class_changed:{base_path.stem}")


def evaluate_celeb_sample(
    sample: dict[str, Any],
    source_path: Path,
    source_size: tuple[int, int],
    transforms: list[dict[str, Any]],
    dataset: dict[str, Any],
    project_root: Path,
    fail_events: list[dict[str, Any]],
    boundary_tolerance: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {"mode": "semantic_segmentation", "classes": []}
    sample_id = int(source_path.stem)
    if str(sample.get("sample_id")) != source_path.stem:
        fail_events.append(
            {"code": "celeb_sample_id_pairing_mismatch", "sample_id": sample.get("sample_id"), "message": source_path.stem}
        )
        return result
    id_min = int(dataset["eligible_id_min"])
    id_max = int(dataset["eligible_id_max"])
    if sample_id < id_min or sample_id > id_max:
        fail_events.append(
            {
                "code": "celeb_id_out_of_range",
                "sample_id": sample.get("sample_id", source_path.stem),
                "message": f"{sample_id} outside [{id_min},{id_max}]",
            }
        )
        return result
    pred_dir = to_abs_path(project_root, str(sample["prediction_path"]))
    if not pred_dir.exists() or not pred_dir.is_dir():
        fail_events.append(
            {
                "code": "prediction_directory_missing",
                "sample_id": sample.get("sample_id", source_path.stem),
                "message": str(pred_dir),
            }
        )
        return result
    validate_celeb_composition(project_root, sample, pred_dir)
    classes = sample.get("classes")
    if not isinstance(classes, list) or not classes:
        fail_events.append(
            {
                "code": "classes_missing",
                "sample_id": sample.get("sample_id", source_path.stem),
                "message": "manifest sample must declare non-empty classes for CelebAMask-HQ",
            }
        )
        return result
    known_classes = set(dataset.get("class_file_counts", {}).keys())
    if known_classes and any(str(class_name) not in known_classes for class_name in classes):
        fail_events.append(
            {"code": "celeb_unknown_class", "sample_id": sample.get("sample_id"), "message": str(classes)}
        )
        return result
    if "neck" in classes and "neck_l" in classes:
        neck_path = pred_dir / "neck.png"
        neck_l_path = pred_dir / "neck_l.png"
        if neck_path.exists() and neck_l_path.exists() and neck_path.resolve() == neck_l_path.resolve():
            fail_events.append(
                {
                    "code": "neck_and_neck_l_merged",
                    "sample_id": sample.get("sample_id", source_path.stem),
                    "message": "neck and neck_l must remain separate classes",
                }
            )
            return result
        if neck_path.exists() and neck_l_path.exists():
            neck_pixels = image_to_bool_mask(neck_path)
            neck_l_pixels = image_to_bool_mask(neck_l_path)
            if neck_pixels.shape == neck_l_pixels.shape and np.any(neck_pixels) and np.array_equal(neck_pixels, neck_l_pixels):
                fail_events.append(
                    {
                        "code": "neck_and_neck_l_pixel_identical",
                        "sample_id": sample.get("sample_id", source_path.stem),
                        "message": "nonempty anatomical neck and necklace/accessory masks must not be pixel-identical",
                    }
                )
                return result
    protected_neighbors = sample.get("protected_neighbors")
    if not isinstance(protected_neighbors, dict) or any(class_name not in protected_neighbors for class_name in classes):
        fail_events.append(
            {
                "code": "protected_neighbors_missing_or_incomplete",
                "sample_id": sample.get("sample_id", source_path.stem),
                "message": "every evaluated class requires an explicit protected-neighbor list",
            }
        )
        return result
    gold_root = to_abs_path(project_root, str(dataset["gold_annotations_root"]))
    class_results: list[dict[str, Any]] = []
    for class_name in classes:
        pred_path = pred_dir / f"{class_name}.png"
        if not pred_path.exists():
            fail_events.append(
                {
                    "code": "prediction_class_mask_missing",
                    "sample_id": sample.get("sample_id", source_path.stem),
                    "message": f"missing {pred_path.name}",
                }
            )
            continue
        pred_mask = invert_mask_to_source(image_to_bool_mask(pred_path), transforms, source_size)
        gold_path = gold_root / f"{sample_id:05d}_{class_name}.png"
        gold_exists = gold_path.exists()
        if gold_exists:
            gold_mask_raw = image_to_bool_mask(gold_path)
            gold_mask = resize_mask_nearest(gold_mask_raw, source_size[0], source_size[1])
        else:
            # Eligible Celeb IDs allow missing class files as explicit empty category.
            gold_mask = np.zeros((source_size[1], source_size[0]), dtype=bool)
        metrics = binary_metrics(gold_mask, pred_mask, boundary_tolerance)
        neighbors = protected_neighbors.get(class_name, [])
        if not isinstance(neighbors, list) or (known_classes and any(str(item) not in known_classes for item in neighbors)):
            raise ValueError(f"protected_neighbor_class_invalid:{class_name}")
        leakage_den = float(np.count_nonzero(pred_mask))
        protected_union = np.zeros_like(pred_mask, dtype=bool)
        for neighbor in neighbors:
            neighbor_path = gold_root / f"{sample_id:05d}_{neighbor}.png"
            if neighbor_path.exists():
                neighbor_mask = resize_mask_nearest(image_to_bool_mask(neighbor_path), source_size[0], source_size[1])
                protected_union = np.logical_or(protected_union, neighbor_mask)
        leakage_num = float(np.count_nonzero(np.logical_and(pred_mask, protected_union)))
        leakage = (leakage_num / leakage_den) if leakage_den else 0.0
        class_results.append(
            {
                "class_name": class_name,
                "gold_exists": gold_exists,
                "gold_normalization": {
                    "source_size": list(source_size),
                    "annotation_size": [int(gold_mask_raw.shape[1]), int(gold_mask_raw.shape[0])] if gold_exists else None,
                    "operation": "nearest_resize_to_source" if gold_exists and gold_mask_raw.shape != gold_mask.shape else "identity_or_empty",
                },
                "prediction_path": str(pred_path),
                "metrics": metrics,
                "protected_neighbor_leakage": leakage,
            }
        )
    result["classes"] = class_results
    return result


def evaluate_lapa_sample(
    manifest: dict[str, Any],
    sample: dict[str, Any],
    source_path: Path,
    source_size: tuple[int, int],
    transforms: list[dict[str, Any]],
    dataset: dict[str, Any],
    project_root: Path,
    split_role_audit: dict[str, Any],
    fail_events: list[dict[str, Any]],
    taxonomy_binding: dict[str, Any] | None,
    boundary_tolerance: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {"classes": [], "landmarks": None, "mode": str(sample.get("mode", "semantic_and_landmarks"))}
    split = str(manifest.get("split", "")).strip()
    if split not in ("train", "val", "test"):
        fail_events.append({"code": "lapa_split_invalid", "sample_id": sample.get("sample_id"), "message": str(split)})
        return result
    split_roots = dataset["splits"][split]
    images_root = to_abs_path(project_root, str(split_roots["images_root"]))
    labels_root = to_abs_path(project_root, str(split_roots["labels_root"]))
    landmarks_root = to_abs_path(project_root, str(split_roots["landmarks_root"]))
    if not ensure_under_root(source_path, images_root):
        fail_events.append(
            {
                "code": "lapa_split_mismatch",
                "sample_id": sample.get("sample_id", source_path.stem),
                "message": f"{source_path} not under {images_root}",
            }
        )
        return result
    split_role_audit["seen_splits"].append(split)
    stem = source_path.stem
    if str(sample.get("sample_id")) != stem:
        fail_events.append({"code": "lapa_sample_id_pairing_mismatch", "sample_id": sample.get("sample_id"), "message": stem})
        return result
    gold_label_path = labels_root / f"{stem}.png"
    gold_landmark_path = landmarks_root / f"{stem}.txt"
    if not gold_label_path.exists():
        fail_events.append(
            {"code": "lapa_gold_label_missing", "sample_id": sample.get("sample_id", stem), "message": str(gold_label_path)}
        )
        return result
    mode = str(sample.get("mode", "semantic_and_landmarks"))
    if mode in ("semantic", "semantic_and_landmarks"):
        taxonomy = taxonomy_binding.get("label_to_class") if isinstance(taxonomy_binding, dict) else None
        if not isinstance(taxonomy, dict) or set(taxonomy.keys()) != LAPA_REQUIRED_IDS:
            fail_events.append(
                {
                    "code": "lapa_taxonomy_missing_or_invalid",
                    "sample_id": sample.get("sample_id", stem),
                    "message": "semantic_taxonomy_binding must map IDs 0..10",
                }
            )
            return result
        protected = taxonomy_binding.get("protected_neighbors") if isinstance(taxonomy_binding, dict) else None
        if not isinstance(protected, dict) or any(class_id not in protected for class_id in LAPA_REQUIRED_IDS):
            fail_events.append(
                {
                    "code": "lapa_protected_neighbors_missing",
                    "sample_id": sample.get("sample_id", stem),
                    "message": "protected_neighbors is required for semantic evaluation",
                }
            )
            return result
        prediction_indexed = image_to_indexed(to_abs_path(project_root, str(sample["prediction_path"])))
        final_size = transform_output_size(transforms, source_size)
        if prediction_indexed.shape != (final_size[1], final_size[0]):
            raise ValueError("prediction_dimension_mismatch_lapa_indexed")
        gold_indexed = image_to_indexed(gold_label_path)
        if gold_indexed.shape != (source_size[1], source_size[0]):
            raise ValueError("lapa_gold_label_dimension_mismatch")
        for class_id in sorted(LAPA_REQUIRED_IDS, key=lambda value: int(value)):
            pred_class = prediction_indexed == int(class_id)
            pred_class = invert_mask_to_source(pred_class, transforms, source_size)
            gold_class = gold_indexed == int(class_id)
            class_metrics = binary_metrics(gold_class, pred_class, boundary_tolerance)
            neighbors = protected.get(class_id, [])
            leakage_den = float(np.count_nonzero(pred_class))
            protected_union = np.zeros_like(pred_class, dtype=bool)
            for neighbor_id in neighbors:
                if str(neighbor_id) not in LAPA_REQUIRED_IDS:
                    raise ValueError(f"protected_neighbor_id_invalid:{neighbor_id}")
                neighbor_mask = gold_indexed == int(neighbor_id)
                protected_union = np.logical_or(protected_union, neighbor_mask)
            leakage_num = float(np.count_nonzero(np.logical_and(pred_class, protected_union)))
            leakage = (leakage_num / leakage_den) if leakage_den else 0.0
            result["classes"].append(
                {
                    "class_id": int(class_id),
                    "class_name": str(taxonomy[class_id]),
                    "metrics": class_metrics,
                    "protected_neighbor_leakage": leakage,
                }
            )
    if mode in ("landmarks", "semantic_and_landmarks"):
        normalization = manifest.get("landmark_normalization")
        if not isinstance(normalization, dict):
            fail_events.append(
                {
                    "code": "lapa_landmark_normalization_missing",
                    "sample_id": sample.get("sample_id", stem),
                    "message": "landmark_normalization with interocular indices and authority is required",
                }
            )
            return result
        if not gold_landmark_path.exists():
            fail_events.append(
                {
                    "code": "lapa_gold_landmarks_missing",
                    "sample_id": sample.get("sample_id", stem),
                    "message": str(gold_landmark_path),
                }
            )
            return result
        pred_landmark_path_raw = sample.get("prediction_landmarks_path")
        if not isinstance(pred_landmark_path_raw, str):
            fail_events.append(
                {
                    "code": "prediction_landmarks_missing",
                    "sample_id": sample.get("sample_id", stem),
                    "message": "prediction_landmarks_path required for landmarks mode",
                }
            )
            return result
        pred_landmark_path = to_abs_path(project_root, pred_landmark_path_raw)
        expected_landmark_sha = sample.get("prediction_landmarks_sha256")
        if not isinstance(expected_landmark_sha, str) or sha256_file(pred_landmark_path) != expected_landmark_sha:
            raise ValueError("prediction_landmarks_sha_mismatch")
        gold_points = parse_landmarks_txt(gold_landmark_path)
        pred_points = parse_landmarks_prediction(pred_landmark_path)
        pred_points = invert_points_to_source(pred_points, transforms, source_size)
        if len(gold_points) != len(pred_points):
            fail_events.append(
                {
                    "code": "landmark_count_mismatch",
                    "sample_id": sample.get("sample_id", stem),
                    "message": f"gold={len(gold_points)} pred={len(pred_points)}",
                }
            )
            return result
        if normalization.get("method") != "interocular_index_pair" or not normalization.get("authority_source"):
            raise ValueError("landmark_normalization_policy_invalid")
        nme, norm_distance = nme_with_normalization(gold_points, pred_points, normalization.get("indices", []))
        result["landmarks"] = {
            "point_count": int(len(gold_points)),
            "normalization_distance": norm_distance,
            "nme": nme,
            "normalization_method": normalization["method"],
            "normalization_authority_source": normalization["authority_source"],
        }
    return result


def evaluate_manifest(
    project_root: Path, manifest_path: Path, out_path: Path, taxonomy_binding_path: Path | None
) -> int:
    evidence: dict[str, Any] = {
        "status": "fail_closed_validation",
        "local_live_boundary": {
            "local_only": True,
            "live_runtime_generation_executed": False,
            "mask_promotion_performed": False,
            "certification_performed": False,
        },
        "sample_results": [],
        "fail_closed_events": [],
        "per_class_metrics": {},
        "landmark_nme_summary": {"sample_count": 0, "mean_nme": None, "max_nme": None},
        "transform_audit": [],
        "split_role_audit": {"seen_splits": [], "mixed_split_detected": False},
        "leakage_audit": {"gold_path_exposure_detected": False, "events": []},
        "claim_boundary": {
            "route_evaluated_only": True,
            "promotion_authorized": False,
            "certification_authorized": False,
        },
    }
    fail_events: list[dict[str, Any]] = evidence["fail_closed_events"]
    try:
        registry_path = project_root / "Plan/10_REGISTRIES/facial_neck_hair_gold_standard_dataset_registry.json"
        protocol_path = project_root / "Plan/Instructions/QA/FACIAL_NECK_HAIR_GOLD_STANDARD_BENCHMARK_PROTOCOL.md"
        manifest = load_json(manifest_path)
        registry = load_json(registry_path)
        taxonomy_binding = load_json(taxonomy_binding_path) if taxonomy_binding_path else None
        protocol_hash = sha256_file(protocol_path)
        manifest_hash = sha256_file(manifest_path)
        registry_hash = sha256_file(registry_path)
        evidence["hashes"] = {
            "manifest_sha256": manifest_hash,
            "registry_sha256": registry_hash,
            "protocol_sha256": protocol_hash,
            "taxonomy_binding_sha256": sha256_file(taxonomy_binding_path) if taxonomy_binding_path else None,
        }
        required_fields = (
            "schema_version",
            "created_at",
            "route_id",
            "route_model_identity",
            "route_configuration_sha256",
            "dataset_id",
            "run_id",
            "producer_contract",
            "samples",
        )
        missing = [field for field in required_fields if field not in manifest]
        if missing:
            raise ValueError(f"manifest_missing_fields:{','.join(missing)}")
        producer = manifest["producer_contract"]
        required_contract = {
            "originals_only": True,
            "gold_paths_exposed_to_route": False,
            "prediction_generated_before_evaluation": True,
        }
        for key, expected in required_contract.items():
            if producer.get(key) is not expected:
                raise ValueError(f"producer_contract_invalid:{key}")
        dataset_id = str(manifest["dataset_id"])
        route_model_identity = manifest["route_model_identity"]
        if not isinstance(route_model_identity, dict) or not route_model_identity.get("model_id"):
            raise ValueError("route_model_identity_invalid")
        model_sha256 = str(route_model_identity.get("model_sha256", "")).lower()
        if len(model_sha256) != 64 or any(char not in "0123456789abcdef" for char in model_sha256):
            raise ValueError("route_model_identity_model_sha256_invalid")
        if not isinstance(manifest["route_configuration_sha256"], str) or len(manifest["route_configuration_sha256"]) != 64:
            raise ValueError("route_configuration_sha256_invalid")
        dataset = None
        for ds in registry.get("datasets", []):
            if ds.get("dataset_id") == dataset_id:
                dataset = ds
                break
        if dataset is None:
            raise ValueError(f"dataset_not_in_registry:{dataset_id}")
        split_role_audit: dict[str, Any] = evidence["split_role_audit"]
        gold_roots: list[Path] = []
        if dataset_id == "lapa":
            split = str(manifest.get("split", "")).strip()
            if split not in ("train", "val", "test"):
                raise ValueError("lapa_requires_split_train_val_or_test")
            split_obj = dataset["splits"][split]
            gold_roots.extend(
                [
                    to_abs_path(project_root, str(split_obj["labels_root"])),
                    to_abs_path(project_root, str(split_obj["landmarks_root"])),
                ]
            )
            split_role_audit["manifest_split"] = split
            split_role_audit["split_role"] = {
                "train": "development",
                "val": "configuration_selection",
                "test": "held_out_reporting_only",
            }[split]
            split_role_audit["tuning_allowed"] = split != "test"
        else:
            gold_roots.append(to_abs_path(project_root, str(dataset.get("gold_annotations_root"))))
        leakage_hits = detect_gold_leakage_strings(manifest, gold_roots)
        if leakage_hits:
            evidence["leakage_audit"]["gold_path_exposure_detected"] = True
            evidence["leakage_audit"]["events"] = leakage_hits
            raise ValueError("manifest_gold_path_exposure_detected")
        samples = manifest.get("samples")
        if not isinstance(samples, list) or not samples:
            raise ValueError("samples_must_be_non_empty_list")
        evaluated_classes = {
            str(class_name)
            for sample in samples
            if isinstance(sample, dict)
            for class_name in sample.get("classes", [])
        }
        neck_novelty_audit = {
            "neck_evaluated": "neck" in evaluated_classes,
            "registered_bisenet_sha256": REGISTERED_BISENET_NECK_MODEL_SHA256,
            "candidate_model_sha256": model_sha256,
            "candidate_model_distinct": model_sha256 != REGISTERED_BISENET_NECK_MODEL_SHA256,
            "fixed_reconstruction_authority_valid": False,
            "result": "not_applicable",
        }
        evidence["neck_candidate_novelty_audit"] = neck_novelty_audit
        if "neck" in evaluated_classes:
            if model_sha256 != REGISTERED_BISENET_NECK_MODEL_SHA256:
                neck_novelty_audit["result"] = "distinct_model_route"
            else:
                authority = manifest.get("neck_candidate_authority")
                implementation_path_value = authority.get("implementation_path") if isinstance(authority, dict) else None
                implementation_path = (
                    to_abs_path(project_root, implementation_path_value)
                    if isinstance(implementation_path_value, str) and implementation_path_value.strip()
                    else None
                )
                declared_implementation_sha256 = (
                    str(authority.get("implementation_sha256", "")).lower()
                    if isinstance(authority, dict)
                    else ""
                )
                observed_implementation_sha256 = (
                    sha256_file(implementation_path)
                    if implementation_path is not None and implementation_path.is_file()
                    else None
                )
                authority_valid = (
                    isinstance(authority, dict)
                    and authority.get("kind") == "fixed_non_gold_reconstruction"
                    and isinstance(authority.get("authority_id"), str)
                    and bool(authority["authority_id"].strip())
                    and implementation_path is not None
                    and implementation_path.is_file()
                    and len(declared_implementation_sha256) == 64
                    and all(char in "0123456789abcdef" for char in declared_implementation_sha256)
                    and observed_implementation_sha256 == declared_implementation_sha256
                    and authority.get("gold_derived") is False
                )
                neck_novelty_audit["fixed_reconstruction_authority_valid"] = authority_valid
                neck_novelty_audit["authority_id"] = authority.get("authority_id") if isinstance(authority, dict) else None
                neck_novelty_audit["implementation_path"] = str(implementation_path) if implementation_path else None
                neck_novelty_audit["declared_implementation_sha256"] = declared_implementation_sha256 or None
                neck_novelty_audit["observed_implementation_sha256"] = observed_implementation_sha256
                neck_novelty_audit["result"] = (
                    "fixed_non_gold_reconstruction" if authority_valid else "blocked_registered_route_reuse"
                )
                if not authority_valid:
                    raise ValueError("neck_candidate_not_distinct_from_registered_route")
        boundary_tolerance = int(manifest.get("boundary_tolerance_pixels", 1))
        if boundary_tolerance < 0 or boundary_tolerance > 10:
            raise ValueError("boundary_tolerance_out_of_range")
        evidence["boundary_tolerance_pixels"] = boundary_tolerance
        route_inputs = producer.get("route_input_image_paths")
        if not isinstance(route_inputs, list) or not all(isinstance(item, str) for item in route_inputs):
            raise ValueError("producer_contract_route_input_image_paths_required")
        declared_sources = {str(to_abs_path(project_root, str(sample.get("source_path", "")))) for sample in samples}
        declared_route_inputs = {str(to_abs_path(project_root, item)) for item in route_inputs}
        if declared_sources != declared_route_inputs:
            raise ValueError("producer_route_inputs_do_not_exactly_match_original_sources")
        if dataset_id == "lapa" and taxonomy_binding is not None:
            if taxonomy_binding.get("dataset_id") != "lapa" or not taxonomy_binding.get("authority_source"):
                raise ValueError("lapa_taxonomy_binding_authority_missing")
        for sample in samples:
            sample_result: dict[str, Any] = {
                "sample_id": sample.get("sample_id"),
                "dataset_id": dataset_id,
                "status": "ok",
            }
            source_path = to_abs_path(project_root, str(sample["source_path"]))
            source_sha = sha256_file(source_path)
            if source_sha != str(sample["source_sha256"]):
                raise ValueError(f"source_sha_mismatch:{sample.get('sample_id')}")
            prediction_path = to_abs_path(project_root, str(sample["prediction_path"]))
            prediction_sha = sha256_path(prediction_path)
            if prediction_sha != str(sample["prediction_sha256"]):
                raise ValueError(f"prediction_sha_mismatch:{sample.get('sample_id')}")
            source_image = Image.open(source_path).convert("RGB")
            source_wh = source_image.size
            if parse_size(sample.get("source_size")) != source_wh:
                raise ValueError(f"source_dimension_mismatch:{sample.get('sample_id')}")
            transforms = sample.get("transforms", [{"op": "identity", "from_size": list(source_wh), "to_size": list(source_wh)}])
            if not isinstance(transforms, list) or not transforms:
                raise ValueError("transforms_must_be_non_empty_list")
            chain_ok, chain_msg, final_size = validate_transform_chain(transforms, source_wh)
            if not chain_ok:
                raise ValueError(chain_msg)
            evidence.setdefault("transform_audit", []).append(
                {"sample_id": sample.get("sample_id"), "source_size": list(source_wh), "prediction_size": list(final_size), "transforms": transforms}
            )
            if dataset_id == "celebamask_hq_shard_0":
                root = to_abs_path(project_root, str(dataset["original_images_root"]))
                if not ensure_under_root(source_path, root):
                    raise ValueError(f"source_not_under_celeb_original_root:{source_path}")
                eval_result = evaluate_celeb_sample(
                    sample, source_path, source_wh, transforms, dataset, project_root, fail_events, boundary_tolerance
                )
                sample_result["evaluation"] = eval_result
            elif dataset_id == "lapa":
                eval_result = evaluate_lapa_sample(
                    manifest,
                    sample,
                    source_path,
                    source_wh,
                    transforms,
                    dataset,
                    project_root,
                    split_role_audit,
                    fail_events,
                    taxonomy_binding,
                    boundary_tolerance,
                )
                sample_result["evaluation"] = eval_result
            else:
                raise ValueError(f"unsupported_dataset:{dataset_id}")
            if fail_events:
                sample_result["status"] = "fail_closed"
            evidence["sample_results"].append(sample_result)
        seen_splits = [entry for entry in split_role_audit.get("seen_splits", []) if entry]
        if seen_splits and len(set(seen_splits)) > 1:
            split_role_audit["mixed_split_detected"] = True
            fail_events.append(
                {"code": "mixed_lapa_split_detected", "sample_id": None, "message": ",".join(sorted(set(seen_splits)))}
            )
        if not fail_events:
            evidence["status"] = "pass"
        per_class, landmark_summary, leakage_summary = build_rollups(evidence["sample_results"])
        evidence["per_class_metrics"] = per_class
        evidence["landmark_nme_summary"] = landmark_summary
        evidence["leakage_audit"].update(leakage_summary)
    except Exception as exc:  # fail closed and persist evidence
        fail_events.append({"code": "exception", "sample_id": None, "message": str(exc)})
        evidence["status"] = "fail_closed_validation"
    write_json(out_path, evidence)
    return 0 if evidence["status"] == "pass" else 2


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate facial gold manifest without running any model route.")
    parser.add_argument("--project-root", required=True, help="Repository root containing registry/protocol and datasets")
    parser.add_argument("--prediction-manifest", required=True, help="JSON manifest produced by prediction stage")
    parser.add_argument("--out", required=True, help="Output JSON evidence path")
    parser.add_argument("--taxonomy-binding", help="Authoritative LaPa semantic taxonomy JSON; not required for landmarks-only")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    project_root = Path(args.project_root).resolve()
    manifest_path = Path(args.prediction_manifest).resolve()
    out_path = Path(args.out).resolve()
    taxonomy_path = Path(args.taxonomy_binding).resolve() if args.taxonomy_binding else None
    return evaluate_manifest(project_root, manifest_path, out_path, taxonomy_path)


if __name__ == "__main__":
    raise SystemExit(main())
