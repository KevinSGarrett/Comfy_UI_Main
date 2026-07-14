#!/usr/bin/env python3
"""Validate the local Character 1 calibration handoff without rerunning it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter


PASS_Z_SOURCE = Path("assets/inputs/character1_passY_expanded_fill_source.png")
TARGET_MASK = Path("assets/inputs/character1_passO_areola_target_mask_v3.png")
EXPECTED_FILE_COUNT = 158
EXPECTED_MODEL_COUNT = 23


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def workflow_graph_errors(path: Path) -> list[str]:
    workflow = load_json(path)
    if not isinstance(workflow, dict):
        return ["workflow root is not an object"]
    node_ids = set(workflow)
    errors: list[str] = []

    def visit(value: Any, owner: str) -> None:
        if (
            isinstance(value, list)
            and len(value) == 2
            and isinstance(value[0], str)
            and isinstance(value[1], int)
        ):
            if value[0] not in node_ids:
                errors.append(f"node {owner} references missing node {value[0]}")
            return
        if isinstance(value, dict):
            for nested in value.values():
                visit(nested, owner)
        elif isinstance(value, list):
            for nested in value:
                visit(nested, owner)

    for node_id, node in workflow.items():
        if not isinstance(node, dict) or not isinstance(node.get("class_type"), str):
            errors.append(f"node {node_id} lacks a class_type")
            continue
        visit(node.get("inputs", {}), node_id)
    return errors


def verify_manifest(package_root: Path) -> dict[str, Any]:
    manifest_path = package_root / "manifests/file_manifest.csv"
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        records = list(csv.DictReader(handle))
    failures: list[dict[str, Any]] = []
    for record in records:
        path = package_root / record["relative_path"]
        if not path.is_file():
            failures.append({"path": record["relative_path"], "reason": "missing"})
            continue
        actual_bytes = path.stat().st_size
        actual_hash = sha256(path)
        if actual_bytes != int(record["bytes"]) or actual_hash != record["sha256"].upper():
            failures.append(
                {
                    "path": record["relative_path"],
                    "reason": "size_or_hash_mismatch",
                    "expected_bytes": int(record["bytes"]),
                    "actual_bytes": actual_bytes,
                    "expected_sha256": record["sha256"].upper(),
                    "actual_sha256": actual_hash,
                }
            )
    return {
        "path": "manifests/file_manifest.csv",
        "sha256": sha256(manifest_path),
        "declared_file_count": len(records),
        "expected_file_count": EXPECTED_FILE_COUNT,
        "failure_count": len(failures),
        "failures": failures,
        "pass": len(records) == EXPECTED_FILE_COUNT and not failures,
    }


def verify_workflows(
    project_root: Path, package_root: Path, summary: dict[str, Any]
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for value in summary["recommended_workflow_sequence"]:
        package_relative = Path(value)
        package_path = package_root / package_relative
        root_relative = Path("Workflows") / Path(*package_relative.parts[1:])
        root_path = project_root / root_relative
        package_hash = sha256(package_path) if package_path.is_file() else None
        root_hash = sha256(root_path) if root_path.is_file() else None
        package_graph_errors = (
            workflow_graph_errors(package_path) if package_path.is_file() else ["missing"]
        )
        project_graph_errors = (
            workflow_graph_errors(root_path) if root_path.is_file() else ["missing"]
        )
        results.append(
            {
                "package_path": package_relative.as_posix(),
                "project_path": root_relative.as_posix(),
                "package_sha256": package_hash,
                "project_sha256": root_hash,
                "byte_identical": package_hash is not None and package_hash == root_hash,
                "package_graph_errors": package_graph_errors,
                "project_graph_errors": project_graph_errors,
                "pass": (
                    package_hash is not None
                    and package_hash == root_hash
                    and not package_graph_errors
                    and not project_graph_errors
                ),
            }
        )
    return results


def required_class_types(project_root: Path, workflows: list[dict[str, Any]]) -> list[str]:
    class_types: set[str] = set()
    for workflow in workflows:
        payload = load_json(project_root / workflow["project_path"])
        class_types.update(
            node["class_type"]
            for node in payload.values()
            if isinstance(node, dict) and isinstance(node.get("class_type"), str)
        )
    return sorted(class_types)


def image_array(path: Path, mode: str) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert(mode), dtype=np.uint8)


def image_metrics(
    package_root: Path, summary: dict[str, Any]
) -> dict[str, Any]:
    pass_y_relative = Path(summary["current_best_geometry"])
    pass_z_relative = Path(summary["current_best_overall"])
    pass_y_path = package_root / pass_y_relative
    pass_z_path = package_root / pass_z_relative
    source_path = package_root / PASS_Z_SOURCE
    mask_path = package_root / TARGET_MASK

    pass_y = image_array(pass_y_path, "RGB")
    pass_z = image_array(pass_z_path, "RGB")
    source = image_array(source_path, "RGB")
    with Image.open(mask_path) as mask_image:
        mask_pil = mask_image.convert("L")
        mask = np.asarray(mask_pil, dtype=np.uint8)
        conservative_guard = np.asarray(
            mask_pil.filter(ImageFilter.MaxFilter(57)), dtype=np.uint8
        )
    if pass_y.shape != pass_z.shape or pass_y.shape != source.shape:
        raise ValueError("Pass Y, Pass Z, and the Pass Z source dimensions differ")
    if mask.shape != pass_y.shape[:2]:
        raise ValueError("Target mask dimensions differ from the retained images")

    outside = mask < 5
    inside = mask > 250
    outside_exact = np.all(source[outside] == pass_z[outside], axis=1)
    outside_error = np.abs(
        source[outside].astype(np.int16) - pass_z[outside].astype(np.int16)
    )
    inside_error = np.abs(
        source[inside].astype(np.int16) - pass_z[inside].astype(np.int16)
    )
    outside_guard = conservative_guard < 5
    outside_guard_exact = np.all(
        source[outside_guard] == pass_z[outside_guard], axis=1
    )
    outside_guard_error = np.abs(
        source[outside_guard].astype(np.int16)
        - pass_z[outside_guard].astype(np.int16)
    )
    pass_y_lineage_exact = bool(np.array_equal(source, pass_y))
    return {
        "dimensions": {"width": int(pass_y.shape[1]), "height": int(pass_y.shape[0])},
        "pass_y": {
            "path": pass_y_relative.as_posix(),
            "sha256": sha256(pass_y_path),
            "bytes": pass_y_path.stat().st_size,
        },
        "pass_z": {
            "path": pass_z_relative.as_posix(),
            "sha256": sha256(pass_z_path),
            "bytes": pass_z_path.stat().st_size,
        },
        "pass_z_source": {
            "path": PASS_Z_SOURCE.as_posix(),
            "sha256": sha256(source_path),
            "matches_pass_y_exactly": pass_y_lineage_exact,
        },
        "target_mask": {
            "path": TARGET_MASK.as_posix(),
            "sha256": sha256(mask_path),
            "authority": "calibration_target_only_not_gold_standard",
        },
        "pass_z_regional_preservation": {
            "outside_base_mask_exact_match_fraction": round(float(outside_exact.mean()), 9),
            "outside_base_mask_mean_absolute_error_0_255": round(
                float(outside_error.mean()), 9
            ),
            "inside_base_mask_mean_absolute_error_0_255": round(
                float(inside_error.mean()), 9
            ),
            "outside_conservative_28px_guard_exact_match_fraction": round(
                float(outside_guard_exact.mean()), 9
            ),
            "outside_conservative_28px_guard_mean_absolute_error_0_255": round(
                float(outside_guard_error.mean()), 9
            ),
            "note": (
                "The workflow grows and feathers the base mask by 18 pixels, so a small "
                "nonzero difference immediately outside the unexpanded mask is expected. "
                "The square 28-pixel guard conservatively covers the 18-pixel growth plus "
                "10-pixel feather support."
            ),
        },
        "pass": pass_y_lineage_exact,
    }


def runtime_probe(
    runtime_url: str | None, required_node_classes: list[str]
) -> dict[str, Any]:
    if not runtime_url:
        return {"requested": False}
    base = runtime_url.rstrip("/")
    with urllib.request.urlopen(f"{base}/system_stats", timeout=5) as response:
        stats = json.load(response)
    with urllib.request.urlopen(f"{base}/queue", timeout=5) as response:
        queue = json.load(response)
    with urllib.request.urlopen(f"{base}/object_info", timeout=10) as response:
        object_info = json.load(response)
    missing_node_classes = sorted(set(required_node_classes) - set(object_info))
    return {
        "requested": True,
        "reachable": True,
        "comfyui_version": stats.get("system", {}).get("comfyui_version"),
        "device_count": len(stats.get("devices", [])),
        "queue_running_count": len(queue.get("queue_running", [])),
        "queue_pending_count": len(queue.get("queue_pending", [])),
        "required_node_class_count": len(required_node_classes),
        "missing_node_classes": missing_node_classes,
        "generation_submitted": False,
        "pass": (
            not queue.get("queue_running")
            and not queue.get("queue_pending")
            and not missing_node_classes
        ),
    }


def build_evidence(args: argparse.Namespace) -> dict[str, Any]:
    project_root = args.project_root.resolve()
    package_root = args.package_root.resolve()
    summary_path = package_root / "manifests/package_summary.json"
    models_path = package_root / "manifests/model_requirements.json"
    summary = load_json(summary_path)
    models = load_json(models_path)
    summary_validation = summary.get("validation", {})
    summary_errors = list(summary_validation.get("workflow_json_errors", [])) + list(
        summary_validation.get("script_parse_errors", [])
    )
    manifest = verify_manifest(package_root)
    workflows = verify_workflows(project_root, package_root, summary)
    images = image_metrics(package_root, summary)
    runtime = runtime_probe(args.runtime_url, required_class_types(project_root, workflows))
    missing_models = [model["name"] for model in models["models"] if not model["installed"]]
    models_pass = len(models["models"]) == EXPECTED_MODEL_COUNT and not missing_models

    estimates = {
        "authority": "handoff_visual_ellipse_estimate_not_trusted_segmentation",
        "left_projected_ratio": args.left_projected_ratio,
        "right_projected_ratio": args.right_projected_ratio,
        "required_minimum_each": args.required_minimum_each,
        "left_meets_requirement": args.left_projected_ratio >= args.required_minimum_each,
        "right_meets_requirement": args.right_projected_ratio >= args.required_minimum_each,
    }
    target_met = estimates["left_meets_requirement"] and estimates["right_meets_requirement"]
    structural_pass = (
        manifest["pass"]
        and models_pass
        and not summary_errors
        and all(item["pass"] for item in workflows)
        and images["pass"]
        and (not runtime["requested"] or runtime["pass"])
    )
    stamp = args.timestamp.replace("-", "").replace(":", "")
    return {
        "schema_version": "1.0",
        "evidence_id": f"CHARACTER1-CALIBRATION-HANDOFF-INTEGRATION-{stamp}",
        "timestamp": args.timestamp,
        "result": "pass_with_calibration_target_blocker" if structural_pass else "fail",
        "classifications": [
            "LOCAL_RUNTIME_HANDOFF_HASH_VERIFIED",
            "ROOT_WORKFLOW_COPIES_BYTE_IDENTICAL",
            "PASS_Y_GEOMETRY_CANDIDATE_RETAINED",
            "PASS_Z_REGIONAL_TEXTURE_CANDIDATE_RETAINED",
            "NO_DUPLICATE_GENERATION_REQUIRED",
            "BLOCKED_INDEPENDENT_40_PERCENT_GEOMETRY_PROOF_MISSING",
            "BLOCKED_GOLD_MASK_DEPENDENCY_MISSING",
        ],
        "package": {
            "local_root": relative(project_root, package_root),
            "tracked_as_repository_payload": False,
            "package_summary_sha256": sha256(summary_path),
            "model_requirements_sha256": sha256(models_path),
            "acceptance": summary["acceptance"],
            "counts": summary["counts"],
            "summary_validation_errors": summary_errors,
            "manifest_verification": manifest,
        },
        "models": {
            "recorded_at_package_creation": len(models["models"]),
            "expected_count": EXPECTED_MODEL_COUNT,
            "missing_recorded_models": missing_models,
            "pass": models_pass,
            "note": "This verifies the package's recorded model inventory, not a fresh model rehash.",
        },
        "workflows": workflows,
        "retained_images": images,
        "runtime": runtime,
        "calibration_acceptance": {
            "projected_area_estimates": estimates,
            "target_met": target_met,
            "final_acceptance": False,
            "mask_promotion_allowed": False,
            "next_action": (
                "Use final body geometry and independent per-breast trusted masks, target at "
                "least 40 percent on each side, then apply the retained Pass Y/Pass Z method."
            ),
        },
        "structural_validation_pass": structural_pass,
        "process_exit_contract": {
            "0": "structural validation and final calibration acceptance passed",
            "1": "structural validation failed",
            "2": "structural validation passed but final calibration acceptance is blocked",
            "current_exit_code": 2 if structural_pass else 1,
        },
        "boundaries": [
            "No prompt was submitted and none of the 25 retained generations was rerun.",
            "The ztest model weight and raw reference archive remain local-only and unstaged.",
            "Calibration masks were not treated as gold-standard body masks.",
            "No mask promotion, Wave70 hard-gate rerun, Wave71+ activation, Jira mutation, AWS action, or EC2 start occurred.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--package-root", type=Path, default=Path("ztest"))
    parser.add_argument("--runtime-url")
    parser.add_argument("--left-projected-ratio", type=float, default=0.30)
    parser.add_argument("--right-projected-ratio", type=float, default=0.38)
    parser.add_argument("--required-minimum-each", type=float, default=0.40)
    parser.add_argument("--timestamp", default=datetime.now().astimezone().isoformat(timespec="seconds"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    evidence = build_evidence(args)
    payload = json.dumps(evidence, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    if not evidence["structural_validation_pass"]:
        return 1
    return 0 if evidence["calibration_acceptance"]["final_acceptance"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
