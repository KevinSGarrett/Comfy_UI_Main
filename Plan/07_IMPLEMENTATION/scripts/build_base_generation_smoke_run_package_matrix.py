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
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_TS = NOW.replace(microsecond=0).isoformat()

MATERIALIZATION_PARENT = PROJECT_ROOT / "runtime_artifacts/base_generation_smoke_prompt_materialization"


def latest_materialization_root() -> Path:
    candidates = sorted(
        path for path in MATERIALIZATION_PARENT.glob("*")
        if path.is_dir() and list(path.glob("*/PROMPT_MATERIALIZATION_MANIFEST.json"))
    )
    return candidates[-1] if candidates else MATERIALIZATION_PARENT / "20260709T003924-0500"


MATERIALIZATION_ROOT = latest_materialization_root()
RUN_PACKAGE_ROOT = PROJECT_ROOT / f"runtime_artifacts/run_package_matrices/base_generation_smoke_prompts_{STAMP}"
QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Workflow_Static_Validation"
OUT_FILE = QA_DIR / f"BASE_GENERATION_SMOKE_RUN_PACKAGE_MATRIX_{STAMP}.json"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(src: Path, dst: Path) -> dict[str, Any]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {"path": rel(dst), "sha256": sha256_file(dst), "bytes": dst.stat().st_size}


