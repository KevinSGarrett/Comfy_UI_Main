from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
MODEL_ROOT = PROJECT_ROOT / "models"
COMFYUI_INPUT_ROOT = PROJECT_ROOT / "ComfyUI" / "input"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_TS = NOW.replace(microsecond=0).isoformat()

RUN_PACKAGE_MATRIX_PARENT = PROJECT_ROOT / "runtime_artifacts/run_package_matrices"
DEFAULT_MATRIX_ROOT = PROJECT_ROOT / "runtime_artifacts/run_package_matrices/base_generation_smoke_prompts_20260709T004250-0500"
OUT_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Runtime_Readiness"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
OUT_FILE = OUT_DIR / f"BASE_GENERATION_RUN_PACKAGE_ASSET_READINESS_{STAMP}.json"
TRACKER_OUT_FILE = TRACKER_EVIDENCE_DIR / OUT_FILE.name


def latest_run_package_matrix_root() -> Path:
    candidates = sorted(
        path for path in RUN_PACKAGE_MATRIX_PARENT.glob("base_generation_smoke_prompts_*")
        if path.is_dir() and (path / "RUN_PACKAGE_MATRIX_MANIFEST.json").exists()
    )
    return candidates[-1] if candidates else DEFAULT_MATRIX_ROOT


RUN_PACKAGE_MATRIX_ROOT = latest_run_package_matrix_root()
MATRIX_MANIFEST = RUN_PACKAGE_MATRIX_ROOT / "RUN_PACKAGE_MATRIX_MANIFEST.json"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path, cache: dict[Path, str]) -> str:
    resolved = path.resolve()
    if resolved in cache:
        return cache[resolved]
    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024 * 8), b""):
            digest.update(chunk)
    value = digest.hexdigest()
    cache[resolved] = value
    return value


def file_report(path: Path, expected_sha256: str | None, hash_cache: dict[Path, str]) -> dict[str, Any]:
    report: dict[str, Any] = {
        "path": rel(path) if path.exists() else str(path),
        "exists": path.exists(),
        "bytes": None,
        "expected_sha256": expected_sha256,
        "actual_sha256": None,
        "hash_match": None,
        "errors": [],
    }
    if not path.exists():
        report["errors"].append("file_missing")
        return report
    if not path.is_file():
        report["errors"].append("path_not_file")
        return report
    size = path.stat().st_size
    report["bytes"] = size
    if size <= 0:
        report["errors"].append("file_empty")
    if expected_sha256:
        actual = sha256_file(path, hash_cache)
        report["actual_sha256"] = actual
        report["hash_match"] = actual.lower() == expected_sha256.lower()
        if not report["hash_match"]:
            report["errors"].append("sha256_mismatch")
    return report


def model_path(model: dict[str, Any]) -> Path:
    subdir = str(model.get("comfyui_model_subdir") or "").strip("/\\")
    filename = str(model.get("filename") or "")
    return MODEL_ROOT / subdir / filename


def input_asset_path(asset: dict[str, Any]) -> Path:
    comfyui_input_path = str(asset.get("comfyui_input_path") or "")
    if comfyui_input_path:
        normalized = Path(comfyui_input_path.replace("/", "\\"))
        if normalized.is_absolute():
            return normalized
        parts = [part for part in normalized.parts if part not in (".", "")]
        if len(parts) >= 3 and parts[0].lower() == "comfyui" and parts[1].lower() == "input":
            return PROJECT_ROOT.joinpath(*parts)
    subdir = str(asset.get("comfyui_input_subdir") or "").strip("/\\")
    filename = str(asset.get("filename") or "")
    return COMFYUI_INPUT_ROOT / subdir / filename


