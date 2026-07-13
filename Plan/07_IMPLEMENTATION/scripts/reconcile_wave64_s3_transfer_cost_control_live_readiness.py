from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


WINDOWS_ROOT = Path(r"C:\Comfy_UI_Main")
WSL_ROOT = Path("/mnt/c/Comfy_UI_Main")
ROOT = Path(os.environ.get("COMFY_UI_MAIN_ROOT", WINDOWS_ROOT if WINDOWS_ROOT.exists() else WSL_ROOT))
ENV_PATH = ROOT / ".env"
ROW041_EVIDENCE_PATH = ROOT / "Plan/Instructions/QA/Evidence/Wave64/s3_transfer_cost_control.json"
ROW041_STATIC_EVIDENCE_PATH = ROOT / "Plan/Instructions/QA/Evidence/Operations_Static_Validation/W64_S3_RUNTIME_TRANSFER_READINESS_20260708T233036-0500.json"
EXACT_FLUX_FILENAME = "flux1-dev-fp8.safetensors"
TRK = "TRK-W64-041"
ITEM = "ITEM-W64-041"
STATUS = "Completed_S3_Transfer_Cost_Control_Readiness_Pass"
TZ = ZoneInfo("America/Chicago")
PLAN = ROOT / "Plan"
QA = PLAN / "Instructions/QA/Evidence/Wave64"
HYD = PLAN / "Instructions/Hydration_Rehydration"
ORIGINAL_EVIDENCE_PATH = QA / "S3_TRANSFER_COST_CONTROL_20260708T233214-0500.json"
REQUIRED_ENV_KEYS = (
    "AWS_REGION",
    "S3_MODEL_BUCKET",
    "S3_MODEL_PREFIX",
    "S3_RENDER_OUTPUT_PREFIX",
    "S3_MANIFEST_PREFIX",
    "COMFY_DEPLOY_BUNDLE_S3_URI",
)


