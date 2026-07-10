#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops

from wave70_model_registry import COMFYUI_VENV_PYTHON, first_existing_asset


CLASS_ORDER = (
    "skin", "l_brow", "r_brow", "l_eye", "r_eye", "eye_g", "l_ear", "r_ear", "ear_r",
    "nose", "mouth", "u_lip", "l_lip", "neck", "neck_l", "cloth", "hair", "hat",
)
CLASS_INDEX = {class_name: index for index, class_name in enumerate(CLASS_ORDER, start=1)}
ROUTE_INPUT_SIZE = (512, 512)
TTA_RUNNER = Path(__file__).resolve().with_name("run_wave70_facial_bisenet_inference.py")
SKIN_UNION_SOURCES = ("skin", "l_brow", "r_brow", "l_eye", "r_eye", "nose", "mouth", "u_lip", "l_lip")
# Celeb annotations intentionally overlap nested anatomy and accessories. These
# lists contain only regions where prediction overlap is unambiguously leakage.
PROTECTED_NEIGHBORS = {
    "skin": ["cloth", "hat"],
    "l_brow": ["r_brow", "l_eye", "r_eye", "nose", "mouth", "u_lip", "l_lip", "neck", "cloth", "hat"],
    "r_brow": ["l_brow", "l_eye", "r_eye", "nose", "mouth", "u_lip", "l_lip", "neck", "cloth", "hat"],
    "l_eye": ["r_eye", "l_brow", "r_brow", "nose", "mouth", "u_lip", "l_lip", "neck", "cloth", "hair", "hat"],
    "r_eye": ["l_eye", "l_brow", "r_brow", "nose", "mouth", "u_lip", "l_lip", "neck", "cloth", "hair", "hat"],
    "eye_g": ["l_ear", "r_ear", "ear_r", "neck", "neck_l", "cloth", "hat"],
    "l_ear": ["r_ear", "l_brow", "r_brow", "l_eye", "r_eye", "nose", "mouth", "u_lip", "l_lip", "neck", "cloth", "hat"],
    "r_ear": ["l_ear", "l_brow", "r_brow", "l_eye", "r_eye", "nose", "mouth", "u_lip", "l_lip", "neck", "cloth", "hat"],
    "ear_r": ["eye_g", "l_brow", "r_brow", "l_eye", "r_eye", "nose", "mouth", "u_lip", "l_lip", "neck_l", "cloth", "hat"],
    "nose": ["l_brow", "r_brow", "l_eye", "r_eye", "l_ear", "r_ear", "mouth", "u_lip", "l_lip", "neck", "cloth", "hair", "hat"],
    "mouth": ["l_brow", "r_brow", "l_eye", "r_eye", "l_ear", "r_ear", "nose", "neck", "cloth", "hair", "hat"],
    "u_lip": ["l_brow", "r_brow", "l_eye", "r_eye", "l_ear", "r_ear", "nose", "neck", "cloth", "hair", "hat"],
    "l_lip": ["l_brow", "r_brow", "l_eye", "r_eye", "l_ear", "r_ear", "nose", "neck", "cloth", "hair", "hat"],
    "neck": ["l_brow", "r_brow", "l_eye", "r_eye", "nose", "mouth", "u_lip", "l_lip", "hat"],
    "neck_l": ["eye_g", "ear_r", "l_brow", "r_brow", "l_eye", "r_eye", "nose", "mouth", "u_lip", "l_lip", "hat"],
    "cloth": ["l_brow", "r_brow", "l_eye", "r_eye", "nose", "mouth", "u_lip", "l_lip", "eye_g", "ear_r", "hat"],
    "hair": ["l_eye", "r_eye", "nose", "mouth", "u_lip", "l_lip"],
    "hat": ["l_brow", "r_brow", "l_eye", "r_eye", "nose", "mouth", "u_lip", "l_lip", "neck", "neck_l", "cloth"],
}
ELIGIBLE_MIN = 0
ELIGIBLE_MAX = 1999


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_directory(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(child).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def sha256_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relative(project_root: Path, path: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def parse_ids(raw: str) -> list[int]:
    values = []
    for token in raw.split(","):
        sample_id = int(token.strip())
        if sample_id < ELIGIBLE_MIN or sample_id > ELIGIBLE_MAX:
            raise ValueError(f"sample_id_out_of_eligible_range:{sample_id}")
        if sample_id not in values:
            values.append(sample_id)
    if not values:
        raise ValueError("sample_ids_empty")
    return values


def prepare_route_input(source: Path, destination: Path) -> tuple[tuple[int, int], tuple[int, int]]:
    with Image.open(source) as image:
        source_size = image.size
        prepared = image.convert("RGB").resize(ROUTE_INPUT_SIZE, Image.Resampling.BILINEAR)
        destination.parent.mkdir(parents=True, exist_ok=True)
        prepared.save(destination, format="PNG")
    return source_size, ROUTE_INPUT_SIZE


def normalize_predictions(raw_sample_dir: Path, normalized_dir: Path) -> tuple[list[str], tuple[int, int], list[str]]:
    emitted = sorted(raw_sample_dir.glob("??_*.png"))
    if not emitted:
        raise ValueError(f"route_emitted_no_class_masks:{raw_sample_dir}")
    expected_names = {"00_background.png"}
    expected_names.update(f"{index:02d}_{class_name}.png" for class_name, index in CLASS_INDEX.items())
    unexpected = [path.name for path in emitted if path.name not in expected_names]
    if unexpected:
        raise ValueError(f"route_taxonomy_binding_mismatch:{','.join(unexpected)}")
    with Image.open(emitted[0]) as probe:
        output_size = probe.size
    normalized_dir.mkdir(parents=True, exist_ok=True)
    materialized_empty: list[str] = []
    for class_name in CLASS_ORDER:
        expected_name = f"{CLASS_INDEX[class_name]:02d}_{class_name}.png"
        matches = sorted(raw_sample_dir.glob(f"??_{class_name}.png"))
        destination = normalized_dir / f"{class_name}.png"
        if matches:
            if len(matches) != 1 or matches[0].name != expected_name:
                observed = ",".join(path.name for path in matches)
                raise ValueError(f"route_class_index_name_mismatch:{class_name}:{observed}")
            with Image.open(matches[0]) as image:
                if image.size != output_size:
                    raise ValueError(f"route_output_dimension_mismatch:{matches[0].name}")
                image.convert("L").point(lambda value: 255 if value else 0).save(destination)
        else:
            Image.new("L", output_size, 0).save(destination)
            materialized_empty.append(class_name)
    return list(CLASS_ORDER), output_size, materialized_empty


def materialize_composition(base_dir: Path, output_dir: Path, mode: str) -> dict[str, Any] | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for class_name in CLASS_ORDER:
        source = base_dir / f"{class_name}.png"
        if not source.is_file():
            raise FileNotFoundError(f"base_prediction_class_missing:{class_name}")
        shutil.copy2(source, output_dir / source.name)
    if mode == "none":
        return None
    if mode != "skin_nested_union_v1":
        raise ValueError(f"unsupported_mask_composition:{mode}")
    union: Image.Image | None = None
    input_hashes: dict[str, str] = {}
    expected_size: tuple[int, int] | None = None
    for class_name in SKIN_UNION_SOURCES:
        path = base_dir / f"{class_name}.png"
        input_hashes[class_name] = sha256_file(path)
        with Image.open(path) as image:
            mask = image.convert("L").point(lambda value: 255 if value else 0)
            if expected_size is None:
                expected_size = mask.size
            elif mask.size != expected_size:
                raise ValueError(f"composition_input_dimension_mismatch:{class_name}")
            union = mask.copy() if union is None else ImageChops.lighter(union, mask)
    if union is None:
        raise ValueError("composition_sources_empty")
    output_path = output_dir / "skin.png"
    union.save(output_path)
    return {
        "enabled": True,
        "composition_rule_id": "celeb_skin_nested_union_v1",
        "target_class": "skin",
        "union_sources": list(SKIN_UNION_SOURCES),
        "base_prediction_path": str(base_dir),
        "base_prediction_sha256": sha256_directory(base_dir),
        "composition_input_hashes": input_hashes,
        "base_skin_sha256_preserved": input_hashes["skin"],
        "composition_output_sha256": sha256_file(output_path),
    }


def build_route_spec(inference_mode: str, input_dir: Path, output_dir: Path, checkpoint: Path) -> dict[str, Any]:
    producer_path = Path(__file__).resolve()
    if inference_mode == "single_pass":
        code = (
            "from face_parsing.segment import evaluate\n"
            f"evaluate(r'{input_dir}', r'{output_dir}', r'{checkpoint}', [], False, 'face-parsing-style')\n"
        )
        return {
            "command": [str(COMFYUI_VENV_PYTHON), "-c", code],
            "route_id": "face_parsing.segment.evaluate",
            "configuration_components": [producer_path],
            "inference_metadata": {
                "mode": "single_pass",
                "logit_fusion": "none",
                "spatial_unflip": False,
                "semantic_channel_swaps": [],
            },
        }
    if inference_mode != "hflip_logit_mean":
        raise ValueError(f"unsupported_inference_mode:{inference_mode}")
    if not TTA_RUNNER.is_file():
        raise FileNotFoundError(f"facial_tta_runner_missing:{TTA_RUNNER}")
    return {
        "command": [
            str(COMFYUI_VENV_PYTHON), str(TTA_RUNNER),
            "--input-dir", str(input_dir),
            "--output-dir", str(output_dir),
            "--checkpoint", str(checkpoint),
            "--mode", inference_mode,
            "--device", "cuda",
        ],
        "route_id": "run_wave70_facial_bisenet_inference",
        "configuration_components": [producer_path, TTA_RUNNER],
        "inference_metadata": {
            "mode": "hflip_logit_mean",
            "logit_fusion": "mean",
            "spatial_unflip": True,
            "semantic_channel_swaps": [["l_brow", "r_brow"], ["l_eye", "r_eye"], ["l_ear", "r_ear"]],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run face parsing on eligible originals without reading evaluator truth.")
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main")
    parser.add_argument("--sample-ids", default="0")
    parser.add_argument("--out-manifest", required=True)
    parser.add_argument("--runtime-root")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--inference-mode", choices=("single_pass", "hflip_logit_mean"), default="single_pass")
    parser.add_argument("--mask-composition", choices=("none", "skin_nested_union_v1"), default="none")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    sample_ids = parse_ids(args.sample_ids)
    stamp = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
    runtime_root = (
        Path(args.runtime_root).resolve()
        if args.runtime_root
        else project_root / "runtime_artifacts/mask_factory/facial_original_predictions" / stamp
    )
    input_dir = runtime_root / "original_inputs"
    raw_output_dir = runtime_root / "route_output"
    base_predictions_root = runtime_root / "base_predictions"
    normalized_root = runtime_root / "normalized_predictions"
    input_dir.mkdir(parents=True, exist_ok=True)
    original_root = project_root / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img"
    sources: list[dict[str, Any]] = []
    for sample_id in sample_ids:
        source = original_root / f"{sample_id}.jpg"
        if not source.is_file():
            raise FileNotFoundError(f"eligible_original_missing:{source}")
        isolated = input_dir / f"{sample_id}.png"
        source_size, route_input_size = prepare_route_input(source, isolated)
        sources.append(
            {
                "sample_id": str(sample_id),
                "source": source,
                "isolated": isolated,
                "source_size": source_size,
                "route_input_size": route_input_size,
                "source_sha256": sha256_file(source),
            }
        )

    checkpoint = first_existing_asset("bisenet_face_parsing_checkpoint")
    if checkpoint is None or not checkpoint.is_file():
        raise FileNotFoundError("bisenet_face_parsing_checkpoint_not_found")
    if not COMFYUI_VENV_PYTHON.is_file():
        raise FileNotFoundError(f"comfyui_python_missing:{COMFYUI_VENV_PYTHON}")
    raw_output_dir.mkdir(parents=True, exist_ok=True)
    route_spec = build_route_spec(args.inference_mode, input_dir, raw_output_dir, checkpoint)
    process = subprocess.run(
        route_spec["command"],
        cwd=str(project_root),
        check=False,
        capture_output=True,
        text=True,
        timeout=args.timeout_seconds,
    )
    if process.returncode != 0:
        raise RuntimeError(f"face_parser_failed:{process.returncode}:{process.stderr[-2000:]}")

    samples: list[dict[str, Any]] = []
    route_input_paths: list[str] = []
    for source_record in sources:
        sample_id = source_record["sample_id"]
        raw_sample_dir = raw_output_dir / "masks" / sample_id
        base_dir = base_predictions_root / sample_id
        normalized_dir = normalized_root / sample_id
        classes, output_size, materialized_empty = normalize_predictions(raw_sample_dir, base_dir)
        composition = materialize_composition(base_dir, normalized_dir, args.mask_composition)
        source_size = source_record["source_size"]
        route_input_size = source_record["route_input_size"]
        if output_size != route_input_size:
            raise ValueError(
                f"route_output_size_mismatch:{sample_id}:{output_size[0]}x{output_size[1]}"
                f"!={route_input_size[0]}x{route_input_size[1]}"
            )
        transforms = [{"op": "resize", "from_size": list(source_size), "to_size": list(route_input_size)}]
        protected = {class_name: list(PROTECTED_NEIGHBORS[class_name]) for class_name in classes}
        source_path = relative(project_root, source_record["source"])
        route_input_paths.append(source_path)
        sample_manifest = {
                "sample_id": sample_id,
                "source_path": source_path,
                "source_sha256": source_record["source_sha256"],
                "source_size": list(source_size),
                "isolated_route_input_path": relative(project_root, source_record["isolated"]),
                "isolated_route_input_sha256": sha256_file(source_record["isolated"]),
                "isolated_route_input_size": list(route_input_size),
                "prediction_path": relative(project_root, normalized_dir),
                "prediction_sha256": sha256_directory(normalized_dir),
                "classes": classes,
                "protected_neighbors": protected,
                "transforms": transforms,
                "materialized_empty_route_classes": materialized_empty,
            }
        if composition is not None:
            composition["base_prediction_path"] = relative(project_root, base_dir)
            sample_manifest["composition"] = composition
        samples.append(sample_manifest)

    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
        "route_id": route_spec["route_id"],
        "route_model_identity": {
            "model_id": checkpoint.name,
            "model_sha256": sha256_file(checkpoint),
            "model_path": str(checkpoint),
        },
        "route_configuration_sha256": sha256_files(route_spec["configuration_components"]),
        "route_configuration_components": [
            {"path": relative(project_root, path), "sha256": sha256_file(path)}
            for path in route_spec["configuration_components"]
        ],
        "route_preprocessing": {
            "operation": "bilinear_resize",
            "native_input_size": list(ROUTE_INPUT_SIZE),
            "authority": "face_parsing.segment.vis_parsing_maps 512x512 input contract",
        },
        "route_inference": route_spec["inference_metadata"],
        "route_mask_composition": {
            "mode": args.mask_composition,
            "derived_overlay": args.mask_composition != "none",
            "base_masks_preserved": True,
        },
        "dataset_id": "celebamask_hq_shard_0",
        "run_id": f"facial-original-predictions-{stamp}",
        "boundary_tolerance_pixels": 1,
        "producer_contract": {
            "originals_only": True,
            "gold_paths_exposed_to_route": False,
            "prediction_generated_before_evaluation": True,
            "route_input_image_paths": route_input_paths,
        },
        "route_execution": {
            "python": str(COMFYUI_VENV_PYTHON),
            "returncode": process.returncode,
            "stdout_tail": process.stdout[-2000:],
            "stderr_tail": process.stderr[-2000:],
            "input_count": len(sources),
        },
        "samples": samples,
        "claim_boundary": "Originals-only prediction production; no evaluator truth was read and no mask was promoted.",
    }
    out_manifest = Path(args.out_manifest).resolve()
    write_json(out_manifest, manifest)
    print(json.dumps({"result": "pass_originals_only_predictions", "manifest": str(out_manifest), "samples": sample_ids}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"result": "fail_closed_prediction_producer", "error": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(2)
