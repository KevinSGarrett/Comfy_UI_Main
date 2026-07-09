#!/usr/bin/env python3
"""
Wave64 local image-engine router proof.

Resolves a base-generation image route from the active lane manifest, runtime
lane queue, runtime requirements, and model registry. The resolver is local
only: it does not contact AWS, GitHub, Civitai, EC2, or ComfyUI.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PASS_LANE_STATUSES = {"runtime_smoke_proven", "runtime_smoke_complete"}
PASS_REQUIREMENT_STATUSES = {"runtime_smoke_qa_complete"}
PASS_MODEL_RUNTIME_STATUSES = {"runtime_smoke_complete", "runtime_smoke_proven"}
PASS_HASH_STATUSES = {"ec2_static_match_verified"}
PASS_OBJECT_INFO_STATUSES = {"ec2_object_info_passed"}
PASS_LANE_STATUS_PREFIXES = ("runtime_smoke_proven", "runtime_smoke_complete")
PASS_REQUIREMENT_STATUS_PREFIXES = ("runtime_smoke_qa_complete",)
PASS_MODEL_RUNTIME_STATUS_PREFIXES = ("runtime_smoke_complete", "runtime_smoke_proven")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            record["_line_number"] = line_number
            records.append(record)
    return records


def project_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def rel_path(root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def normalize_family(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace("_", "-").replace(" ", "-")
    if not text:
        return None
    if "realvis" in text or text.startswith("sdxl") or "stable-diffusion-xl" in text:
        return "sdxl"
    if text.startswith("flux") or "flux" in text:
        return "flux"
    if text.startswith("pony") or "pony" in text:
        return "pony"
    if text in {"sd15", "sd-15", "sd1.5", "sd-1.5"} or "sd1.5" in text:
        return "sd15"
    if text.startswith("z-image") or text.startswith("zimage") or "zimage" in text:
        return "zimage"
    return text


def status_matches(value: Any, exact_values: set[str], prefixes: tuple[str, ...] = ()) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if text in exact_values:
        return True
    return any(text.startswith(prefix) for prefix in prefixes)


def request_family(request: dict[str, Any]) -> str | None:
    for key in ("requested_engine_family", "engine_family", "selected_family", "requested_engine"):
        family = normalize_family(request.get(key))
        if family:
            return family
    return None


def request_lora_families(request: dict[str, Any]) -> list[str]:
    families: list[str] = []
    primary = normalize_family(request.get("requires_lora_family"))
    if primary:
        families.append(primary)
    for lora in request.get("loras", []) or []:
        if isinstance(lora, dict):
            family = normalize_family(lora.get("family") or lora.get("base_model") or lora.get("engine_family"))
        else:
            family = normalize_family(lora)
        if family:
            families.append(family)
    return sorted(set(families))


def evidence_exists(root: Path, paths: list[str]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    for value in paths:
        path = project_path(root, value)
        if path is None or not path.exists():
            missing.append(value)
    return (len(missing) == 0, missing)


def find_model_for_required_model(
    registry: list[dict[str, Any]],
    lane_id: str,
    required_model: dict[str, Any],
) -> dict[str, Any] | None:
    filename = str(required_model.get("filename", "")).lower()
    sha256 = str(required_model.get("sha256", "")).lower()
    for record in registry:
        if str(record.get("workflow_lane", "")) != lane_id:
            continue
        if filename and str(record.get("file_name", "")).lower() == filename:
            return record
        if sha256 and str(record.get("sha256", "")).lower() == sha256:
            return record
    return None


def add_check(checks: list[dict[str, Any]], name: str, passed: bool, observed: Any = None, expected: Any = None) -> None:
    checks.append(
        {
            "name": name,
            "result": "pass" if passed else "fail",
            "observed": observed,
            "expected": expected,
        }
    )


def lane_score(request: dict[str, Any], lane_id: str, requirements: dict[str, Any], model: dict[str, Any] | None) -> int:
    score = 0
    preferred_lane = request.get("preferred_lane_id")
    if preferred_lane and str(preferred_lane) == lane_id:
        score += 100
    preferred_model = str(request.get("preferred_model_name", "")).lower()
    if preferred_model and model:
        searchable = " ".join(
            str(model.get(key, ""))
            for key in ("model_name", "file_name", "source_model_id", "version_name")
        ).lower()
        if preferred_model in searchable:
            score += 40
    pass_type = str(request.get("pass_type", "")).lower()
    checkpoint_family = str(requirements.get("checkpoint_family", "")).lower()
    if any(token in pass_type for token in ("hyperreal", "photoreal", "realism")) and "realvis" in checkpoint_family:
        score += 30
    if "fallback" in pass_type and "fallback" in lane_id:
        score += 30
    if "realvis" in lane_id.lower():
        score += 10
    return score


def evaluate_lane(
    root: Path,
    request: dict[str, Any],
    active_lane: dict[str, Any],
    queue_lane: dict[str, Any] | None,
    registry: list[dict[str, Any]],
) -> dict[str, Any]:
    lane_id = str(active_lane.get("lane_id", ""))
    requirement_path = project_path(root, active_lane.get("runtime_requirements"))
    requirements = read_json(requirement_path) if requirement_path and requirement_path.exists() else {}
    engine_family = normalize_family(requirements.get("engine_family"))
    requested_family = request_family(request)
    lora_families = request_lora_families(request)
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []

    add_check(checks, "active_lane_present", bool(lane_id), lane_id, "non-empty lane_id")
    add_check(checks, "runtime_requirements_present", bool(requirements), rel_path(root, requirement_path), "existing runtime_requirements.json")

    queue_status = queue_lane.get("status") if queue_lane else None
    add_check(checks, "queue_lane_present", queue_lane is not None, lane_id, "lane listed in runtime_lane_queue.json")
    add_check(
        checks,
        "queue_status_runtime_smoke_proven",
        status_matches(queue_status, PASS_LANE_STATUSES, PASS_LANE_STATUS_PREFIXES),
        queue_status,
        sorted(PASS_LANE_STATUSES) + [f"{prefix}*" for prefix in PASS_LANE_STATUS_PREFIXES],
    )

    current_status = requirements.get("current_status")
    add_check(
        checks,
        "requirements_status_runtime_smoke_qa_complete",
        status_matches(current_status, PASS_REQUIREMENT_STATUSES, PASS_REQUIREMENT_STATUS_PREFIXES),
        current_status,
        sorted(PASS_REQUIREMENT_STATUSES) + [f"{prefix}*" for prefix in PASS_REQUIREMENT_STATUS_PREFIXES],
    )

    if requested_family:
        add_check(checks, "requested_engine_family_matches_lane", requested_family == engine_family, engine_family, requested_family)
    else:
        add_check(checks, "requested_engine_family_not_forced", True, engine_family, "any compatible active family")

    incompatible_loras = [family for family in lora_families if family != engine_family]
    add_check(checks, "lora_families_match_engine_family", len(incompatible_loras) == 0, lora_families, engine_family)

    required_models = requirements.get("required_models", []) or []
    checkpoint_requirements = [model for model in required_models if str(model.get("role", "")).lower() == "checkpoint"]
    add_check(checks, "checkpoint_requirement_present", len(checkpoint_requirements) == 1, len(checkpoint_requirements), 1)

    selected_model = None
    required_checkpoint = checkpoint_requirements[0] if checkpoint_requirements else {}
    if required_checkpoint:
        selected_model = find_model_for_required_model(registry, lane_id, required_checkpoint)
    add_check(checks, "model_registry_checkpoint_match", selected_model is not None, required_checkpoint.get("filename"), "registry record for lane and checkpoint")

    if selected_model:
        compatible_engines = [normalize_family(value) for value in selected_model.get("compatible_engines", [])]
        add_check(checks, "model_compatible_engine_includes_lane_family", engine_family in compatible_engines, compatible_engines, engine_family)
        add_check(checks, "model_compatibility_status_runtime_validated", selected_model.get("compatibility_status") == "runtime_validated", selected_model.get("compatibility_status"), "runtime_validated")
        add_check(
            checks,
            "model_runtime_validation_status_complete",
            status_matches(selected_model.get("runtime_validation_status"), PASS_MODEL_RUNTIME_STATUSES, PASS_MODEL_RUNTIME_STATUS_PREFIXES),
            selected_model.get("runtime_validation_status"),
            sorted(PASS_MODEL_RUNTIME_STATUSES) + [f"{prefix}*" for prefix in PASS_MODEL_RUNTIME_STATUS_PREFIXES],
        )
        add_check(checks, "model_qa_status_pass", str(selected_model.get("qa_status", "")).startswith("pass"), selected_model.get("qa_status"), "pass*")
        add_check(checks, "required_model_sha_matches_registry", str(required_checkpoint.get("sha256", "")).lower() == str(selected_model.get("sha256", "")).lower(), selected_model.get("sha256"), required_checkpoint.get("sha256"))
        registry_evidence_ok, registry_missing = evidence_exists(root, selected_model.get("evidence_paths", []) or [])
        add_check(checks, "model_registry_evidence_paths_exist", registry_evidence_ok, registry_missing, "no missing evidence paths")
    else:
        add_check(checks, "model_compatible_engine_includes_lane_family", False, None, engine_family)
        add_check(checks, "model_compatibility_status_runtime_validated", False, None, "runtime_validated")
        add_check(checks, "model_runtime_validation_status_complete", False, None, sorted(PASS_MODEL_RUNTIME_STATUSES))
        add_check(checks, "model_qa_status_pass", False, None, "pass*")
        add_check(checks, "required_model_sha_matches_registry", False, None, required_checkpoint.get("sha256"))
        add_check(checks, "model_registry_evidence_paths_exist", False, None, "no missing evidence paths")

    model_hash_statuses = [model.get("hash_status") for model in required_models if model.get("sha256")]
    model_path_statuses = [model.get("path_status") for model in required_models if model.get("filename")]
    add_check(checks, "required_model_hash_status_verified", all(status in PASS_HASH_STATUSES for status in model_hash_statuses), model_hash_statuses, sorted(PASS_HASH_STATUSES))
    add_check(checks, "required_model_path_status_verified", all(status in PASS_HASH_STATUSES for status in model_path_statuses), model_path_statuses, sorted(PASS_HASH_STATUSES))
    add_check(checks, "object_info_status_passed", requirements.get("object_info_status") in PASS_OBJECT_INFO_STATUSES, requirements.get("object_info_status"), sorted(PASS_OBJECT_INFO_STATUSES))

    requirements_evidence = requirements.get("evidence_paths", []) or []
    requirements_evidence_ok, requirements_missing = evidence_exists(root, requirements_evidence)
    add_check(checks, "runtime_requirement_evidence_paths_exist", requirements_evidence_ok, requirements_missing, "no missing evidence paths")

    queue_evidence = []
    if queue_lane:
        queue_evidence = (queue_lane.get("proof_evidence", []) or []) + (queue_lane.get("blocker_evidence", []) or [])
    queue_evidence_ok, queue_missing = evidence_exists(root, queue_evidence)
    add_check(checks, "runtime_queue_evidence_paths_exist", queue_evidence_ok, queue_missing, "no missing evidence paths")

    for check in checks:
        if check["result"] != "pass":
            blockers.append(check["name"])

    return {
        "lane_id": lane_id,
        "score": lane_score(request, lane_id, requirements, selected_model),
        "engine_family": engine_family,
        "runtime_requirements_path": rel_path(root, requirement_path),
        "queue_status": queue_status,
        "current_status": current_status,
        "selected_model": None
        if not selected_model
        else {
            "record_id": selected_model.get("record_id"),
            "model_name": selected_model.get("model_name"),
            "file_name": selected_model.get("file_name"),
            "base_model": selected_model.get("base_model"),
            "sha256": selected_model.get("sha256"),
            "workflow_lane": selected_model.get("workflow_lane"),
            "compatibility_status": selected_model.get("compatibility_status"),
            "runtime_validation_status": selected_model.get("runtime_validation_status"),
            "qa_status": selected_model.get("qa_status"),
            "evidence_paths": selected_model.get("evidence_paths", []),
        },
        "checks": checks,
        "blockers": blockers,
        "result": "pass" if not blockers else "block",
    }


def resolve(root: Path, request: dict[str, Any]) -> dict[str, Any]:
    active = read_json(root / "Workflows" / "base_generation" / "ACTIVE_LANES.json")
    queue = read_json(root / "Plan" / "07_IMPLEMENTATION" / "workflow_templates" / "base_generation" / "runtime_lane_queue.json")
    registry = read_jsonl(root / "Plan" / "Registries" / "Models" / "model_registry.jsonl")

    queue_by_lane = {str(lane.get("lane_id")): lane for lane in queue.get("lanes", [])}
    candidate_results = [
        evaluate_lane(root, request, lane, queue_by_lane.get(str(lane.get("lane_id"))), registry)
        for lane in active.get("lanes", [])
    ]

    preferred_lane = request.get("preferred_lane_id")
    if preferred_lane:
        candidate_results = sorted(candidate_results, key=lambda item: (item["lane_id"] != preferred_lane, -item["score"]))
    else:
        candidate_results = sorted(candidate_results, key=lambda item: (-item["score"], item["lane_id"]))

    passing = [candidate for candidate in candidate_results if candidate["result"] == "pass"]
    selected = passing[0] if passing else None
    required_proof = [
        "model_compatibility_matrix",
        "object_info_check",
        "registry_hash_match",
        "runtime_queue_status",
        "router_decision_evidence",
    ]

    if selected:
        reason = "Selected proven image base-generation lane with matching engine family, checkpoint hash/path proof, object_info proof, runtime smoke evidence, and QA evidence."
        blocked: list[str] = []
        result = "pass_local_only"
    else:
        reason = "No compatible active image base-generation lane passed the local router gate; the request was blocked instead of silently falling back."
        blocked = sorted({blocker for candidate in candidate_results for blocker in candidate["blockers"]})
        result = "block_local_only"

    return {
        "evidence_id": None,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "artifact_id": "TRK-W64-009",
        "artifact_type": "wave64_image_engine_router_decision",
        "request": request,
        "selected_engine": selected["lane_id"] if selected else None,
        "selected_family": selected["engine_family"] if selected else None,
        "selected_lane_id": selected["lane_id"] if selected else None,
        "selected_model": selected["selected_model"] if selected else None,
        "reason": reason,
        "blocked": blocked,
        "required_proof": required_proof,
        "candidate_results": candidate_results,
        "local_only": True,
        "contacts": {
            "aws": False,
            "github_api": False,
            "civitai": False,
            "comfyui": False,
            "ec2": False,
        },
        "ec2_started": False,
        "generation_executed": False,
        "result": result,
        "next_action": "Use the selected lane for compatible local planning, or revise the request/model stack if blocked. Run EC2 only for new runtime proof, not for this local routing gate.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--request", required=True, help="Route request JSON")
    parser.add_argument("--output", default="", help="Optional decision evidence JSON path")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    request_path = Path(args.request)
    if not request_path.is_absolute():
        request_path = root / request_path
    request = read_json(request_path)
    decision = resolve(root, request)
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = root / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        decision["evidence_id"] = output_path.stem
        output_path.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(decision, indent=2))
    return 0 if decision["result"] in {"pass_local_only", "block_local_only"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