def validate_package(package_entry: dict[str, Any], hash_cache: dict[Path, str]) -> dict[str, Any]:
    manifest_path = PROJECT_ROOT / str(package_entry["manifest"])
    errors: list[str] = []
    warnings: list[str] = []
    if not manifest_path.exists():
        return {
            "lane_id": package_entry.get("lane_id"),
            "manifest": str(manifest_path),
            "errors": ["run_package_manifest_missing"],
            "pass": False,
        }
    manifest = read_json(manifest_path)
    manifest_hash = sha256_file(manifest_path, hash_cache)
    expected_manifest_hash = package_entry.get("manifest_sha256")
    if expected_manifest_hash and manifest_hash.lower() != str(expected_manifest_hash).lower():
        warnings.append("matrix_manifest_sha256_mismatch_self_referential_manifest_hash")

    model_reports = []
    for model in manifest.get("required_models") or []:
        path = model_path(model)
        report = file_report(path, model.get("sha256"), hash_cache)
        report.update({
            "role": model.get("role"),
            "model_type": model.get("model_type"),
            "comfyui_model_subdir": model.get("comfyui_model_subdir"),
            "filename": model.get("filename"),
            "node_id": model.get("node_id"),
            "node_class": model.get("node_class"),
        })
        model_reports.append(report)

    input_reports = []
    for asset in manifest.get("required_input_assets") or []:
        path = input_asset_path(asset)
        report = file_report(path, asset.get("sha256"), hash_cache)
        report.update({
            "role": asset.get("role"),
            "control_map_type": asset.get("control_map_type"),
            "filename": asset.get("filename"),
            "comfyui_input_path": asset.get("comfyui_input_path"),
            "node_id": asset.get("node_id"),
            "node_class": asset.get("node_class"),
        })
        input_reports.append(report)

    failed_models = [report for report in model_reports if report["errors"]]
    failed_inputs = [report for report in input_reports if report["errors"]]
    if failed_models:
        errors.append("required_model_file_gap")
    if failed_inputs:
        errors.append("required_input_asset_gap")
    if manifest.get("runtime_boundary", {}).get("prompt_submitted") is not False:
        errors.append("runtime_boundary_prompt_submitted_not_false")
    if manifest.get("runtime_boundary", {}).get("generation_executed") is not False:
        errors.append("runtime_boundary_generation_executed_not_false")
    if manifest.get("runtime_boundary", {}).get("ec2_started") is not False:
        errors.append("runtime_boundary_ec2_started_not_false")
    if manifest.get("runtime_boundary", {}).get("aws_contacted") is not False:
        errors.append("runtime_boundary_aws_contacted_not_false")

    return {
        "lane_id": manifest.get("lane_id") or package_entry.get("lane_id"),
        "package_root": manifest.get("package_root"),
        "manifest": rel(manifest_path),
        "expected_manifest_sha256": expected_manifest_hash,
        "actual_manifest_sha256": manifest_hash,
        "required_model_count": len(model_reports),
        "required_input_asset_count": len(input_reports),
        "model_reports": model_reports,
        "input_asset_reports": input_reports,
        "warnings": warnings,
        "errors": errors,
        "pass": not errors,
    }


def main() -> int:
    hash_cache: dict[Path, str] = {}
    matrix_errors: list[str] = []
    matrix_manifest = read_json(MATRIX_MANIFEST) if MATRIX_MANIFEST.exists() else {}
    packages = matrix_manifest.get("packages") if isinstance(matrix_manifest, dict) else None
    if not MATRIX_MANIFEST.exists():
        matrix_errors.append("run_package_matrix_manifest_missing")
        packages = []
    if not isinstance(packages, list):
        matrix_errors.append("run_package_matrix_packages_not_list")
        packages = []

    package_reports = [
        validate_package(package_entry, hash_cache)
        for package_entry in packages
        if isinstance(package_entry, dict)
    ]
    failed = [report for report in package_reports if not report["pass"]]
    unique_required_model_files = sorted({
        report["path"]
        for package in package_reports
        for report in package.get("model_reports", [])
    })
    unique_required_input_files = sorted({
        report["path"]
        for package in package_reports
        for report in package.get("input_asset_reports", [])
    })

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"BASE_GENERATION_RUN_PACKAGE_ASSET_READINESS_{STAMP}",
        "created_iso": ISO_TS,
        "run_package_matrix_root": rel(RUN_PACKAGE_MATRIX_ROOT) if RUN_PACKAGE_MATRIX_ROOT.exists() else str(RUN_PACKAGE_MATRIX_ROOT),
        "run_package_matrix_manifest": rel(MATRIX_MANIFEST) if MATRIX_MANIFEST.exists() else str(MATRIX_MANIFEST),
        "model_root": rel(MODEL_ROOT) if MODEL_ROOT.exists() else str(MODEL_ROOT),
        "comfyui_input_root": rel(COMFYUI_INPUT_ROOT) if COMFYUI_INPUT_ROOT.exists() else str(COMFYUI_INPUT_ROOT),
        "counts": {
            "packages_declared": len(packages),
            "packages_checked": len(package_reports),
            "failed_packages": len(failed),
            "unique_required_model_files": len(unique_required_model_files),
            "unique_required_input_files": len(unique_required_input_files),
            "unique_files_hashed": len(hash_cache),
        },
        "unique_required_model_files": unique_required_model_files,
        "unique_required_input_files": unique_required_input_files,
        "matrix_errors": matrix_errors,
        "package_reports": package_reports,
        "runtime_boundary": {
            "local_file_readiness_only": True,
            "comfyui_contacted": False,
            "object_info_contacted": False,
            "prompt_submitted": False,
            "generation_executed": False,
            "history_polled": False,
            "ec2_started": False,
            "aws_contacted": False,
            "hard_gates_rerun": False,
            "mask_truth_consumed": False,
            "candidate_masks_consumed_as_truth": False,
            "masks_promoted": False,
            "wave71_activation_attempted": False,
        },
    }
    payload["pass"] = not matrix_errors and len(package_reports) == 8 and not failed
    payload["decision"] = "base_generation_run_package_asset_readiness_passed" if payload["pass"] else "blocked_base_generation_run_package_asset_readiness_gap"

    write_json(OUT_FILE, payload)
    TRACKER_OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT_FILE, TRACKER_OUT_FILE)
    print(json.dumps({
        "evidence": rel(OUT_FILE),
        "tracker_evidence": rel(TRACKER_OUT_FILE),
        "pass": payload["pass"],
        "decision": payload["decision"],
        "counts": payload["counts"],
        "failed_lanes": [report["lane_id"] for report in failed],
        "matrix_errors": matrix_errors,
    }, indent=2))
    return 0 if payload["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
