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

from PIL import Image

from wave70_model_registry import COMFYUI_VENV_PYTHON, first_existing_asset


CLASS_ORDER = (
    "skin", "l_brow", "r_brow", "l_eye", "r_eye", "eye_g", "l_ear", "r_ear", "ear_r",
    "nose", "mouth", "u_lip", "l_lip", "neck", "neck_l", "cloth", "hair", "hat",
)
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


def normalize_predictions(raw_sample_dir: Path, normalized_dir: Path) -> tuple[list[str], tuple[int, int], list[str]]:
    emitted = sorted(raw_sample_dir.glob("??_*.png"))
    if not emitted:
        raise ValueError(f"route_emitted_no_class_masks:{raw_sample_dir}")
    with Image.open(emitted[0]) as probe:
        output_size = probe.size
    normalized_dir.mkdir(parents=True, exist_ok=True)
    materialized_empty: list[str] = []
    for class_name in CLASS_ORDER:
        matches = sorted(raw_sample_dir.glob(f"??_{class_name}.png"))
        destination = normalized_dir / f"{class_name}.png"
        if matches:
            with Image.open(matches[0]) as image:
                if image.size != output_size:
                    raise ValueError(f"route_output_dimension_mismatch:{matches[0].name}")
                image.convert("L").point(lambda value: 255 if value else 0).save(destination)
        else:
            Image.new("L", output_size, 0).save(destination)
            materialized_empty.append(class_name)
    return list(CLASS_ORDER), output_size, materialized_empty


def main() -> int:
    parser = argparse.ArgumentParser(description="Run face parsing on eligible originals without reading evaluator truth.")
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main")
    parser.add_argument("--sample-ids", default="0")
    parser.add_argument("--out-manifest", required=True)
    parser.add_argument("--runtime-root")
    parser.add_argument("--timeout-seconds", type=int, default=300)
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
    normalized_root = runtime_root / "normalized_predictions"
    input_dir.mkdir(parents=True, exist_ok=True)
    original_root = project_root / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img"
    sources: list[dict[str, Any]] = []
    for sample_id in sample_ids:
        source = original_root / f"{sample_id}.jpg"
        if not source.is_file():
            raise FileNotFoundError(f"eligible_original_missing:{source}")
        isolated = input_dir / f"{sample_id}.jpg"
        shutil.copy2(source, isolated)
        if sha256_file(source) != sha256_file(isolated):
            raise ValueError(f"isolated_original_hash_mismatch:{sample_id}")
        with Image.open(source) as image:
            source_size = image.size
        sources.append(
            {
                "sample_id": str(sample_id),
                "source": source,
                "isolated": isolated,
                "source_size": source_size,
                "source_sha256": sha256_file(source),
            }
        )

    checkpoint = first_existing_asset("bisenet_face_parsing_checkpoint")
    if checkpoint is None or not checkpoint.is_file():
        raise FileNotFoundError("bisenet_face_parsing_checkpoint_not_found")
    if not COMFYUI_VENV_PYTHON.is_file():
        raise FileNotFoundError(f"comfyui_python_missing:{COMFYUI_VENV_PYTHON}")
    raw_output_dir.mkdir(parents=True, exist_ok=True)
    code = (
        "from face_parsing.segment import evaluate\n"
        f"evaluate(r'{input_dir}', r'{raw_output_dir}', r'{checkpoint}', [], False, 'face-parsing-style')\n"
    )
    process = subprocess.run(
        [str(COMFYUI_VENV_PYTHON), "-c", code],
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
        normalized_dir = normalized_root / sample_id
        classes, output_size, materialized_empty = normalize_predictions(raw_sample_dir, normalized_dir)
        source_size = source_record["source_size"]
        transforms = (
            [{"op": "identity", "from_size": list(source_size), "to_size": list(source_size)}]
            if output_size == source_size
            else [{"op": "resize", "from_size": list(source_size), "to_size": list(output_size)}]
        )
        protected = {class_name: list(PROTECTED_NEIGHBORS[class_name]) for class_name in classes}
        source_path = relative(project_root, source_record["source"])
        route_input_paths.append(source_path)
        samples.append(
            {
                "sample_id": sample_id,
                "source_path": source_path,
                "source_sha256": source_record["source_sha256"],
                "source_size": list(source_size),
                "isolated_route_input_path": relative(project_root, source_record["isolated"]),
                "isolated_route_input_sha256": sha256_file(source_record["isolated"]),
                "prediction_path": relative(project_root, normalized_dir),
                "prediction_sha256": sha256_directory(normalized_dir),
                "classes": classes,
                "protected_neighbors": protected,
                "transforms": transforms,
                "materialized_empty_route_classes": materialized_empty,
            }
        )

    script_path = Path(__file__).resolve()
    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
        "route_id": "face_parsing.segment.evaluate",
        "route_model_identity": {
            "model_id": checkpoint.name,
            "model_sha256": sha256_file(checkpoint),
            "model_path": str(checkpoint),
        },
        "route_configuration_sha256": sha256_file(script_path),
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
