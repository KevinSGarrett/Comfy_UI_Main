#!/usr/bin/env python3
"""Apply the fail-closed Wave64 fluid-state runtime result to Row056 authority."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
REGISTRY = PROJECT_ROOT / "Plan/10_REGISTRIES/advanced_additions_direct_proof_status.json"
CANONICAL = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Wave64/advanced_additions_integration.json"
ITEM = PROJECT_ROOT / "Plan/Items/Reports/ITEM-W64-056_advanced_additions_integration.json"
TRACKERS = [
    PROJECT_ROOT / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
]
HYDRATION = [
    PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
    PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
]
EVIDENCE_REL = "Plan/Instructions/QA/Evidence/Wave64/FLUID_BODY_STATE_CONTINUITY_DIRECT_RUNTIME_REVIEW_20260715T100719-0500.json"
TRACKER_EVIDENCE_REL = "Plan/Tracker/Evidence/FLUID_BODY_STATE_CONTINUITY_DIRECT_RUNTIME_REVIEW_20260715T100719-0500.json"
EVIDENCE_SHA256 = "cccf2e6b3a7a5e4b19773bf070ce574cd1bf08db62cc9e93803508f0859a903e"
TIMESTAMP = "2026-07-15T10:07:19-05:00"
STATUS = "Blocked_Five_Advanced_Systems_Direct_Proof_Missing_Fluid_State_Continuity_Fail_One_Bounded_System_Pass"
DECISION = "micro_motion_bounded_pass_fluid_state_runtime_review_fail_five_systems_missing"
NOTE_MARKER = "Wave64 Row056 fluid-state runtime review 2026-07-15"
HYDRATION_MARKER = "## Wave64 Fluid-State Direct Runtime Review Failed - 2026-07-15T10:07:19-05:00"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(encoded)
    os.replace(temporary, path)


def updated_fluid_entry(entry: dict[str, Any]) -> dict[str, Any]:
    updated = dict(entry)
    updated["blockers"] = [
        "direct_runtime_review_executed_no_route_passed_state_and_continuity",
        "identity_critical_eye_region_continuity_failure",
        "production_robustness_multi_sample_missing",
    ]
    updated["direct_proof_scope"] = {
        "local_runtime_route_count": 3,
        "local_generation_count": 4,
        "candidate_retry_count": 0,
        "before_after_visual_review_count": 3,
        "planned_state_achieved_by_at_least_one_route": True,
        "shot_continuity_achieved_by_at_least_one_route": True,
        "single_route_achieved_state_and_continuity": False,
        "evidence_path": EVIDENCE_REL,
        "evidence_sha256": EVIDENCE_SHA256,
    }
    updated["runtime_promotion_state"] = "bounded_direct_runtime_review_fail_shot_continuity"
    return updated


def update_systems(systems: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matched = 0
    updated: list[dict[str, Any]] = []
    for entry in systems:
        if entry.get("system_id") == "fluid_body_state_continuity":
            updated.append(updated_fluid_entry(entry))
            matched += 1
        else:
            updated.append(entry)
    if matched != 1:
        raise ValueError(f"expected one fluid system entry, found {matched}")
    return updated


def proof_summary() -> dict[str, Any]:
    return {
        "bounded_direct_runtime_proof_pass": 1,
        "bounded_pass_system": "micro_motion_layer",
        "direct_runtime_review_fail": 1,
        "failed_system": "fluid_body_state_continuity",
        "direct_runtime_proof_missing": 5,
        "production_certified": 0,
        "systems_total": 7,
    }


def remaining_blockers(existing: dict[str, Any]) -> dict[str, Any]:
    updated = dict(existing)
    updated["fluid_body_state_continuity"] = [
        "direct_runtime_review_executed_no_route_passed_state_and_continuity",
        "identity_critical_eye_region_continuity_failure",
        "production_robustness_multi_sample_missing",
    ]
    return updated


def update_registry(payload: dict[str, Any]) -> dict[str, Any]:
    updated = dict(payload)
    updated["advanced_systems"] = update_systems(list(payload.get("advanced_systems") or []))
    updated["artifact_id"] = "advanced_additions_direct_proof_status_20260715T100719-0500"
    updated["proof_summary"] = proof_summary()
    updated["qa_decision"] = DECISION
    updated["runtime_promotion_state"] = "blocked"
    updated["status"] = STATUS
    updated["timestamp"] = TIMESTAMP
    return updated


def update_canonical(payload: dict[str, Any]) -> dict[str, Any]:
    updated = dict(payload)
    updated["advanced_systems"] = update_systems(list(payload.get("advanced_systems") or []))
    updated["evidence_id"] = "W64-ROW056-ADVANCED-ADDITIONS-FLUID-STATE-DIRECT-RUNTIME-20260715T1007190500"
    updated["proof_summary"] = proof_summary()
    updated["qa_decision"] = DECISION
    updated["remaining_blockers"] = remaining_blockers(dict(payload.get("remaining_blockers") or {}))
    updated["runtime_promotion_state"] = "blocked"
    updated["status"] = STATUS
    updated["timestamp"] = TIMESTAMP
    paths = list(payload.get("evidence_paths") or [])
    for path in (EVIDENCE_REL, TRACKER_EVIDENCE_REL):
        if path not in paths:
            paths.append(path)
    updated["evidence_paths"] = paths
    updated["fluid_state_direct_evidence"] = {
        "path": EVIDENCE_REL,
        "sha256": EVIDENCE_SHA256,
        "classification": "DIRECT_RUNTIME_REVIEW_EXECUTED_NO_ROUTE_PASSED_BOTH_STATE_AND_CONTINUITY",
    }
    return updated


def update_item(payload: dict[str, Any]) -> dict[str, Any]:
    updated = dict(payload)
    evidence = list(payload.get("evidence") or [])
    for path in (EVIDENCE_REL, TRACKER_EVIDENCE_REL):
        if path not in evidence:
            evidence.insert(0, path)
    updated["created_iso"] = TIMESTAMP
    updated["evidence"] = evidence
    updated["next_action"] = (
        "Preserve all three fluid-state routes without rerun. Continue a different advanced system only when its "
        "exact non-mask/non-audio prerequisites are present; reopen fluid state only for a new identity-preserving "
        "regional-control implementation, not a seed or parameter retry."
    )
    updated["proof_summary"] = proof_summary()
    updated["qa_decision"] = DECISION
    updated["remaining_blockers"] = remaining_blockers(dict(payload.get("remaining_blockers") or {}))
    updated["row_complete"] = False
    updated["status"] = STATUS
    return updated


def update_tracker(path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise ValueError(f"tracker header missing: {path}")
    matched = 0
    note = (
        f"{NOTE_MARKER}: three hash-bound local routes and four generations produced exact visual evidence. "
        "Txt2img established tears but changed identity/hair/wardrobe; low-denoise img2img preserved continuity "
        "but omitted tears; masked inpaint established tear cues but changed iris and eye/brow identity detail. "
        "No retry, EC2, AWS, mask promotion, Wave71, or Jira action occurred."
    )
    for row in rows:
        if row.get("Tracker_ID") != "TRK-W64-056":
            continue
        matched += 1
        row["Status"] = STATUS
        row["Status_Decision"] = DECISION
        row["Evidence_Path"] = str(PROJECT_ROOT / TRACKER_EVIDENCE_REL.replace("/", "\\"))
        existing = row.get("Notes") or ""
        if NOTE_MARKER not in existing:
            row["Notes"] = f"{existing} | {note}" if existing else note
    if matched != 1:
        raise ValueError(f"expected one TRK-W64-056 row in {path}, found {matched}")
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def hydration_block() -> str:
    return f"""{HYDRATION_MARKER}

