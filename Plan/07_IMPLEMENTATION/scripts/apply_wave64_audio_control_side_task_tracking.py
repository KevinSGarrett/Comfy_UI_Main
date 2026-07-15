#!/usr/bin/env python3
"""Reconcile Wave64 audio controls without promoting any audio row."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TRACKER_PATHS = (
    "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv",
    "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
)
ITEM_PATHS = (
    "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
)
REPORT_PATHS = {
    "ITEM-W64-025": "Plan/Items/Reports/ITEM-W64-025_audio_pipeline_build.json",
    "ITEM-W64-026": "Plan/Items/Reports/ITEM-W64-026_audio_engine_routing.json",
    "ITEM-W64-027": "Plan/Items/Reports/ITEM-W64-027_audio_voice_dialogue.json",
    "ITEM-W64-031": "Plan/Items/Reports/ITEM-W64-031_audio_strict_review.json",
}
ROW_STATUS = {
    "025": "Blocked_Production_Eligible_Audio_Candidate_Missing",
    "026": "Blocked_Audio_Engine_Authority_Not_Approved",
    "027": "Blocked_Production_Eligible_Voice_Candidate_Missing",
    "031": "Blocked_Strict_Audio_Production_Review_Proof_Missing",
}
INDEX_EVIDENCE = "Plan/Instructions/QA/Evidence/Audio_Asset_Intake/AUDIO_PACK_FUNCTIONAL_INDEX_20260715T151915Z.json"
INDEX_EVIDENCE_SHA = "0f91c4627ea139bccddc600332742e4552b8f2a8bd916e269f9df119871b61b8"
CONTROL_EVIDENCE = "Plan/Instructions/QA/Evidence/Wave64/W64_AUDIO_HUMAN_QA_VOICE_CONTRACT_20260715T102730-0500.json"
CONTROL_EVIDENCE_SHA = "f107919fab6f03e52b4ca0bc8c7518bbf0fb97f7a941f7869ff482f8f8177800"
CHATTERBOX_EVIDENCE = "Plan/Instructions/QA/Evidence/Wave64/W64_CHATTERBOX_DIALOGUE_REJECTION_20260715T092901-0500.json"
CHATTERBOX_EVIDENCE_SHA = "fa524a959e5d28b37709f22eb96768e4ca02816babd3a327bc47576dc39cc4c0"
INDEX_RUNTIME = "runtime_artifacts/audio_asset_indexes/audio_downloads_functional_20260715T095712-0500/audio_pack_functional_index.jsonl"
INDEX_SHA = "7301243a364025dbd23907aee20ee8593d5897caa83d38391026ad42da6d17ec"
INDEX_ROWS = {"025", "026", "028", "029", "030", "031", "032"}
CONTROL_ROWS = {"025", "027", "031"}
HUMAN_REVIEW_ROWS = {f"{number:03d}" for number in range(25, 34)}
NOTE = (
    "Wave64 audio-control side task 2026-07-15: all 39,771 external audio files are hash-bound and "
    "selectable with no content-based suppression; human playback and distinct final-authority schemas "
    "are implemented; focused is delivery style and controlled is intensity. Chatterbox is the latest "
    "immutable rejection at 3.92 seconds versus 3.0. No row or candidate was promoted."
)
HUMAN_POLICY = (
    "Codex performs all preparation, hashing, automated evaluation, packet production, validation, and "
    "tracking. Human work is limited to the irreducible listening scores for an automatically eligible "
    "hash-bound candidate; human listening alone cannot authorize final promotion."
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _append_unique(current: str, value: str, separator: str) -> str:
    entries = [entry.strip() for entry in (current or "").split(separator) if entry.strip()]
    if value not in entries:
        entries.append(value)
    return separator.join(entries)


def verify_evidence(root: Path = ROOT) -> dict[str, Any]:
    expected = {
        INDEX_EVIDENCE: INDEX_EVIDENCE_SHA,
        CONTROL_EVIDENCE: CONTROL_EVIDENCE_SHA,
        CHATTERBOX_EVIDENCE: CHATTERBOX_EVIDENCE_SHA,
    }
    for relative, expected_sha in expected.items():
        path = root / relative
        if not path.is_file() or _sha256(path) != expected_sha:
            raise ValueError(f"evidence hash mismatch: {path}")
    index_path = root / INDEX_RUNTIME
    if not index_path.is_file() or _sha256(index_path) != INDEX_SHA:
        raise ValueError("functional index hash mismatch")
    with index_path.open("r", encoding="utf-8") as handle:
        count = sum(1 for _ in handle)
    if count != 39771:
        raise ValueError(f"functional index row count mismatch: {count}")
    return {"evidence_count": 3, "functional_index_rows": count, "functional_index_sha256": INDEX_SHA}


def update_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    item_id = payload.get("item_id")
    if item_id not in REPORT_PATHS:
        raise ValueError(f"unexpected report identity: {item_id}")
    row = item_id[-3:]
    payload["timestamp"] = "2026-07-15T10:27:30.0899161-05:00"
    payload["status"] = ROW_STATUS[row]
    payload["row_complete"] = False
    implementation = payload.setdefault("implementation", {})
    implementation.update(
        {
            "full_audio_pack_functional_index_ready": True,
            "human_playback_review_authority_path_ready": True,
            "human_final_production_authority_path_ready": True,
            "dialogue_contract_v2_style_intensity_separation_ready": True,
            "reference_speaker_registry_ready": True,
        }
    )
    validation = payload.setdefault("validation", {})
    validation.update(
        {
            "functional_audio_index_file_count": 39771,
            "functional_audio_index_unique_sha256_count": 29862,
            "functional_audio_index_sha256": INDEX_SHA,
            "audio_control_side_task_tests_passed": 96,
            "chatterbox_candidate_sha256": "cde61c59adace5b0674ee05268f56a091b0921b196bc7ad54ad0a06fc17a5b96",
            "chatterbox_candidate_duration_seconds": 3.92,
            "chatterbox_expected_duration_seconds": 3.0,
            "chatterbox_candidate_rejected": True,
        }
    )
    gates = payload.setdefault("acceptance_gates", {})
    gates.update(
        {
            "full_audio_pack_functional_index_ready": True,
            "content_based_audio_suppression_absent": True,
            "human_playback_review_schema_ready": True,
            "human_final_authority_schema_ready": True,
            "production_eligible_dialogue_candidate_present": False,
            "independent_playback_review_pass": False,
            "production_review_authority_pass": False,
            "row_complete": False,
        }
    )
    blockers = payload.get("blockers")
    if isinstance(blockers, list):
        blockers[:] = [
            item for item in blockers
            if not (isinstance(item, dict) and item.get("scope") == "primary_row_blocker")
        ]
        primary_reason = {
            "025": "Runtime execution exists for Parler, CosyVoice2, Chatterbox, and MMAudio, but every current dialogue candidate is rejected and no production-eligible complete audio chain is approved.",
            "026": "Audio assets and several real engine runtimes exist, but the production engine selection and authority decision remain unapproved.",
            "027": "No production-eligible C01 dialogue candidate exists; C01 identity policy and canonical reference or synthetic baseline also remain pending.",
            "031": "Human/model playback paths are implemented, but no eligible candidate has passing playback proof and no distinct final production authority is allowlisted.",
        }[row]
        blockers.insert(0, {"classification": ROW_STATUS[row], "scope": "primary_row_blocker", "reason": primary_reason})
    evidence = payload.setdefault("evidence", [])
    if isinstance(evidence, list):
        for path, sha in (
            (INDEX_EVIDENCE, INDEX_EVIDENCE_SHA),
            (CONTROL_EVIDENCE, CONTROL_EVIDENCE_SHA),
            (CHATTERBOX_EVIDENCE, CHATTERBOX_EVIDENCE_SHA),
        ):
            if row == "026" and path != INDEX_EVIDENCE:
                continue
            existing = next((item for item in evidence if isinstance(item, dict) and item.get("path") == path), None)
            if existing:
                existing["sha256"] = sha
            else:
                evidence.append({"path": path, "sha256": sha})
    payload["next_action"] = (
        "Keep rejected candidates immutable. Select or design C01's canonical voice identity, preflight line duration, "
        "then generate a predeclared bounded audition batch through a distinct eligible engine/configuration. Send only "
        "an automated-gate-passing candidate to the hash-bound human playback workflow."
    )
    return payload


def update_report(path: Path, *, apply: bool) -> dict[str, Any]:
    payload = update_report_payload(json.loads(path.read_text(encoding="utf-8")))
    if apply:
        temporary = path.with_name(f".{path.name}.audio-control.tmp")
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    return {"item_id": payload["item_id"], "status": payload["status"], "row_complete": payload["row_complete"]}


def update_csv(path: Path, *, key: str, evidence_field: str, apply: bool) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    required = {key, "Status", evidence_field, "Notes", "Coverage_Audit_Status", "Human_Input_Allowed", "Human_Work_Allowed", "Blocker_Policy"}
    if required - set(fields):
        raise ValueError(f"missing CSV fields in {path}: {sorted(required - set(fields))}")
    changed: list[dict[str, str]] = []
    for row in rows:
        row_id = row.get(key, "")
        if not row_id.startswith(("ITEM-W64-", "TRK-W64-")):
            continue
        number = row_id[-3:]
        if number not in HUMAN_REVIEW_ROWS:
            continue
        row["Human_Input_Allowed"] = "TRUE"
        row["Human_Work_Allowed"] = "TRUE"
        row["Blocker_Policy"] = HUMAN_POLICY
        if key == "Tracker_ID":
            row["Autonomous_Execution_Mode"] = "Codex autonomous with bounded human playback judgment only after automated eligibility"
        else:
            row["Autonomous_Required"] = "TRUE"
        if number in ROW_STATUS:
            row["Status"] = ROW_STATUS[number]
            if "Status_Decision" in row:
                row["Status_Decision"] = ROW_STATUS[number]
        evidence_values: list[str] = []
        if number in INDEX_ROWS:
            evidence_values.append(INDEX_EVIDENCE)
        if number in CONTROL_ROWS:
            evidence_values.extend([CONTROL_EVIDENCE, CHATTERBOX_EVIDENCE])
        for evidence in evidence_values:
            row[evidence_field] = _append_unique(row.get(evidence_field, ""), evidence, "; ")
        for tag in (
            "audio_pack_functional_index_hash_bound",
            "human_audio_authority_schema_supported",
            "adult_specific_audio_standard_routing_no_suppression",
        ):
            row["Coverage_Audit_Status"] = _append_unique(row.get("Coverage_Audit_Status", ""), tag, "; ")
        row["Notes"] = _append_unique(row.get("Notes", ""), NOTE, " | ")
        changed.append({"id": row_id, "status": row["Status"]})
    if len(changed) != 9:
        raise ValueError(f"expected 9 Wave64 audio rows in {path}, found {len(changed)}")
    if apply:
        temporary = path.with_name(f".{path.name}.audio-control.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = {
        "mode": "apply" if args.apply else "dry_run",
        "verification": verify_evidence(),
        "reports": [update_report(ROOT / relative, apply=args.apply) for relative in REPORT_PATHS.values()],
        "tracker": [update_csv(ROOT / relative, key="Tracker_ID", evidence_field="Evidence_Path", apply=args.apply) for relative in TRACKER_PATHS],
        "items": [update_csv(ROOT / relative, key="Item_ID", evidence_field="Evidence_Required", apply=args.apply) for relative in ITEM_PATHS],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
