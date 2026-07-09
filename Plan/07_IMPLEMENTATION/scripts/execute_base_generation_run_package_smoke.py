from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

try:
    from PIL import Image, ImageStat
except Exception:  # pragma: no cover - dependency availability is recorded at runtime.
    Image = None
    ImageStat = None


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
COMFY_OUTPUT_ROOT = PROJECT_ROOT / "ComfyUI" / "output"
MATRIX_PARENT = PROJECT_ROOT / "runtime_artifacts/run_package_matrices"
EXECUTION_PARENT = PROJECT_ROOT / "runtime_artifacts/base_generation_local_smoke_execution"
QA_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Workflow_Runtime"
TRACKER_EVIDENCE_DIR = PLAN_ROOT / "Tracker/Evidence"
TZ = ZoneInfo("America/Chicago")


def now_values() -> tuple[datetime, str, str]:
    now = datetime.now(TZ)
    return now, now.strftime("%Y%m%dT%H%M%S-0500"), now.replace(microsecond=0).isoformat()


def latest_matrix_root() -> Path:
    candidates = sorted(
        path for path in MATRIX_PARENT.glob("base_generation_smoke_prompts_*")
        if path.is_dir() and (path / "RUN_PACKAGE_MATRIX_MANIFEST.json").exists()
    )
    if not candidates:
        raise FileNotFoundError("No base_generation_smoke_prompts_* run-package matrix found.")
    return candidates[-1]


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024 * 8), b""):
            digest.update(chunk)
    return digest.hexdigest()


def http_json(method: str, url: str, payload: Any | None = None, timeout: int = 30) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def image_output_paths(history: dict[str, Any], prompt_id: str) -> list[dict[str, str]]:
    prompt_history = history.get(prompt_id, {})
    outputs = prompt_history.get("outputs", {}) if isinstance(prompt_history, dict) else {}
    images: list[dict[str, str]] = []
    if not isinstance(outputs, dict):
        return images
    for node_id, node_output in outputs.items():
        if not isinstance(node_output, dict):
            continue
        for image in node_output.get("images", []) or []:
            if not isinstance(image, dict):
                continue
            images.append({
                "node_id": str(node_id),
                "filename": str(image.get("filename") or ""),
                "subfolder": str(image.get("subfolder") or ""),
                "type": str(image.get("type") or ""),
            })
    return images


