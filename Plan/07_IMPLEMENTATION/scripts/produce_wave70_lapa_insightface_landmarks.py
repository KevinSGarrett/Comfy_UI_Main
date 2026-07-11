#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np


MODEL_HASHES = {
    "1k3d68.onnx": "df5c06b8a0c12e422b2ed8947b8869faa4105387f199c477af038aa01f9a45cc",
    "2d106det.onnx": "f001b856447c413801ef5c42091ed0cd516fcd21f2d6b79635b1e733a7109dbf",
    "det_10g.onnx": "5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91",
    "genderage.onnx": "4fde69b1c810857b88c64a335084f1c3fe8f01246c9a191b48c7bb756d6652fb",
    "w600k_r50.onnx": "4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43",
}
PROVIDERS = ["CPUExecutionProvider"]
DETECTION_SIZE = [640, 640]
NORMALIZATION_INDICES = [35, 93]
OFFICIAL_LAPA_README = "https://github.com/jd-opensource/lapa-dataset/blob/master/README.md"
OFFICIAL_INSIGHTFACE_MARKUP = (
    "https://github.com/nttstar/insightface-resources/blob/master/alignment/images/2d106markup.jpg"
)
OFFICIAL_MARKUP_SHA256 = "4292c0db899a701e512ff1d724d6fc6070676e9d8cc00e1bb7f7be0252cf75ce"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relative(project_root: Path, path: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def parse_stems(raw: str) -> list[str]:
    stems: list[str] = []
    for token in raw.split(","):
        stem = token.strip()
        if not stem or stem in {".", ".."} or "/" in stem or "\\" in stem:
            raise ValueError(f"sample_stem_invalid:{stem}")
        if stem not in stems:
            stems.append(stem)
    if not stems:
        raise ValueError("sample_stems_empty")
    return stems


def verify_model_assets(model_dir: Path) -> list[dict[str, Any]]:
    records = []
    for name, expected_hash in MODEL_HASHES.items():
        path = model_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"insightface_model_missing:{path}")
        observed_hash = sha256_file(path)
        if observed_hash != expected_hash:
            raise ValueError(f"insightface_model_hash_mismatch:{name}")
        records.append({"name": name, "path": str(path), "bytes": path.stat().st_size, "sha256": observed_hash})
    return records


def route_configuration_sha256(script_hash: str, model_assets: list[dict[str, Any]]) -> str:
    payload = {
        "route": "insightface.FaceAnalysis.buffalo_l.landmark_2d_106",
        "script_sha256": script_hash,
        "providers": PROVIDERS,
        "ctx_id": -1,
        "det_size": DETECTION_SIZE,
        "primary_face_selection": "largest_bbox_then_highest_detection_score",
        "normalization_indices": NORMALIZATION_INDICES,
        "models": [{"name": item["name"], "sha256": item["sha256"]} for item in model_assets],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def face_value(face: Any, name: str) -> Any:
    if hasattr(face, name):
        return getattr(face, name)
    if isinstance(face, dict):
        return face.get(name)
    return None


def choose_primary_face(faces: list[Any]) -> Any | None:
    if not faces:
        return None

    def key(face: Any) -> tuple[float, float]:
        bbox = np.asarray(face_value(face, "bbox"), dtype=np.float64).reshape(-1)
        if len(bbox) != 4 or not np.all(np.isfinite(bbox)):
            return (-1.0, -1.0)
        area = max(0.0, float(bbox[2] - bbox[0])) * max(0.0, float(bbox[3] - bbox[1]))
        score = float(face_value(face, "det_score") or 0.0)
        return (area, score)

    selected = max(faces, key=key)
    return selected if key(selected)[0] > 0.0 else None


def load_source_image(path: Path) -> tuple[np.ndarray, tuple[int, int]]:
    import cv2

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"source_image_decode_failed:{path}")
    height, width = image.shape[:2]
    return image, (width, height)


