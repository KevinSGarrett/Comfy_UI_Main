#!/usr/bin/env python3
"""Verify the local Character 1 Pass Y/Pass Z pair without forming a Row034 request."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops


CANONICAL_ROOT = Path("C:/Comfy_UI_Main")
INTEGRATION_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Runtime_Readiness/"
    "CHARACTER1_CALIBRATION_HANDOFF_INTEGRATION_20260714T094811-0500.json"
)
RULES_PATH = Path(
    "Plan/10_REGISTRIES/wave64_localized_change_whole_artifact_regression_rules.json"
)
FILE_MANIFEST = Path("manifests/file_manifest.csv")
IMAGE_INVENTORY = Path("manifests/generated_image_inventory.csv")
PASS_Y = Path(
    "assets/outputs/flux_fill_calibration/passY_expanded_flux_fill_areola_00001_.png"
)
PASS_Z = Path(
    "assets/outputs/flux_fill_calibration/"
    "passZ_expanded_reference_texture_finish_00001_.png"
)
PASS_Z_SOURCE = Path("assets/inputs/character1_passY_expanded_fill_source.png")
PASS_Y_WORKFLOW = Path(
    "workflows/regional_detail/character1_flux_fill_areola_reference/"
    "workflow.passY_expanded_geometry.api.json"
)
PASS_Z_WORKFLOW = Path(
    "workflows/regional_detail/character1_flux_fill_areola_reference/"
    "workflow.passZ_expanded_texture_finish.api.json"
)
MISSING_NON_PRIMARY_BINDINGS = (
    "baseline_row033_report",
    "candidate_row033_report",
    "row032_global_audio_report",
    "wave33_preview_qa",
    "baseline_artifact_manifest",
    "candidate_artifact_manifest",
    "failure_record",
    "retest_record",
    "whole_artifact_delta",
    "whole_artifact_review",
    "runtime_proof",
    "change_manifest",
)
MISSING_METADATA = (
    "regression_id",
    "change_id",
    "scene_id",
    "shot_id",
    "take_id",
    "baseline_artifact_id",
    "candidate_artifact_id",
    "baseline_run_id",
    "candidate_run_id",
    "review_run_id",
    "change_kind",
    "audio_change_expected",
    "production_authority_claim",
    "canonical_partitions",
    "target_partition_ids",
    "non_target_partition_ids",
    "attempt_history",
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def resolve_under(root: Path, relative: Path, label: str) -> Path:
    root = root.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes root: {relative}") from exc
    return path


def bind_file(path: Path, relative_to: Path) -> dict[str, Any]:
    before = path.stat()
    if not path.is_file() or before.st_size < 1:
        raise ValueError(f"missing or empty file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f"file changed while hashing: {path}")
    return {
        "path": path.resolve().relative_to(relative_to.resolve()).as_posix(),
        "sha256": digest.hexdigest(),
        "bytes": after.st_size,
    }


def manifest_index(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["relative_path", "bytes", "sha256"]:
            raise ValueError(f"unexpected manifest columns: {path}")
        result: dict[str, dict[str, str]] = {}
        for row in reader:
            key = str(row["relative_path"]).replace("\\", "/")
            if not key or key in result:
                raise ValueError(f"empty or duplicate manifest path: {key}")
            result[key] = row
    return result


def verify_manifest_record(
    index: dict[str, dict[str, str]], relative: Path, binding: dict[str, Any], label: str
) -> dict[str, Any]:
    key = relative.as_posix()
    row = index.get(key)
    if row is None:
        raise ValueError(f"{label} missing manifest record: {key}")
    try:
        recorded_bytes = int(row["bytes"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} invalid byte count: {key}") from exc
    if recorded_bytes != binding["bytes"]:
        raise ValueError(f"{label} byte mismatch: {key}")
    if str(row["sha256"]).lower() != str(binding["sha256"]).lower():
        raise ValueError(f"{label} hash mismatch: {key}")
    return {"manifest_path": key, "sha256_match": True, "bytes_match": True}


def image_delta(baseline_path: Path, candidate_path: Path) -> dict[str, Any]:
    with Image.open(baseline_path) as baseline_image, Image.open(candidate_path) as candidate_image:
        baseline = baseline_image.convert("RGB")
        candidate = candidate_image.convert("RGB")
        if baseline.size != candidate.size:
            raise ValueError(
                f"image dimension mismatch: baseline={baseline.size} candidate={candidate.size}"
            )
        difference = ImageChops.difference(baseline, candidate)
        changed_pixels = sum(
            1 for pixel in difference.get_flattened_data() if pixel != (0, 0, 0)
        )
        channel_absolute_sum = sum(
            value * count for count, value in zip(difference.histogram(), list(range(256)) * 3)
        )
        total_pixels = baseline.width * baseline.height
        return {
            "width": baseline.width,
            "height": baseline.height,
            "pixel_count": total_pixels,
            "changed_pixel_count": changed_pixels,
            "changed_pixel_fraction": changed_pixels / total_pixels,
            "rgb_mean_absolute_error_0_255": channel_absolute_sum / (total_pixels * 3),
            "material_change_observed": changed_pixels > 0,
            "interpretation": "whole_image_material_change_only_not_target_region_correctness",
        }


def require_recorded_binding(
    recorded: Any, actual: dict[str, Any], expected_relative: Path, label: str
) -> None:
    if not isinstance(recorded, dict):
        raise ValueError(f"integration evidence missing {label}")
    if str(recorded.get("path", "")).replace("\\", "/") != expected_relative.as_posix():
        raise ValueError(f"integration evidence path mismatch: {label}")
    if str(recorded.get("sha256", "")).lower() != actual["sha256"].lower():
        raise ValueError(f"integration evidence hash mismatch: {label}")
    if "bytes" in recorded and recorded["bytes"] != actual["bytes"]:
        raise ValueError(f"integration evidence byte mismatch: {label}")


def build_evidence(
    project_root: Path,
    ztest_root: Path,
    integration_path: Path,
    rules_path: Path,
    timestamp: str,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    ztest_root = ztest_root.resolve()
    integration_path = integration_path.resolve()
    rules_path = rules_path.resolve()
    for label, path in (("ztest", ztest_root), ("integration", integration_path), ("rules", rules_path)):
        try:
            path.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(f"{label} path must stay inside project root") from exc

    paths = {
        "pass_y": resolve_under(ztest_root, PASS_Y, "pass_y"),
        "pass_z": resolve_under(ztest_root, PASS_Z, "pass_z"),
        "pass_z_source": resolve_under(ztest_root, PASS_Z_SOURCE, "pass_z_source"),
        "pass_y_workflow": resolve_under(ztest_root, PASS_Y_WORKFLOW, "pass_y_workflow"),
        "pass_z_workflow": resolve_under(ztest_root, PASS_Z_WORKFLOW, "pass_z_workflow"),
    }
    bindings = {name: bind_file(path, ztest_root) for name, path in paths.items()}
    file_manifest_path = resolve_under(ztest_root, FILE_MANIFEST, "file_manifest")
    image_inventory_path = resolve_under(ztest_root, IMAGE_INVENTORY, "image_inventory")
    file_manifest_binding = bind_file(file_manifest_path, project_root)
    image_inventory_binding = bind_file(image_inventory_path, project_root)
    file_records = manifest_index(file_manifest_path)
    inventory_records = manifest_index(image_inventory_path)
    file_manifest_checks = {
        name: verify_manifest_record(file_records, relative, bindings[name], "file_manifest")
        for name, relative in (
            ("pass_y", PASS_Y),
            ("pass_z", PASS_Z),
            ("pass_z_source", PASS_Z_SOURCE),
            ("pass_y_workflow", PASS_Y_WORKFLOW),
            ("pass_z_workflow", PASS_Z_WORKFLOW),
        )
    }
    inventory_checks = {
        name: verify_manifest_record(inventory_records, relative, bindings[name], "image_inventory")
        for name, relative in (("pass_y", PASS_Y), ("pass_z", PASS_Z))
    }

    if bindings["pass_z_source"]["sha256"] != bindings["pass_y"]["sha256"]:
        raise ValueError("Pass Z source does not exactly equal Pass Y")
    if paths["pass_z_source"].read_bytes() != paths["pass_y"].read_bytes():
        raise ValueError("Pass Z source bytes do not exactly equal Pass Y")

    integration = load_json(integration_path)
    retained = integration.get("retained_images")
    acceptance = integration.get("calibration_acceptance")
    if not isinstance(retained, dict) or not isinstance(acceptance, dict):
        raise ValueError("integration evidence retained-image/calibration sections missing")
    require_recorded_binding(retained.get("pass_y"), bindings["pass_y"], PASS_Y, "pass_y")
    require_recorded_binding(retained.get("pass_z"), bindings["pass_z"], PASS_Z, "pass_z")
    require_recorded_binding(
        retained.get("pass_z_source"), bindings["pass_z_source"], PASS_Z_SOURCE, "pass_z_source"
    )
    if retained.get("pass_z_source", {}).get("matches_pass_y_exactly") is not True:
        raise ValueError("integration evidence does not assert exact Pass Y source lineage")
    if acceptance.get("target_met") is not False:
        raise ValueError("integration evidence must retain target_met=false")
    if acceptance.get("mask_promotion_allowed") is not False:
        raise ValueError("integration evidence must retain mask_promotion_allowed=false")

    rules = load_json(rules_path)
    authority_rules = rules.get("authority_rules")
    if not isinstance(authority_rules, dict):
        raise ValueError("Row034 authority rules missing")
    production_objects = authority_rules.get("production_authority_exact_objects")
    fixture_objects = authority_rules.get("fixture_authority_exact_objects")
    if not isinstance(production_objects, list) or not isinstance(fixture_objects, list):
        raise ValueError("Row034 authority arrays missing")
    delta = image_delta(paths["pass_y"], paths["pass_z"])
    if not delta["material_change_observed"]:
        raise ValueError("Pass Y and Pass Z contain no image change")

    stamp = timestamp.replace("-", "").replace(":", "")
    return {
        "schema_version": "1.0",
        "evidence_id": f"W64-ROW034-CHARACTER1-PASSY-PASSZ-READINESS-{stamp}",
        "timestamp": timestamp,
        "result": "blocked_passy_passz_primary_media_verified_row034_request_not_formable",
        "classification": "Blocked_Localized_Change_Production_Review_Proof_Missing",
        "row": {"tracker_id": "TRK-W64-034", "item_id": "ITEM-W64-034"},
        "source_bindings": {
            "integration_evidence": bind_file(integration_path, project_root),
            "row034_rules": bind_file(rules_path, project_root),
            "file_manifest": file_manifest_binding,
            "generated_image_inventory": image_inventory_binding,
            "local_assets": bindings,
        },
        "verification": {
            "file_manifest_records": file_manifest_checks,
            "generated_image_inventory_records": inventory_checks,
            "pass_z_source_matches_pass_y_sha256": True,
            "pass_z_source_matches_pass_y_bytes": True,
            "pass_y_pass_z_delta": delta,
            "integration_target_met": False,
            "integration_mask_promotion_allowed": False,
            "production_authority_object_count": len(production_objects),
            "fixture_authority_object_count": len(fixture_objects),
        },
        "row034_contract_gap": {
            "verified_primary_bindings": ["baseline_primary_media", "candidate_primary_media"],
            "missing_non_primary_bindings": list(MISSING_NON_PRIMARY_BINDINGS),
            "missing_metadata": list(MISSING_METADATA),
            "canonical_visual_partitions_available": False,
            "canonical_audio_partitions_available": False,
            "audio_review_proof_available": False,
            "exact_production_authority_available": len(production_objects) == 1,
            "request_formable": False,
            "strict_producer_invoked": False,
            "strict_evaluator_invoked": False,
        },
        "claim_boundary": {
            "local_calibration_assets_committable": False,
            "target_region_correctness_proven": False,
            "body_mask_or_geometry_authority_proven": False,
            "gold_mask_dependency_cleared": False,
            "mask_promotion_authorized": False,
            "row034_pass_authorized": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activation_authorized": False,
        },
        "next_action": (
            "Obtain one exact Row034 production bundle containing all non-primary bindings, canonical "
            "visual/audio partitions, review/runtime proof, and an exact authority object before invoking "
            "the strict producer or evaluator."
        ),
    }


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=CANONICAL_ROOT)
    parser.add_argument("--ztest-root", type=Path)
    parser.add_argument("--integration-evidence", type=Path)
    parser.add_argument("--rules", type=Path)
    parser.add_argument("--timestamp", default=datetime.now().astimezone().isoformat(timespec="seconds"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracker-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.project_root.resolve()
        ztest = (args.ztest_root or root / "ztest").resolve()
        integration = (args.integration_evidence or root / INTEGRATION_EVIDENCE).resolve()
        rules = (args.rules or root / RULES_PATH).resolve()
        output = args.output.resolve()
        tracker_output = args.tracker_output.resolve()
        for label, path in (("output", output), ("tracker_output", tracker_output)):
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"{label} must stay inside project root") from exc
        evidence = build_evidence(root, ztest, integration, rules, args.timestamp)
        write_atomic(output, evidence)
        write_atomic(tracker_output, evidence)
        print(json.dumps({"result": evidence["result"], "output": str(output)}))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"result": "failed_closed", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
