from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_TS = NOW.replace(microsecond=0).isoformat()

API_URL = "http://127.0.0.1:8188"
RUN_PACKAGE_MATRIX_PARENT = PROJECT_ROOT / "runtime_artifacts/run_package_matrices"
DEFAULT_MATRIX_ROOT = PROJECT_ROOT / "runtime_artifacts/run_package_matrices/base_generation_smoke_prompts_20260709T004250-0500"


def latest_run_package_matrix_root() -> Path:
    candidates = sorted(
        path for path in RUN_PACKAGE_MATRIX_PARENT.glob("base_generation_smoke_prompts_*")
        if path.is_dir() and (path / "RUN_PACKAGE_MATRIX_MANIFEST.json").exists()
    )
    return candidates[-1] if candidates else DEFAULT_MATRIX_ROOT


RUN_PACKAGE_MATRIX_ROOT = latest_run_package_matrix_root()
OUT_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Runtime_Readiness"
OUT_FILE = OUT_DIR / f"BASE_GENERATION_RUN_PACKAGE_OBJECT_INFO_{STAMP}.json"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def fetch_object_info() -> tuple[dict[str, Any] | None, str | None]:
    try:
        req = Request(f"{API_URL}/object_info", headers={"Accept": "application/json"})
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8")), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def prompt_node_types(prompt: dict[str, Any]) -> set[str]:
    node_types = set()
    for node in prompt.values():
        if isinstance(node, dict) and node.get("class_type"):
            node_types.add(str(node["class_type"]))
    return node_types


def validate_package(package_dir: Path, visible_node_types: set[str]) -> dict[str, Any]:
    manifest_path = package_dir / "RUN_PACKAGE_MANIFEST.json"
    prompt_path = package_dir / "prompt_only.json"
    errors: list[str] = []
    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    prompt = read_json(prompt_path) if prompt_path.exists() else {}
    node_types = prompt_node_types(prompt) if isinstance(prompt, dict) else set()
    missing = sorted(node_type for node_type in node_types if node_type not in visible_node_types)

    if not manifest_path.exists():
        errors.append("run_package_manifest_missing")
    if not prompt_path.exists():
        errors.append("prompt_only_missing")
    if not isinstance(prompt, dict):
        errors.append("prompt_only_not_object")
    if missing:
        errors.append(f"missing_object_info_node_types:{missing}")
    if manifest.get("runtime_boundary", {}).get("prompt_submitted") is not False:
        errors.append("runtime_boundary_prompt_submitted_not_false")
    if manifest.get("runtime_boundary", {}).get("generation_executed") is not False:
        errors.append("runtime_boundary_generation_executed_not_false")

    return {
        "lane_id": manifest.get("lane_id") or package_dir.name,
        "package_root": rel(package_dir),
        "run_package_manifest": rel(manifest_path) if manifest_path.exists() else str(manifest_path),
        "prompt_only": rel(prompt_path) if prompt_path.exists() else str(prompt_path),
        "prompt_node_types": sorted(node_types),
        "missing_object_info_node_types": missing,
        "errors": errors,
        "pass": not errors,
    }


def main() -> int:
    object_info, fetch_error = fetch_object_info()
    visible_node_types = set(object_info.keys()) if isinstance(object_info, dict) else set()
    package_dirs = sorted(path for path in RUN_PACKAGE_MATRIX_ROOT.iterdir() if path.is_dir()) if RUN_PACKAGE_MATRIX_ROOT.exists() else []
    package_reports = [
        validate_package(package_dir, visible_node_types)
        for package_dir in package_dirs
    ] if fetch_error is None else []
    failed = [report for report in package_reports if not report["pass"]]

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"BASE_GENERATION_RUN_PACKAGE_OBJECT_INFO_{STAMP}",
        "created_iso": ISO_TS,
        "api_url": API_URL,
        "run_package_matrix_root": rel(RUN_PACKAGE_MATRIX_ROOT) if RUN_PACKAGE_MATRIX_ROOT.exists() else str(RUN_PACKAGE_MATRIX_ROOT),
        "object_info": {
            "contacted": fetch_error is None,
            "fetch_error": fetch_error,
            "visible_node_type_count": len(visible_node_types),
            "snapshot_path": None,
        },
        "counts": {
            "package_dirs": len(package_dirs),
            "packages_checked": len(package_reports),
            "failed_packages": len(failed),
        },
        "package_reports": package_reports,
        "runtime_boundary": {
            "object_info_only": True,
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
    snapshot_path = OUT_DIR / f"BASE_GENERATION_RUN_PACKAGE_OBJECT_INFO_SNAPSHOT_{STAMP}.json"
    if object_info is not None:
        write_json(snapshot_path, {
            "schema_version": "wave03.object_info_snapshot.v1",
            "comfyui_api_url": API_URL,
            "captured_iso": ISO_TS,
            "node_type_count": len(visible_node_types),
            "object_info": object_info,
        })
        payload["object_info"]["snapshot_path"] = rel(snapshot_path)

    payload["pass"] = fetch_error is None and len(package_dirs) == 8 and not failed
    payload["decision"] = "base_generation_run_package_object_info_passed" if payload["pass"] else "blocked_base_generation_run_package_object_info_gap"
    write_json(OUT_FILE, payload)
    print(json.dumps({
        "evidence": rel(OUT_FILE),
        "pass": payload["pass"],
        "decision": payload["decision"],
        "object_info_contacted": payload["object_info"]["contacted"],
        "visible_node_type_count": payload["object_info"]["visible_node_type_count"],
        "counts": payload["counts"],
        "failed_lanes": [report["lane_id"] for report in failed],
        "fetch_error": fetch_error,
    }, indent=2))
    return 0 if payload["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
