#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from produce_wave70_facial_original_predictions import (
    CLASS_ORDER,
    materialize_composition,
    relative,
    sha256_directory,
    sha256_file,
    sha256_files,
    write_json,
)


ALLOWED_MODES = {"u_lip_dilate_exclusive_v1": "u_lip"}


def resolve_project_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (project_root / path).resolve()


def display_path(project_root: Path, path: Path) -> str:
    try:
        return relative(project_root, path)
    except ValueError:
        return str(path.resolve())


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("source_manifest_must_be_object")
    return payload


def compose_manifest(
    project_root: Path,
    source_manifest_path: Path,
    runtime_root: Path,
    out_manifest: Path,
    mode: str,
) -> dict[str, Any]:
    if mode not in ALLOWED_MODES:
        raise ValueError(f"unsupported_candidate_composition:{mode}")
    source_manifest = load_json(source_manifest_path)
    producer_contract = source_manifest.get("producer_contract")
    if not isinstance(producer_contract, dict):
        raise ValueError("source_producer_contract_missing")
    if (
        producer_contract.get("originals_only") is not True
        or producer_contract.get("gold_paths_exposed_to_route") is not False
        or producer_contract.get("prediction_generated_before_evaluation") is not True
    ):
        raise ValueError("source_producer_contract_not_originals_only")
    samples = source_manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("source_samples_missing")

    output_root = runtime_root / "normalized_predictions"
    composed_samples: list[dict[str, Any]] = []
    for source_sample in samples:
        if not isinstance(source_sample, dict) or not source_sample.get("sample_id"):
            raise ValueError("source_sample_invalid")
        source_prediction = resolve_project_path(project_root, str(source_sample.get("prediction_path", "")))
        if not source_prediction.is_dir():
            raise FileNotFoundError(f"source_prediction_directory_missing:{source_prediction}")
        observed_source_hash = sha256_directory(source_prediction)
        if observed_source_hash != source_sample.get("prediction_sha256"):
            raise ValueError(f"source_prediction_hash_mismatch:{source_sample['sample_id']}")
        destination = output_root / str(source_sample["sample_id"])
        if destination.exists() and any(destination.iterdir()):
            raise ValueError(f"candidate_output_directory_not_empty:{source_sample['sample_id']}")
        composition = materialize_composition(source_prediction, destination, mode)
        if composition is None:
            raise ValueError("candidate_composition_record_missing")
        composition["base_prediction_path"] = relative(project_root, source_prediction)
        candidate_sample = copy.deepcopy(source_sample)
        candidate_sample["prediction_path"] = relative(project_root, destination)
        candidate_sample["prediction_sha256"] = sha256_directory(destination)
        candidate_sample["composition"] = composition
        composed_samples.append(candidate_sample)

    composer_path = Path(__file__).resolve()
    producer_path = composer_path.with_name("produce_wave70_facial_original_predictions.py")
    components = [source_manifest_path.resolve(), composer_path, producer_path]
    stamp = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
    candidate_manifest = copy.deepcopy(source_manifest)
    candidate_manifest.update(
        {
            "created_at": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
            "route_id": f"{source_manifest.get('route_id', 'unknown')}.fixed_composition",
            "route_configuration_sha256": sha256_files(components),
            "route_configuration_components": [
                {"path": display_path(project_root, path), "sha256": sha256_file(path)} for path in components
            ],
            "candidate_target_classes": [ALLOWED_MODES[mode]],
            "derived_from_prediction_manifest": {
                "path": display_path(project_root, source_manifest_path),
                "sha256": sha256_file(source_manifest_path),
                "base_route_configuration_sha256": source_manifest.get("route_configuration_sha256"),
                "model_route_rerun": False,
            },
            "run_id": f"facial-fixed-candidate-{mode}-{stamp}",
            "route_mask_composition": {
                "mode": mode,
                "derived_overlay": True,
                "base_masks_preserved": True,
                "target_classes": [ALLOWED_MODES[mode]],
            },
            "route_execution": {
                "model_route_executed": False,
                "reused_hash_verified_predictions": True,
                "input_sample_count": len(composed_samples),
            },
            "samples": composed_samples,
            "claim_boundary": (
                "Fixed non-gold candidate composition over hash-verified originals-only predictions; "
                "no model rerun, evaluator truth access, mask promotion, or certification."
            ),
        }
    )
    write_json(out_manifest, candidate_manifest)
    return candidate_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose a fixed facial candidate from existing predictions only.")
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main")
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--out-manifest", required=True)
    parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), required=True)
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    manifest = compose_manifest(
        project_root,
        Path(args.source_manifest).resolve(),
        Path(args.runtime_root).resolve(),
        Path(args.out_manifest).resolve(),
        args.mode,
    )
    print(
        json.dumps(
            {
                "result": "pass_fixed_non_gold_candidate_composition",
                "manifest": str(Path(args.out_manifest).resolve()),
                "sample_ids": [sample["sample_id"] for sample in manifest["samples"]],
                "candidate_target_classes": manifest["candidate_target_classes"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"result": "fail_closed_candidate_composition", "error": str(exc)}, indent=2))
        raise SystemExit(2)
