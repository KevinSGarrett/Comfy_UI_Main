#!/usr/bin/env python3
"""Package the live Wave64 speech bridge smoke and reconcile Rows145/146."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


EXPECTED_CLASSIFICATION = "W64_ROWS145_146_LIVE_COMFYUI_BRIDGE_SMOKE_PASS_PRODUCTION_BLOCKED"
ROW_STATUS = {
    "145": "Blocked_Production_Engine_Dispatch_And_Voice_Authority_Pending_Live_Bridge_Smoke_Pass",
    "146": "Blocked_Full_Engine_Isolation_Cache_Hit_Replay_And_Cost_Authority_Pending_Live_Lock_Telemetry_Pass",
}
ROW_BLOCKERS = {
    "145": [
        "production voice authority is missing",
        "the bridge version is dry-run only and does not dispatch a production engine",
    ],
    "146": [
        "multi-engine isolated runtime coverage is incomplete",
        "cache-hit replay and production cost authority are not yet proven",
    ],
}


class FinalizationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise FinalizationError(f"required file is missing: {path}")
    return {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FinalizationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise FinalizationError(f"JSON root must be an object: {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, ensure_ascii=True) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def copy_exact(source: Path, destination: Path) -> dict[str, Any]:
    source_binding = binding(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(destination) != source_binding["sha256"]:
            raise FinalizationError(f"durable artifact hash conflict: {destination}")
    else:
        shutil.copy2(source, destination)
    durable = binding(destination)
    if durable["sha256"] != source_binding["sha256"]:
        raise FinalizationError(f"durable artifact copy mismatch: {destination}")
    return durable


def require_bound_file(record: dict[str, Any], label: str) -> Path:
    path = Path(str(record.get("path", ""))).resolve()
    observed = binding(path)
    if observed["sha256"] != record.get("sha256") or observed["bytes"] != record.get("bytes"):
        raise FinalizationError(f"{label} binding mismatch")
    return path


def validate_smoke(smoke: dict[str, Any]) -> tuple[Path, Path]:
    if smoke.get("classification") != EXPECTED_CLASSIFICATION:
        raise FinalizationError("live smoke classification is invalid")
    if smoke.get("media_tree_unchanged") is not True or smoke.get("queue_idle_before") is not True:
        raise FinalizationError("queue or media non-mutation proof is missing")
    result = smoke.get("result")
    boundaries = smoke.get("boundaries")
    if not isinstance(result, dict) or not isinstance(boundaries, dict):
        raise FinalizationError("smoke result or boundaries are missing")
    if result.get("classification") != "W64_SPEECH_BRIDGE_DRY_RUN_VALIDATED_AUTHORITY_BLOCKED":
        raise FinalizationError("bridge did not return the expected fail-closed classification")
    if result.get("status") != "BLOCKED" or len(str(result.get("cache_key", ""))) != 64:
        raise FinalizationError("bridge status or cache key is invalid")
    expected = {"BLOCKED_VOICE_AUTHORITY_MISSING", "BLOCKED_PRODUCTION_CERTIFICATION_INCOMPLETE"}
    if not expected.issubset(set(result.get("blockers", []))):
        raise FinalizationError("required voice/production blockers are missing")
    required_false = (
        "media_generated", "candidate_media_written", "promotion_attempted", "production_authority_claimed",
        "aws_or_ec2_used", "mask_or_wave71_touched", "content_based_suppression",
    )
    if any(boundaries.get(name) is not False for name in required_false):
        raise FinalizationError("a smoke boundary improperly claims media, authority, or prohibited work")
    result_boundaries = result.get("boundaries", {})
    if result_boundaries.get("dry_run") is not True or result_boundaries.get("engine_subprocess_called") is not False:
        raise FinalizationError("bridge dispatch boundary is invalid")
    node = smoke.get("node_object_info", {})
    if node.get("category") != "Wave64/Speech" or node.get("output_node") is not True:
        raise FinalizationError("live object_info does not expose the expected output node")
    result_path = require_bound_file(result.get("result_binding", {}), "bridge result")
    telemetry_path = require_bound_file(result.get("telemetry_binding", {}), "bridge telemetry")
    lock = result_path.parents[3] / "audio_speech_cache/locks" / f"{result['cache_key']}.lock"
    if lock.exists():
        raise FinalizationError("cache lock was not released after live execution")
    return result_path, telemetry_path


def update_rows(path: Path, id_column: str, prefix: str, evidence_root: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames or id_column not in fieldnames:
        raise FinalizationError(f"CSV schema mismatch: {path}")
    found: set[str] = set()
    for row in rows:
        row_id = row[id_column]
        for number, status in ROW_STATUS.items():
            if row_id != f"{prefix}-W64-{number}":
                continue
            found.add(number)
            evidence = f"{evidence_root}/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{number}.json"
            row["Status"] = status
            row["Coverage_Audit_Status"] = "live_comfyui_bridge_runtime_recorded_exact_production_blockers_preserved"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = evidence
            if "Status_Decision" in row:
                row["Status_Decision"] = status.lower()
            row["Notes"] = (
                f"Live local ComfyUI /prompt speech-bridge evidence is recorded in {evidence}. "
                "Schema, object_info, cache-key, exclusive-lock, telemetry, structured-blocker, and no-media gates pass. "
                "The bridge is dry-run only; production engine dispatch, voice authority, cache-hit replay, and promotion remain blocked. "
                "content_based_suppression=false."
            )
    if found != set(ROW_STATUS):
        raise FinalizationError(f"missing expected rows in {path}: {sorted(set(ROW_STATUS) - found)}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def load_cache_manager(root: Path):
    path = root / "Plan/07_IMPLEMENTATION/scripts/manage_wave64_speech_runtime_cache_cost.py"
    spec = importlib.util.spec_from_file_location("wave64_cache_report_finalizer", path)
    if not spec or not spec.loader:
        raise FinalizationError("unable to load runtime cache manager")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(root: Path, smoke_path: Path, durable_dir_name: str) -> dict[str, Any]:
    smoke = load_object(smoke_path)
    result_path, telemetry_path = validate_smoke(smoke)
    canonical_node = root / "Plan/07_IMPLEMENTATION/comfyui_custom_nodes/wave64_speech_bridge/__init__.py"
    installed_node = root / "ComfyUI/custom_nodes/wave64_speech_bridge/__init__.py"
    if sha256_file(canonical_node) != sha256_file(installed_node):
        raise FinalizationError("installed ComfyUI node does not match canonical source")
    runtime_sources = {
        "wave64_speech_bridge_live_smoke.json": smoke_path,
        "wave64_speech_bridge_result.json": result_path,
        "wave64_speech_bridge_telemetry.json": telemetry_path,
    }
    durable_dir = root / "Plan/Instructions/Operations/Pulled_Back_Artifacts" / durable_dir_name
    durable = {name: copy_exact(source, durable_dir / name) for name, source in runtime_sources.items()}
    runtime = {name: binding(source) for name, source in runtime_sources.items()}
    implementation_paths = {
        "request_schema": "Plan/08_SCHEMAS/wave64_speech_bridge_request.schema.json",
        "bridge_node": "Plan/07_IMPLEMENTATION/comfyui_custom_nodes/wave64_speech_bridge/__init__.py",
        "cache_manager": "Plan/07_IMPLEMENTATION/scripts/manage_wave64_speech_runtime_cache_cost.py",
        "installer_smoke": "Plan/07_IMPLEMENTATION/scripts/install_and_smoke_wave64_speech_bridge.py",
        "finalizer": "Plan/07_IMPLEMENTATION/scripts/finalize_wave64_speech_rows145_146.py",
        "tests": "Plan/Instructions/QA/Scripts/test_wave64_speech_bridge.py",
        "finalizer_tests": "Plan/Instructions/QA/Scripts/test_finalize_wave64_speech_rows145_146.py",
        "workflow": "Workflows/audio_generation/wave64_speech_bridge_dry_run/workflow.api.json",
        "runtime_requirements": "Workflows/audio_generation/wave64_speech_bridge_dry_run/runtime_requirements.json",
        "smoke_contract": "Workflows/audio_generation/wave64_speech_bridge_dry_run/smoke_test_request.json",
    }
    implementation = {name: binding(root / relative) for name, relative in implementation_paths.items()}
    cache_report = load_cache_manager(root).report(root / "runtime_artifacts/audio_speech_cache")
    common = {
        "schema_version": "1.0",
        "runtime_classification": smoke["classification"],
        "live_smoke": smoke,
        "runtime_artifacts": runtime,
        "durable_artifacts": durable,
        "implementation": implementation,
        "installed_node": binding(installed_node),
        "cache_cost_report": cache_report,
        "boundaries": {
            **smoke["boundaries"],
            "bridge_is_dry_run_only": True,
            "row144_promotion_touched": False,
            "row_complete_claimed": False,
            "pass_like_claimed": False,
        },
    }
    capabilities = {
        "145": "live dependency-light ComfyUI output node with schema validation, structured authority blocking, tracked API workflow, and no-media /prompt proof",
        "146": "canonical exact-hash cache key, exclusive per-key lock, immutable result binding, local telemetry, and aggregate cache/cost report",
    }
    gates = {
        "145": {
            "installed_hash_matches_canonical": True,
            "live_object_info_pass": True,
            "live_prompt_execution_pass": True,
            "structured_authority_blocker_pass": True,
            "no_media_or_promotion_pass": True,
            "production_engine_dispatch_pass": False,
            "production_voice_authority_pass": False,
        },
        "146": {
            "canonical_cache_key_pass": True,
            "exclusive_lock_live_pass": True,
            "lock_release_pass": True,
            "local_telemetry_pass": True,
            "cache_hit_replay_pass": False,
            "full_engine_isolation_pass": False,
            "production_cost_authority_pass": False,
        },
    }
    qa_root = root / "Plan/Instructions/QA/Evidence/Audio_Asset_Intake"
    tracker_root = root / "Plan/Tracker/Evidence/Audio_Asset_Intake"
    for number in ROW_STATUS:
        record = {
            **common,
            "artifact_type": f"wave64_autonomous_hyperreal_speech_row{number}_evidence",
            "row": {
                "item_id": f"ITEM-W64-{number}",
                "tracker_id": f"TRK-W64-{number}",
                "implemented_capability": capabilities[number],
                "status": ROW_STATUS[number],
                "automated_gates": gates[number],
                "blockers": ROW_BLOCKERS[number],
                "pass_like": False,
            },
            "row_complete": False,
        }
        name = f"WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{number}.json"
        write_json_atomic(qa_root / name, record)
        write_json_atomic(tracker_root / name, record)
    update_rows(
        root / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv",
        "Item_ID", "ITEM", "Plan/Instructions/QA/Evidence/Audio_Asset_Intake",
    )
    update_rows(
        root / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv",
        "Tracker_ID", "TRK", "Plan/Instructions/QA/Evidence/Audio_Asset_Intake",
    )
    return {
        "classification": "W64_ROWS145_146_LIVE_BRIDGE_RECONCILED_BLOCKED_PRODUCTION",
        "durable_artifacts": durable,
        "row_status": ROW_STATUS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--smoke-evidence", type=Path, required=True)
    parser.add_argument("--durable-dir-name", required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    smoke_path = args.smoke_evidence.resolve() if args.smoke_evidence.is_absolute() else (root / args.smoke_evidence).resolve()
    try:
        result = build(root, smoke_path, args.durable_dir_name)
    except Exception as exc:
        print(json.dumps({"classification": "W64_ROWS145_146_FINALIZATION_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