def package_lane(materialization_manifest_path: Path) -> dict[str, Any]:
    materialization = read_json(materialization_manifest_path)
    lane_id = str(materialization["lane_id"])
    package_dir = RUN_PACKAGE_ROOT / lane_id
    lane_files_dir = package_dir / "lane_files"
    errors: list[str] = []

    copied = {
        "prompt_request": copy_file(PROJECT_ROOT / materialization["prompt_request"], package_dir / "prompt_request.json"),
        "prompt_only": copy_file(PROJECT_ROOT / materialization["prompt_only"], package_dir / "prompt_only.json"),
        "materialization_manifest": copy_file(materialization_manifest_path, package_dir / "PROMPT_MATERIALIZATION_MANIFEST.json"),
        "workflow": copy_file(PROJECT_ROOT / materialization["workflow"], lane_files_dir / "workflow.api.json"),
        "smoke_request": copy_file(PROJECT_ROOT / materialization["smoke_request"], lane_files_dir / "smoke_test_request.json"),
        "patch_points": copy_file(PROJECT_ROOT / materialization["patch_points"], lane_files_dir / "patch_points.json"),
        "runtime_requirements": copy_file(PROJECT_ROOT / materialization["runtime_requirements"], lane_files_dir / "runtime_requirements.json"),
    }

    prompt_request = read_json(package_dir / "prompt_request.json")
    dry_run_checks = {
        "prompt_request_json_valid": isinstance(prompt_request, dict),
        "prompt_key_present": isinstance(prompt_request, dict) and isinstance(prompt_request.get("prompt"), dict),
        "client_id_present": isinstance(prompt_request, dict) and bool(prompt_request.get("client_id")),
        "execution_flag_false": prompt_request.get("extra_data", {}).get("execution_allowed") is False if isinstance(prompt_request, dict) else False,
        "materialization_passed": materialization.get("pass") is True,
        "materialization_errors_empty": materialization.get("errors") == [],
    }
    for key, passed in dry_run_checks.items():
        if not passed:
            errors.append(f"dry_run_check_failed:{key}")

    smoke_dry_run = {
        "schema_version": "1.0",
        "lane_id": lane_id,
        "created_iso": ISO_TS,
        "checks": dry_run_checks,
        "runtime_boundary": {
            "dry_run_only": True,
            "prompt_submitted": False,
            "comfyui_contacted": False,
            "generation_executed": False,
            "ec2_started": False,
            "aws_contacted": False,
        },
        "errors": errors,
        "pass": not errors,
    }
    write_json(package_dir / "smoke_dry_run.json", smoke_dry_run)

    static_validation = {
        "schema_version": "1.0",
        "lane_id": lane_id,
        "created_iso": ISO_TS,
        "package_files_exist": all((package_dir / name).exists() for name in ["prompt_request.json", "prompt_only.json", "PROMPT_MATERIALIZATION_MANIFEST.json", "smoke_dry_run.json"]),
        "lane_files_exist": all((lane_files_dir / name).exists() for name in ["workflow.api.json", "smoke_test_request.json", "patch_points.json", "runtime_requirements.json"]),
        "source_hashes": {
            "workflow": materialization.get("workflow_sha256"),
            "smoke_request": materialization.get("smoke_request_sha256"),
            "patch_points": materialization.get("patch_points_sha256"),
            "runtime_requirements": materialization.get("runtime_requirements_sha256"),
            "prompt_request": materialization.get("prompt_request_sha256"),
        },
        "copied_hashes": copied,
        "errors": errors,
        "pass": not errors,
    }
    write_json(package_dir / "static_validation.json", static_validation)

    run_package_manifest = {
        "schema_version": "1.0",
        "package_id": f"base_generation_smoke_prompt_{lane_id}_{STAMP}",
        "lane_id": lane_id,
        "created_iso": ISO_TS,
        "package_root": rel(package_dir),
        "source_materialization_manifest": rel(materialization_manifest_path),
        "files": {
            "prompt_request": copied["prompt_request"],
            "prompt_only": copied["prompt_only"],
            "smoke_dry_run": {"path": rel(package_dir / "smoke_dry_run.json"), "sha256": sha256_file(package_dir / "smoke_dry_run.json")},
            "static_validation": {"path": rel(package_dir / "static_validation.json"), "sha256": sha256_file(package_dir / "static_validation.json")},
            "materialization_manifest": copied["materialization_manifest"],
            "lane_files": {
                "workflow": copied["workflow"],
                "smoke_request": copied["smoke_request"],
                "patch_points": copied["patch_points"],
                "runtime_requirements": copied["runtime_requirements"],
            },
        },
        "expected_outputs": materialization.get("expected_outputs"),
        "required_models": materialization.get("required_models"),
        "required_input_assets": materialization.get("required_input_assets"),
        "runtime_boundary": {
            "dry_run_only": True,
            "prompt_submitted": False,
            "comfyui_contacted": False,
            "generation_executed": False,
            "ec2_started": False,
            "aws_contacted": False,
            "masks_promoted": False,
            "candidate_masks_consumed_as_truth": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
        "pass": not errors,
    }
    write_json(package_dir / "RUN_PACKAGE_MANIFEST.json", run_package_manifest)
    run_package_manifest["manifest_sha256"] = sha256_file(package_dir / "RUN_PACKAGE_MANIFEST.json")
    write_json(package_dir / "RUN_PACKAGE_MANIFEST.json", run_package_manifest)
    return run_package_manifest


def main() -> int:
    manifests = sorted(MATERIALIZATION_ROOT.glob("*/PROMPT_MATERIALIZATION_MANIFEST.json"))
    lane_packages = [package_lane(path) for path in manifests]
    failed = [package for package in lane_packages if not package.get("pass")]
    matrix_manifest = {
        "schema_version": "1.0",
        "evidence_id": f"BASE_GENERATION_SMOKE_RUN_PACKAGE_MATRIX_{STAMP}",
        "created_iso": ISO_TS,
        "source_materialization_root": rel(MATERIALIZATION_ROOT),
        "run_package_matrix_root": rel(RUN_PACKAGE_ROOT),
        "counts": {
            "source_materialization_manifests": len(manifests),
            "packages_built": len(lane_packages),
            "failed_packages": len(failed),
        },
        "packages": [
            {
                "lane_id": package["lane_id"],
                "package_id": package["package_id"],
                "package_root": package["package_root"],
                "manifest": f"{package['package_root']}/RUN_PACKAGE_MANIFEST.json",
                "manifest_sha256": package["manifest_sha256"],
                "pass": package["pass"],
                "errors": package["errors"],
            }
            for package in lane_packages
        ],
        "runtime_boundary": {
            "dry_run_only": True,
            "prompt_submitted": False,
            "comfyui_contacted": False,
            "generation_executed": False,
            "ec2_started": False,
            "aws_contacted": False,
            "hard_gates_rerun": False,
            "mask_truth_consumed": False,
            "candidate_masks_consumed_as_truth": False,
            "masks_promoted": False,
            "wave71_activation_attempted": False,
        },
    }
    matrix_manifest["pass"] = not failed and len(manifests) == 8
    matrix_manifest["decision"] = "base_generation_smoke_run_package_matrix_passed" if matrix_manifest["pass"] else "blocked_base_generation_smoke_run_package_matrix_gap"
    write_json(RUN_PACKAGE_ROOT / "RUN_PACKAGE_MATRIX_MANIFEST.json", matrix_manifest)
    matrix_manifest["run_package_matrix_manifest_sha256"] = sha256_file(RUN_PACKAGE_ROOT / "RUN_PACKAGE_MATRIX_MANIFEST.json")
    write_json(RUN_PACKAGE_ROOT / "RUN_PACKAGE_MATRIX_MANIFEST.json", matrix_manifest)
    write_json(OUT_FILE, matrix_manifest)
    print(json.dumps({
        "evidence": rel(OUT_FILE),
        "pass": matrix_manifest["pass"],
        "decision": matrix_manifest["decision"],
        "run_package_matrix_root": rel(RUN_PACKAGE_ROOT),
        "counts": matrix_manifest["counts"],
        "failed_lanes": [package["lane_id"] for package in failed],
    }, indent=2))
    return 0 if matrix_manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