def run_route(project_root: Path, split: str, stems: list[str], runtime_root: Path, out_manifest: Path) -> dict[str, Any]:
    if split not in {"train", "val", "test"}:
        raise ValueError(f"lapa_split_invalid:{split}")
    source_root = project_root / "MaskedWarehouse" / "LaPa" / split / "images"
    model_root = project_root / "runtime_artifacts" / "mask_factory" / "insightface_models"
    model_dir = model_root / "models" / "buffalo_l"
    markup_path = model_root / "2d106markup_official.jpg"
    if not markup_path.is_file() or sha256_file(markup_path) != OFFICIAL_MARKUP_SHA256:
        raise ValueError("insightface_official_markup_hash_mismatch")
    model_assets = verify_model_assets(model_dir)

    from insightface.app import FaceAnalysis

    app = FaceAnalysis(name="buffalo_l", root=str(model_root), providers=list(PROVIDERS))
    app.prepare(ctx_id=-1, det_size=tuple(DETECTION_SIZE))
    output_dir = runtime_root / "predicted_points"
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("prediction_output_directory_not_empty")

    samples: list[dict[str, Any]] = []
    route_inputs: list[str] = []
    for stem in stems:
        source = source_root / f"{stem}.jpg"
        if not source.is_file():
            raise FileNotFoundError(f"lapa_original_missing:{source}")
        image, source_size = load_source_image(source)
        faces = list(app.get(image))
        face = choose_primary_face(faces)
        if face is None:
            raise ValueError(f"insightface_primary_face_missing:{stem}")
        points = np.asarray(face_value(face, "landmark_2d_106"), dtype=np.float64)
        if points.shape != (106, 2) or not np.all(np.isfinite(points)):
            raise ValueError(f"insightface_landmark_shape_invalid:{stem}:{points.shape}")
        width, height = source_size
        out_of_bounds = int(
            np.logical_or.reduce(
                (points[:, 0] < 0, points[:, 1] < 0, points[:, 0] >= width, points[:, 1] >= height)
            ).sum()
        )
        prediction = output_dir / f"{stem}.json"
        write_json(prediction, [[float(x), float(y)] for x, y in points])
        source_rel = relative(project_root, source)
        prediction_rel = relative(project_root, prediction)
        route_inputs.append(source_rel)
        bbox = np.asarray(face_value(face, "bbox"), dtype=np.float64).reshape(-1)
        samples.append(
            {
                "sample_id": stem,
                "source_path": source_rel,
                "source_sha256": sha256_file(source),
                "source_size": [width, height],
                "prediction_path": prediction_rel,
                "prediction_sha256": sha256_file(prediction),
                "prediction_landmarks_path": prediction_rel,
                "prediction_landmarks_sha256": sha256_file(prediction),
                "mode": "landmarks",
                "transforms": [{"op": "identity", "from_size": [width, height], "to_size": [width, height]}],
                "route_observation": {
                    "detected_face_count": len(faces),
                    "selected_bbox": [float(value) for value in bbox],
                    "selected_detection_score": float(face_value(face, "det_score") or 0.0),
                    "point_count": 106,
                    "out_of_bounds_point_count": out_of_bounds,
                },
            }
        )

    script_path = Path(__file__).resolve()
    script_hash = sha256_file(script_path)
    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
        "route_id": "insightface.FaceAnalysis.buffalo_l.landmark_2d_106",
        "route_model_identity": {
            "model_id": "buffalo_l/2d106det.onnx",
            "model_sha256": MODEL_HASHES["2d106det.onnx"],
        },
        "route_model_assets": [
            {**item, "path": relative(project_root, Path(item["path"]))} for item in model_assets
        ],
        "route_configuration_sha256": route_configuration_sha256(script_hash, model_assets),
        "route_configuration": {
            "script_path": relative(project_root, script_path),
            "script_sha256": script_hash,
            "providers": list(PROVIDERS),
            "ctx_id": -1,
            "det_size": list(DETECTION_SIZE),
            "primary_face_selection": "largest_bbox_then_highest_detection_score",
        },
        "dataset_id": "lapa",
        "split": split,
        "run_id": f"lapa-insightface-106-{split}-{datetime.now(ZoneInfo('America/Chicago')).strftime('%Y%m%dT%H%M%S-0500')}",
        "producer_contract": {
            "originals_only": True,
            "gold_paths_exposed_to_route": False,
            "prediction_generated_before_evaluation": True,
            "route_input_image_paths": route_inputs,
        },
        "landmark_normalization": {
            "method": "interocular_index_pair",
            "indices": list(NORMALIZATION_INDICES),
            "authority_source": (
                f"LaPa official README confirms 106 points ({OFFICIAL_LAPA_README}); InsightFace official ordered "
                f"106-point markup identifies outer eye corners 35 and 93 ({OFFICIAL_INSIGHTFACE_MARKUP}); "
                f"local markup SHA256 {OFFICIAL_MARKUP_SHA256}."
            ),
        },
        "samples": samples,
        "route_execution": {
            "runtime": "ComfyUI/.venv",
            "provider": PROVIDERS[0],
            "model_route_executed": True,
            "sample_count": len(samples),
        },
        "license_boundary": (
            "LaPa and InsightFace supplied/pretrained assets remain local evaluation inputs; verify upstream rights "
            "before redistribution or commercial use."
        ),
        "claim_boundary": (
            "Originals-only local landmark production. Gold landmark files were not read by this producer; "
            "no segmentation mask, route promotion, or certification is claimed."
        ),
    }
    write_json(out_manifest, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Produce hash-bound LaPa InsightFace 106-point predictions.")
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main")
    parser.add_argument("--split", choices=("train", "val", "test"), required=True)
    parser.add_argument("--sample-stems", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--out-manifest", required=True)
    args = parser.parse_args()
    manifest = run_route(
        Path(args.project_root).resolve(),
        args.split,
        parse_stems(args.sample_stems),
        Path(args.runtime_root).resolve(),
        Path(args.out_manifest).resolve(),
    )
    print(
        json.dumps(
            {
                "result": "pass_lapa_insightface_106_originals_only_predictions",
                "split": manifest["split"],
                "sample_ids": [sample["sample_id"] for sample in manifest["samples"]],
                "manifest": str(Path(args.out_manifest).resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"result": "fail_closed_lapa_insightface_106_producer", "error": str(exc)}, indent=2))
        raise SystemExit(2)