`TRK-W64-056` / `ITEM-W64-056` now has genuine local direct runtime and visual-review evidence for `fluid_body_state_continuity`. Three architecture-distinct routes executed four total generations with zero retries: txt2img established tears but failed identity/hair/wardrobe continuity; low-denoise img2img preserved continuity but omitted tears; deterministic masked inpaint established bilateral tear cues but changed iris color and eye/brow identity detail. No route passed both planned state and shot continuity, so the system and Row056 remain blocked.

Next action: preserve this chain without another seed/parameter loop. Continue a different exact implementation dependency or wait for the active audio-control/index side-task handoff; reopen fluid state only for a genuinely new identity-preserving regional-control artifact. Keep EC2 stopped and preserve gold-mask, Wave71+, Jira, and final-certification boundaries.

Evidence: `{EVIDENCE_REL}`.

"""


def prepend_hydration(path: Path) -> None:
    existing = path.read_text(encoding="utf-8-sig")
    if HYDRATION_MARKER in existing:
        return
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(hydration_block() + existing, encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", default=str(PROJECT_ROOT / EVIDENCE_REL))
    args = parser.parse_args()
    evidence = Path(args.evidence).resolve()
    if sha256_file(evidence) != EVIDENCE_SHA256:
        raise ValueError("fluid-state evidence hash drift")
    write_json(REGISTRY, update_registry(read_json(REGISTRY)))
    write_json(CANONICAL, update_canonical(read_json(CANONICAL)))
    write_json(ITEM, update_item(read_json(ITEM)))
    for tracker in TRACKERS:
        update_tracker(tracker)
    for hydration in HYDRATION:
        prepend_hydration(hydration)
    print(json.dumps({"status": STATUS, "evidence_sha256": EVIDENCE_SHA256}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
