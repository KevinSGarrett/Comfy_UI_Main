#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


RULES = Path("Plan/10_REGISTRIES/wave64_multimodal_scorecard_rules.json")
CURRENT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/multimodal_cross_review.json"
)
ITEM_REPORT = Path("Plan/Items/Reports/ITEM-W64-033_multimodal_cross_review.json")
PRODUCER = Path(
    "Plan/07_IMPLEMENTATION/scripts/produce_wave64_multimodal_scorecard_request.py"
)
EVALUATOR = Path("Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_multimodal_scorecard.py")
CANDIDATE_PATHS: dict[str, Path | None] = {
    "image_review_binding": Path(
        "Plan/Instructions/QA/Evidence/Wave64/image_multi_sample_certification.json"
    ),
    "video_review_binding": Path(
        "Plan/Instructions/QA/Evidence/Wave64/video_temporal_visual_review.json"
    ),
    "strict_audio_report_binding": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "AUDIO_STRICT_REVIEW_RECOVERED_READINESS_20260714T092355-0500.json"
    ),
    "global_audio_report_binding": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "AUDIO_GLOBAL_REVIEW_RECOVERED_READINESS_20260714T105133-0500.json"
    ),
    "av_sync_report_binding": Path(
        "Plan/Instructions/QA/Evidence/Wave64/"
        "AUDIO_AV_SYNC_RECOVERED_READINESS_20260714T075606-0500.json"
    ),
    "artifact_manifest_binding": None,
    "release_gate_decision_binding": Path(
        "Plan/Instructions/QA/Evidence/Wave64/release_done_certification.json"
    ),
}
EXPECTED_TRACKER_ITEMS = {
    "image_review_binding": ("TRK-W64-018", "ITEM-W64-018"),
    "video_review_binding": ("TRK-W64-021", "ITEM-W64-021"),
}
EXPECTED_AUDIO_SCHEMAS = {
    "strict_audio_report_binding": "wave64_strict_audio_review_report",
    "global_audio_report_binding": "wave64_global_audio_review_report",
    "av_sync_report_binding": "wave64_av_sync_certification_report",
}
EXPECTED_BLOCKED_RESULTS = {
    "strict_audio_report_binding": (
        "blocked_recovered_mixes_decodable_but_not_strict_audio_review_request_eligible"
    ),
    "global_audio_report_binding": (
        "blocked_recovered_mixes_not_global_audio_review_request_eligible"
    ),
    "av_sync_report_binding": (
        "blocked_recovered_mux_decodable_but_not_strict_packet_eligible"
    ),
}
ELIGIBILITY_FIELDS = {
    "strict_audio_report_binding": "eligible_for_strict_request",
    "global_audio_report_binding": "eligible_for_strict_request",
    "av_sync_report_binding": "eligible_for_strict_packet",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(root: Path, relative: Path) -> Path:
    root = root.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {relative}") from exc
    return path


def file_binding(root: Path, relative: Path) -> dict[str, Any]:
    path = project_path(root, relative)
    if not path.is_file():
        raise ValueError(f"required file missing: {relative}")
    return {
        "path": path.relative_to(root.resolve()).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def candidate_decision(
    root: Path, role: str, relative: Path | None, payload: dict[str, Any] | None
) -> dict[str, Any]:
    if relative is None:
        return {
            "present": False,
            "candidate_binding": None,
            "contract_compatible": False,
            "blocking_reasons": ["exact_artifact_manifest_missing"],
        }
    assert payload is not None
    reasons: list[str] = []
    if role in EXPECTED_TRACKER_ITEMS:
        tracker_id, item_id = EXPECTED_TRACKER_ITEMS[role]
        if payload.get("tracker_id") != tracker_id or payload.get("item_id") != item_id:
            reasons.append("tracker_or_item_contract_mismatch")
        if not isinstance(payload.get("lineage"), dict):
            reasons.append("shared_multimodal_lineage_missing")
        if not isinstance(payload.get("evidence_id"), str):
            reasons.append("artifact_identity_missing")
        if role == "image_review_binding" and payload.get("row_complete") is not True:
            reasons.append("image_review_not_complete")
        if role == "video_review_binding":
            reasons.append("video_evidence_bounded_not_full_multimodal_release")
    elif role in EXPECTED_AUDIO_SCHEMAS:
        if payload.get("schema_name") != EXPECTED_AUDIO_SCHEMAS[role]:
            reasons.append("strict_report_schema_mismatch")
        if payload.get("result") != EXPECTED_BLOCKED_RESULTS[role]:
            raise ValueError(f"recovered audio result changed: {role}")
        eligibility_field = ELIGIBILITY_FIELDS[role]
        if payload.get("mapping_decision", {}).get(eligibility_field) is not False:
            raise ValueError(f"recovered audio eligibility changed: {role}")
        reasons.extend(("shared_multimodal_lineage_missing", "upstream_audio_row_blocked"))
    elif role == "release_gate_decision_binding":
        if not isinstance(payload.get("release_id"), str):
            reasons.append("row033_release_id_missing")
        if payload.get("tracker_id") != "TRK-W64-033":
            reasons.append("release_decision_not_owned_by_row033_artifact")
        reasons.append("release_evidence_is_full_project_blocked_audit_not_row033_gate")
    return {
        "present": True,
        "candidate_binding": file_binding(root, relative),
        "contract_compatible": not reasons,
        "blocking_reasons": reasons,
    }


def build_evidence(root: Path, timestamp: str) -> dict[str, Any]:
    root = root.resolve()
    rules = load_json(project_path(root, RULES))
    current = load_json(project_path(root, CURRENT_EVIDENCE))
    item = load_json(project_path(root, ITEM_REPORT))
    if current.get("status_decision") != "Blocked_Multimodal_Production_Review_Proof_Missing":
        raise ValueError("Row033 evidence status changed; reassess mapping")
    if item.get("status") != "Blocked_Multimodal_Production_Review_Proof_Missing":
        raise ValueError("Row033 item status changed; reassess mapping")
    authorities = rules.get("authority_rules", {}).get(
        "production_authority_exact_objects"
    )
    if authorities != []:
        raise ValueError("Row033 production authority registry changed; reassess mapping")
    current_authority = current.get("current_authority", {})
    if current_authority.get("approved_production_authority_object_count") != 0:
        raise ValueError("Row033 approved authority count changed")

    candidates: dict[str, dict[str, Any]] = {}
    for role, relative in CANDIDATE_PATHS.items():
        payload = None if relative is None else load_json(project_path(root, relative))
        candidates[role] = candidate_decision(root, role, relative, payload)
    compatible_count = sum(item["contract_compatible"] for item in candidates.values())

    stamp = timestamp.replace("-", "").replace(":", "")
    return {
        "schema_version": "1.0",
        "evidence_id": f"W64-MULTIMODAL-RECOVERED-READINESS-{stamp}",
        "timestamp": timestamp,
        "tracker_id": "TRK-W64-033",
        "item_id": "ITEM-W64-033",
        "status_decision": "Blocked_Multimodal_Production_Review_Proof_Missing",
        "source_bindings": {
            "rules": file_binding(root, RULES),
            "current_row033_evidence": file_binding(root, CURRENT_EVIDENCE),
            "row033_item_report": file_binding(root, ITEM_REPORT),
            "request_producer": file_binding(root, PRODUCER),
            "evaluator": file_binding(root, EVALUATOR),
        },
        "required_binding_count": len(CANDIDATE_PATHS),
        "binding_candidates": candidates,
        "mapping_decision": {
            "present_candidate_count": sum(item["present"] for item in candidates.values()),
            "contract_compatible_binding_count": compatible_count,
            "shared_artifact_id_selected": False,
            "shared_lineage_selected": False,
            "artifact_manifest_release_id_match": False,
            "eligible_for_strict_request": False,
            "strict_producer_invoked": False,
            "strict_evaluator_invoked": False,
            "skip_reason": (
                "Fail closed before request production: available image/video evidence has no "
                "shared Row033 lineage, recovered audio/sync records are readiness blockers rather "
                "than strict report schemas, no exact artifact manifest exists, and the release "
                "audit is not a matching Row033 release-gate object."
            ),
        },
        "authority_state": {
            "approved_production_authority_object_count": 0,
            "supporting_evidence_promoted_to_shared_bundle": False,
            "bounded_video_pass_promoted_to_multimodal_release": False,
            "blocked_audio_readiness_promoted_to_strict_reports": False,
            "full_project_release_audit_promoted_to_row033_gate": False,
        },
        "boundaries": {
            "existing_evidence_reused": True,
            "generation_executed": False,
            "media_modified": False,
            "lineage_or_release_identity_invented": False,
            "aws_contacted": False,
            "ec2_started": False,
            "mask_or_wave71_touched": False,
            "jira_mutated": False,
        },
        "result": "blocked_recovered_evidence_not_multimodal_scorecard_request_eligible",
        "next_action": (
            "Retain these records as hash-bound supporting evidence only. Do not form a strict "
            "Row033 request until seven distinct artifacts share one exact non-synthetic artifact/"
            "run/scene/shot/take lineage, strict audio schemas, matching manifest/release IDs, and "
            "an approved production authority object; proceed to Row034 without promoting Row033."
        ),
    }


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise ValueError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="C:/Comfy_UI_Main")
    parser.add_argument("--output", required=True)
    parser.add_argument("--tracker-output", required=True)
    parser.add_argument(
        "--timestamp", default=datetime.now().astimezone().isoformat(timespec="seconds")
    )
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        output = project_path(root, Path(args.output))
        tracker_output = project_path(root, Path(args.tracker_output))
        if output == tracker_output:
            raise ValueError("output and tracker output must differ")
        evidence = build_evidence(root, args.timestamp)
        atomic_write(output, evidence)
        atomic_write(tracker_output, evidence)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(
        json.dumps(
            {
                "status": evidence["status_decision"],
                "present_candidates": evidence["mapping_decision"]["present_candidate_count"],
                "compatible_bindings": evidence["mapping_decision"][
                    "contract_compatible_binding_count"
                ],
                "eligible_for_strict_request": evidence["mapping_decision"][
                    "eligible_for_strict_request"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