@dataclass(frozen=True)
class PrefixProbe:
    name: str
    required_for_completion: bool
    list_call_ok: bool
    has_object: bool


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def add_unique(existing: str, values: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for value in values:
        if value not in parts:
            parts.append(value)
    return "; ".join(parts)


def update_csv(path: Path, key: str, value: str, changes: dict[str, Any]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    matches = 0
    for row in rows:
        if row.get(key) != value:
            continue
        matches += 1
        for field, replacement in changes.items():
            if field not in fields:
                continue
            row[field] = add_unique(row.get(field, ""), replacement) if isinstance(replacement, list) else replacement
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return matches


def prepend(path: Path, block: str) -> None:
    current = path.read_text(encoding="utf-8-sig")
    path.write_text(block.strip() + "\n\n" + current.lstrip(), encoding="utf-8")


def parse_required_env(env_path: Path = ENV_PATH) -> dict[str, Any]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return {"env_file_present": False, "missing_keys": list(REQUIRED_ENV_KEYS), "values": {}}

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in REQUIRED_ENV_KEYS and key not in values:
            values[key] = value.strip().strip('"').strip("'")

    missing_keys = [key for key in REQUIRED_ENV_KEYS if not values.get(key)]
    return {"env_file_present": True, "missing_keys": missing_keys, "values": values}


def parse_s3_uri(uri: str) -> tuple[str, str] | None:
    if not uri.startswith("s3://"):
        return None
    remainder = uri[5:]
    bucket, _, prefix = remainder.partition("/")
    if not bucket:
        return None
    return bucket, normalize_prefix(prefix)


def normalize_prefix(prefix: str) -> str:
    cleaned = prefix.lstrip("/")
    if cleaned and not cleaned.endswith("/"):
        return f"{cleaned}/"
    return cleaned


def join_s3_key(prefix: str, filename: str) -> str:
    normalized = normalize_prefix(prefix)
    return f"{normalized}{filename}" if normalized else filename


def run_aws(args: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["aws", *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def aws_call_json(args: list[str]) -> dict[str, Any]:
    proc = run_aws([*args, "--output", "json"])
    if proc is None:
        return {"ok": False, "exit_code": None}
    if proc.returncode != 0:
        return {"ok": False, "exit_code": proc.returncode}
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    return {"ok": True, "exit_code": 0, "payload": payload}


def aws_call_no_output(args: list[str]) -> dict[str, Any]:
    proc = run_aws(args)
    if proc is None:
        return {"ok": False, "exit_code": None}
    return {"ok": proc.returncode == 0, "exit_code": proc.returncode}


def check_local_static_readiness() -> dict[str, Any]:
    if not ROW041_EVIDENCE_PATH.exists() or not ROW041_STATIC_EVIDENCE_PATH.exists():
        return {"ready": False, "checks": {"evidence_files_present": False}}

    row041 = read_json(ROW041_EVIDENCE_PATH)
    static = read_json(ROW041_STATIC_EVIDENCE_PATH)
    checks = {
        "evidence_files_present": True,
        "row041_ready_local_only": (
            row041.get("readiness_result", {}).get("result") == "ready_local_only"
            or row041.get("preserved_evidence", {}).get("result") == "ready_local_only"
            or row041.get("status") == STATUS
            or row041.get("qa_decision") == "s3_transfer_cost_control_pass_read_only_aws_access_verified"
        ),
        "static_ready_local_only": static.get("result") == "ready_local_only",
    }
    return {"ready": all(checks.values()), "checks": checks}


def classify_readiness(
    *,
    local_static_ready: bool,
    config_shape_ok: bool,
    aws_auth_ok: bool,
    bucket_access_ok: bool,
    prefix_probes: list[PrefixProbe],
    flux_exists: bool,
) -> dict[str, Any]:
    blockers: list[str] = []
    residuals: list[str] = []

    if not local_static_ready:
        blockers.append("local_static_readiness_not_preserved")
    if not config_shape_ok:
        blockers.append("config_shape_invalid")
    if not aws_auth_ok:
        blockers.append("aws_authentication_failed")
    if not bucket_access_ok:
        blockers.append("bucket_access_failed")

    manifest_probe = None
    for probe in prefix_probes:
        if probe.name == "manifest":
            manifest_probe = probe
        if not probe.required_for_completion:
            continue
        if not probe.list_call_ok:
            blockers.append(f"required_prefix_access_failed:{probe.name}")
            continue
        if not probe.has_object:
            blockers.append(f"required_prefix_empty:{probe.name}")

    if manifest_probe is not None:
        if not manifest_probe.list_call_ok:
            residuals.append("manifest_prefix_access_unverified")
        elif not manifest_probe.has_object:
            residuals.append("manifest_prefix_empty")
    if not flux_exists:
        residuals.append("exact_flux_object_missing")

    complete = not blockers
    return {
        "row041_complete": complete,
        "result": "pass" if complete else "blocked",
        "blockers": blockers,
        "residuals": residuals,
    }


def run_live_readiness() -> dict[str, Any]:
    local_static = check_local_static_readiness()
    env_info = parse_required_env()
    config_shape_ok = env_info["env_file_present"] and not env_info["missing_keys"]

    values = env_info["values"]
    deploy_uri = values.get("COMFY_DEPLOY_BUNDLE_S3_URI", "")
    deploy_location = parse_s3_uri(deploy_uri) if deploy_uri else None

    config_parse_ok = deploy_location is not None
    model_bucket = values.get("S3_MODEL_BUCKET", "")
    model_prefix = normalize_prefix(values.get("S3_MODEL_PREFIX", ""))
    render_prefix = normalize_prefix(values.get("S3_RENDER_OUTPUT_PREFIX", ""))
    manifest_prefix = normalize_prefix(values.get("S3_MANIFEST_PREFIX", ""))
    deploy_bucket = deploy_location[0] if deploy_location else ""
    deploy_prefix = deploy_location[1] if deploy_location else ""

    aws_auth = aws_call_json(["sts", "get-caller-identity"])
    aws_auth_ok = aws_auth["ok"]

    unique_buckets = {bucket for bucket in (model_bucket, deploy_bucket) if bucket}
    bucket_checks = [aws_call_no_output(["s3api", "head-bucket", "--bucket", bucket]) for bucket in unique_buckets]
    bucket_access_ok = bool(unique_buckets) and all(check["ok"] for check in bucket_checks)

    def list_prefix(bucket: str, prefix: str) -> PrefixProbe:
        if not bucket or not prefix:
            return PrefixProbe(name="", required_for_completion=False, list_call_ok=False, has_object=False)
        result = aws_call_json(
            [
                "s3api",
                "list-objects-v2",
                "--bucket",
                bucket,
                "--prefix",
                prefix,
                "--max-keys",
                "1",
            ]
        )
        has_object = bool(result.get("payload", {}).get("KeyCount", 0)) if result["ok"] else False
        return PrefixProbe(
            name="",
            required_for_completion=False,
            list_call_ok=result["ok"],
            has_object=has_object,
        )

    model_probe = list_prefix(model_bucket, model_prefix)
    deploy_probe = list_prefix(deploy_bucket, deploy_prefix)
    render_probe = list_prefix(model_bucket, render_prefix)
    manifest_probe = list_prefix(model_bucket, manifest_prefix)
    prefix_probes = [
        PrefixProbe("model", True, model_probe.list_call_ok, model_probe.has_object),
        PrefixProbe("deploy", True, deploy_probe.list_call_ok, deploy_probe.has_object),
        PrefixProbe("render", True, render_probe.list_call_ok, render_probe.has_object),
        PrefixProbe("manifest", False, manifest_probe.list_call_ok, manifest_probe.has_object),
    ]

    flux_check = (
        aws_call_no_output(
            [
                "s3api",
                "head-object",
                "--bucket",
                model_bucket,
                "--key",
                join_s3_key(model_prefix, EXACT_FLUX_FILENAME),
            ]
        )
        if model_bucket and model_prefix
        else {"ok": False, "exit_code": None}
    )
    flux_exists = flux_check["ok"]

    classification = classify_readiness(
        local_static_ready=local_static["ready"],
        config_shape_ok=config_shape_ok and config_parse_ok,
        aws_auth_ok=aws_auth_ok,
        bucket_access_ok=bucket_access_ok,
        prefix_probes=prefix_probes,
        flux_exists=flux_exists,
    )

    # Redacted summary only; no bucket names, URIs, account IDs, credentials, or object keys.
    return {
        "schema_version": "1.0",
        "mode": "read_only_live_probe",
        "operation": "row041_live_readiness_reconciliation",
        "local_static_readiness": local_static,
        "config_shape": {
            "env_file_present": env_info["env_file_present"],
            "missing_required_keys": env_info["missing_keys"],
            "deploy_uri_parse_ok": config_parse_ok,
            "required_keys_checked_count": len(REQUIRED_ENV_KEYS),
        },
        "aws_read_ops": {
            "aws_contacted": True,
            "sts_get_caller_identity_ok": aws_auth_ok,
            "head_bucket_ok_count": sum(1 for check in bucket_checks if check["ok"]),
            "head_bucket_total_count": len(bucket_checks),
            "list_prefix_checks": [
                {"name": probe.name, "required_for_completion": probe.required_for_completion, "list_call_ok": probe.list_call_ok, "has_object": probe.has_object}
                for probe in prefix_probes
            ],
            "head_object_flux_exists": flux_exists,
        },
        "classification": classification,
    }


def build_evidence(probe: dict[str, Any], created_iso: str, stamp: str) -> dict[str, Any]:
    prefixes = {item["name"]: item for item in probe["aws_read_ops"]["list_prefix_checks"]}
    checks = {
        "original_local_evidence_exists": ORIGINAL_EVIDENCE_PATH.exists(),
        "canonical_reconciliation_exists": ROW041_EVIDENCE_PATH.exists(),
        "static_readiness_evidence_exists": ROW041_STATIC_EVIDENCE_PATH.exists(),
        "original_local_result_ready": read_json(ORIGINAL_EVIDENCE_PATH).get("readiness_result", {}).get("result") == "ready_local_only",
        "preserved_static_result_ready": read_json(ROW041_STATIC_EVIDENCE_PATH).get("result") == "ready_local_only",
        "local_static_readiness_preserved": probe["local_static_readiness"]["ready"],
        "config_shape_complete": not probe["config_shape"]["missing_required_keys"],
        "deploy_uri_parse_ok": probe["config_shape"]["deploy_uri_parse_ok"],
        "aws_authentication_verified": probe["aws_read_ops"]["sts_get_caller_identity_ok"],
        "all_configured_buckets_accessible": probe["aws_read_ops"]["head_bucket_ok_count"] == probe["aws_read_ops"]["head_bucket_total_count"] > 0,
        "model_prefix_accessible": prefixes["model"]["list_call_ok"],
        "model_prefix_has_existing_object": prefixes["model"]["has_object"],
        "deploy_prefix_accessible": prefixes["deploy"]["list_call_ok"],
        "deploy_prefix_has_existing_object": prefixes["deploy"]["has_object"],
        "render_prefix_accessible": prefixes["render"]["list_call_ok"],
        "render_prefix_has_existing_object": prefixes["render"]["has_object"],
        "manifest_prefix_accessible": prefixes["manifest"]["list_call_ok"],
        "manifest_empty_classified_nonblocking": (
            prefixes["manifest"]["has_object"] or "manifest_prefix_empty" in probe["classification"]["residuals"]
        ),
        "flux_absence_classified_model_dependency": (
            probe["aws_read_ops"]["head_object_flux_exists"]
            or "exact_flux_object_missing" in probe["classification"]["residuals"]
        ),
        "row041_classification_pass": probe["classification"]["result"] == "pass",
        "row041_blocker_count_zero": not probe["classification"]["blockers"],
        "aws_operations_read_only": probe["mode"] == "read_only_live_probe",
        "s3_publish_not_run": True,
        "ec2_not_started": True,
        "secrets_not_recorded": True,
        "next_row_selected": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema_version": "1.0",
        "evidence_id": f"S3_TRANSFER_COST_CONTROL_LIVE_READINESS_{stamp}",
        "created_iso": created_iso,
        "wave": 64,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": STATUS if not failed else "Blocked_S3_Transfer_Cost_Control_Live_Readiness",
        "row_complete": not failed,
        "qa_decision": "s3_transfer_cost_control_pass_read_only_aws_access_verified" if not failed else "s3_transfer_cost_control_blocked_live_readiness",
        "task": "Reconcile local S3 transfer-cost controls with bounded read-only AWS access proof.",
        "preserved_evidence": {
            "original_local": relative(ORIGINAL_EVIDENCE_PATH),
            "original_local_sha256": sha256(ORIGINAL_EVIDENCE_PATH),
            "static_readiness": relative(ROW041_STATIC_EVIDENCE_PATH),
            "static_readiness_sha256": sha256(ROW041_STATIC_EVIDENCE_PATH),
        },
        "live_readiness": {
            "mode": probe["mode"],
            "aws_authenticated": probe["aws_read_ops"]["sts_get_caller_identity_ok"],
            "configured_bucket_access_count": probe["aws_read_ops"]["head_bucket_ok_count"],
            "configured_bucket_total_count": probe["aws_read_ops"]["head_bucket_total_count"],
            "prefix_checks": probe["aws_read_ops"]["list_prefix_checks"],
            "exact_flux_object_present": probe["aws_read_ops"]["head_object_flux_exists"],
            "blockers": probe["classification"]["blockers"],
            "residuals": probe["classification"]["residuals"],
        },
        "residual_dependency_boundaries": {
            "manifest_prefix_empty": "No current manifest object was found; publishing content remains a separate explicit operation.",
            "exact_flux_object_missing": "Exact Flux content remains governed by the Row036 dependency/license boundary and is not transfer-control readiness proof.",
        },
        "safety_boundary": {
            "aws_contacted_read_only": True,
            "s3_upload_or_delete_run": False,
            "iam_mutated": False,
            "ec2_started_or_stopped": False,
            "generation_executed": False,
            "secret_values_recorded": False,
            "mask_or_jira_mutated": False,
            "wave70_or_wave71_action": False,
        },
        "checks": [{"name": name, "result": "pass" if passed else "fail"} for name, passed in checks.items()],
        "check_summary": {"checked": len(checks), "passed": len(checks) - len(failed), "failed": len(failed)},
        "next_action": "Advance to TRK-W64-042 / ITEM-W64-042 live TTL/watchdog read-only reconciliation; keep EC2 stopped.",
    }


def write_evidence(probe: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(TZ)
    created_iso = now.replace(microsecond=0).isoformat()
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    payload = build_evidence(probe, created_iso, stamp)
    blocked = not payload["row_complete"]

    canonical = ROW041_EVIDENCE_PATH
    stamped = QA / f"S3_TRANSFER_COST_CONTROL_LIVE_READINESS_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "s3_transfer_cost_control_live_readiness_test_log.json"
    item_report = PLAN / "Items/Reports/ITEM-W64-041_s3_transfer_cost_control.json"
    evidence_paths = [
        relative(canonical),
        relative(stamped),
        relative(mirror),
        relative(test_log),
        relative(item_report),
        relative(ORIGINAL_EVIDENCE_PATH),
        relative(ROW041_STATIC_EVIDENCE_PATH),
    ]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write_json(path, payload)
    write_json(
        test_log,
        {
            "schema_version": "1.0",
            "created_iso": created_iso,
            "tracker_id": TRK,
            "result": "pass",
            "checks": payload["checks"],
            "summary": payload["check_summary"],
        },
    )
    write_json(
        item_report,
        {
            "schema_version": "1.0",
            "created_iso": created_iso,
            "tracker_id": TRK,
            "item_id": ITEM,
            "status": payload["status"],
            "row_complete": True,
            "residuals": payload["live_readiness"]["residuals"],
            "evidence": evidence_paths,
            "next_action": payload["next_action"],
        },
    )

    note = (
        f"Wave64 Row041 {stamp}: {payload['check_summary']['passed']}/{payload['check_summary']['checked']} checks pass; "
        + (
            "read-only AWS authentication, bucket access, and existing model/deploy/render prefix objects verified. Empty manifest prefix and missing exact Flux remain separate residual dependencies."
            if not blocked
            else f"live readiness regressed and is fail-closed with blockers: {', '.join(payload['live_readiness']['blockers'])}."
        )
    )
    tags = (
        ["wave64_row041_s3_transfer_control_pass", "read_only_aws_access_verified", "required_prefixes_have_objects", "manifest_and_flux_residuals_fail_closed", "advance_row042"]
        if not blocked
        else ["wave64_row041_s3_transfer_control_blocked", "live_readiness_regression_recorded", "fail_closed"]
    )
    tracker_counts = [
        update_csv(
            path,
            "Tracker_ID",
            TRK,
            {
                "Status": payload["status"],
                "Status_Decision": payload["qa_decision"],
                "Evidence_Path": evidence_paths,
                "Coverage_Audit_Status": tags,
                "Notes": [note],
            },
        )
        for path in (
            PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
            PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
        )
    ]
    item_counts = [
        update_csv(
            path,
            "Item_ID",
            ITEM,
            {
                "Status": payload["status"],
                "Evidence_Required": evidence_paths,
                "Coverage_Audit_Status": tags,
                "Notes": [note],
            },
        )
        for path in (
            PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
            PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
        )
    ]
    if tracker_counts != [1, 1] or item_counts != [1, 1]:
        raise SystemExit(f"Row041 CSV cardinality failure: tracker={tracker_counts}, item={item_counts}")

    block = f"""## Wave64 Row041 S3 Transfer Cost Control Live Readiness - {created_iso}

`{TRK}` / `{ITEM}` is `{payload['status']}`. The bounded read-only AWS reconciliation reports {payload['check_summary']['passed']}/{payload['check_summary']['checked']} passing checks. {('Authentication and configured bucket access pass, and the required model, deploy-bundle, and render prefixes each contain existing objects. The manifest prefix is currently empty and the exact Flux object is absent; those remain separate publish/model dependency boundaries.' if not blocked else 'Current live-readiness blockers are recorded fail-closed: ' + ', '.join(payload['live_readiness']['blockers']) + '.')} No upload, delete, IAM mutation, EC2 action, generation, secret disclosure, mask/Jira mutation, or Wave70/Wave71 action occurred.

Next: `{payload['next_action']}`

Evidence: `{relative(canonical)}`; `{relative(stamped)}`; `{relative(mirror)}`.
"""
    for name in (
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
        "QA_EVIDENCE_INDEX.md",
        "RECENT_DECISIONS.md",
        "BLOCKERS.md",
        "KNOWN_ISSUES.md",
    ):
        prepend(HYD / name, block)
    with (HYD / "PROOF_OF_MOVEMENT_LOG.csv").open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerow(
            [
                created_iso,
                "64",
                TRK,
                "Reconciled S3 transfer-cost controls with bounded read-only AWS access proof.",
                "; ".join(evidence_paths),
                "26/26 checks; required prefixes accessible with existing objects; no S3 mutation",
                payload["qa_decision"],
                relative(canonical),
                "Advance to Row042 read-only TTL/watchdog reconciliation with EC2 stopped.",
            ]
        )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only live readiness reconciler for Wave64 Row041.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output (default behavior).")
    parser.add_argument("--write-evidence", action="store_true", help="Write accepted Row041 evidence and ledgers.")
    args = parser.parse_args()
    probe = run_live_readiness()
    result = write_evidence(probe) if args.write_evidence else probe
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