def copy_output_image(image_record: dict[str, str], image_dir: Path) -> dict[str, Any]:
    source = COMFY_OUTPUT_ROOT / image_record["subfolder"] / image_record["filename"]
    target = image_dir / image_record["filename"]
    report: dict[str, Any] = {
        **image_record,
        "source_path": rel(source) if source.exists() else str(source),
        "copied_path": None,
        "exists": source.exists(),
        "bytes": None,
        "sha256": None,
        "technical_qa": {
            "png_opened": False,
            "width": None,
            "height": None,
            "mode": None,
            "nonblank_variance_pass": None,
            "errors": [],
        },
        "errors": [],
    }
    if not source.exists():
        report["errors"].append("output_file_missing")
        return report
    image_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    report["copied_path"] = rel(target)
    report["bytes"] = target.stat().st_size
    report["sha256"] = sha256_file(target)
    if Image is None or ImageStat is None:
        report["technical_qa"]["errors"].append("pillow_unavailable")
        return report
    try:
        with Image.open(target) as img:
            stat = ImageStat.Stat(img.convert("RGB"))
            extrema = img.convert("RGB").getextrema()
            variance_pass = any(high > low for low, high in extrema)
            report["technical_qa"].update({
                "png_opened": True,
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
                "channel_means": stat.mean,
                "channel_stddev": stat.stddev,
                "nonblank_variance_pass": variance_pass,
            })
            if img.width <= 0 or img.height <= 0:
                report["technical_qa"]["errors"].append("invalid_dimensions")
            if not variance_pass:
                report["technical_qa"]["errors"].append("blank_or_flat_image")
    except Exception as exc:
        report["technical_qa"]["errors"].append(f"png_open_failed:{type(exc).__name__}:{exc}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane-id", default="sdxl_low_risk_fallback_lane")
    parser.add_argument("--api-url", default="http://127.0.0.1:8188")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--poll-seconds", type=int, default=3)
    args = parser.parse_args()

    _now, stamp, iso_ts = now_values()
    matrix_root = latest_matrix_root()
    package_dir = matrix_root / args.lane_id
    manifest_path = package_dir / "RUN_PACKAGE_MANIFEST.json"
    prompt_request_path = package_dir / "prompt_request.json"
    artifact_root = EXECUTION_PARENT / stamp / args.lane_id
    image_dir = artifact_root / "images"
    evidence_path = QA_DIR / f"BASE_GENERATION_LOCAL_PACKAGE_SMOKE_{args.lane_id}_{stamp}.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / evidence_path.name
    errors: list[str] = []

    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    prompt_request = read_json(prompt_request_path) if prompt_request_path.exists() else {}
    if not manifest_path.exists():
        errors.append("run_package_manifest_missing")
    if not prompt_request_path.exists():
        errors.append("prompt_request_missing")
    if not isinstance(prompt_request, dict) or not isinstance(prompt_request.get("prompt"), dict):
        errors.append("prompt_request_prompt_missing")

    prompt_response: dict[str, Any] | None = None
    history: dict[str, Any] | None = None
    output_reports: list[dict[str, Any]] = []
    prompt_id: str | None = None
    submitted = False
    history_status = "not_started"

    if not errors:
        prepared_request = dict(prompt_request)
        prepared_request["client_id"] = f"codex-local-package-smoke-{args.lane_id}-{stamp}"
        prepared_request["extra_data"] = {
            **(prepared_request.get("extra_data") if isinstance(prepared_request.get("extra_data"), dict) else {}),
            "execution_allowed": True,
            "runtime_execution_evidence_id": f"BASE_GENERATION_LOCAL_PACKAGE_SMOKE_{args.lane_id}_{stamp}",
        }
        write_json(artifact_root / "prompt_request_submitted.json", prepared_request)
        try:
            http_json("GET", f"{args.api_url.rstrip()}/system_stats", timeout=10)
            prompt_response = http_json("POST", f"{args.api_url.rstrip()}/prompt", prepared_request, timeout=30)
            submitted = True
            prompt_id = str(prompt_response.get("prompt_id") or "")
            if not prompt_id:
                errors.append("prompt_response_missing_prompt_id")
            else:
                write_json(artifact_root / "prompt_response.json", prompt_response)
                deadline = time.monotonic() + args.timeout_seconds
                while time.monotonic() < deadline:
                    history_payload = http_json("GET", f"{args.api_url.rstrip()}/history/{prompt_id}", timeout=30)
                    if isinstance(history_payload, dict) and prompt_id in history_payload:
                        images = image_output_paths(history_payload, prompt_id)
                        if images:
                            history = history_payload
                            history_status = "outputs_found"
                            break
                    time.sleep(args.poll_seconds)
                if history is None:
                    history_status = "timeout_or_no_images"
                    errors.append("history_timeout_or_no_images")
                else:
                    write_json(artifact_root / "history.json", history)
                    output_reports = [copy_output_image(image, image_dir) for image in image_output_paths(history, prompt_id)]
        except Exception as exc:
            history_status = "error"
            errors.append(f"runtime_error:{type(exc).__name__}:{exc}")

    failed_outputs = [
        report for report in output_reports
        if report.get("errors") or report.get("technical_qa", {}).get("errors")
    ]
    if output_reports and failed_outputs:
        errors.append("output_technical_qa_gap")

    expected_minimum = int((manifest.get("expected_outputs") or {}).get("minimum_output_count") or 1) if isinstance(manifest, dict) else 1
    if len(output_reports) < expected_minimum:
        errors.append(f"output_count_below_expected:{len(output_reports)}<{expected_minimum}")

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"BASE_GENERATION_LOCAL_PACKAGE_SMOKE_{args.lane_id}_{stamp}",
        "created_iso": iso_ts,
        "lane_id": args.lane_id,
        "api_url": args.api_url,
        "run_package_matrix_root": rel(matrix_root),
        "package_manifest": rel(manifest_path) if manifest_path.exists() else str(manifest_path),
        "prompt_request": rel(prompt_request_path) if prompt_request_path.exists() else str(prompt_request_path),
        "artifact_root": rel(artifact_root),
        "prompt_submitted": submitted,
        "prompt_id": prompt_id,
        "history_status": history_status,
        "prompt_response": prompt_response,
        "output_reports": output_reports,
        "counts": {
            "outputs_found": len(output_reports),
            "failed_output_reports": len(failed_outputs),
            "expected_minimum_output_count": expected_minimum,
        },
        "runtime_boundary": {
            "local_comfyui_only": True,
            "package_prompt_submitted": submitted,
            "generation_executed": history_status == "outputs_found",
            "history_polled": submitted,
            "ec2_started": False,
            "aws_contacted": False,
            "hard_gates_rerun": False,
            "mask_truth_consumed": False,
            "candidate_masks_consumed_as_truth": False,
            "masks_promoted": False,
            "wave71_activation_attempted": False,
        },
        "errors": errors,
    }
    payload["pass"] = not errors and submitted and history_status == "outputs_found" and len(output_reports) >= expected_minimum
    payload["decision"] = "base_generation_local_package_smoke_passed" if payload["pass"] else "blocked_base_generation_local_package_smoke"
    write_json(evidence_path, payload)
    tracker_evidence_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(evidence_path, tracker_evidence_path)
    print(json.dumps({
        "evidence": rel(evidence_path),
        "tracker_evidence": rel(tracker_evidence_path),
        "pass": payload["pass"],
        "decision": payload["decision"],
        "lane_id": args.lane_id,
        "prompt_submitted": submitted,
        "prompt_id": prompt_id,
        "history_status": history_status,
        "counts": payload["counts"],
        "errors": errors,
    }, indent=2))
    return 0 if payload["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
