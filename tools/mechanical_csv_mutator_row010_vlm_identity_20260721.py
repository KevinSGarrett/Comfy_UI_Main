#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: sync TRK/ITEM-W64-010 Notes for 73f185c5 VLM identity."""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
NOW = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

EVID = ROOT / "Plan/Instructions/QA/Evidence/Wave64"
RUNTIME_EVID = ROOT / "Plan/Instructions/QA/Evidence/Runtime_Readiness"

E2E_TRACKER = ROOT / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv"
E2E_TRACKER_WAVES = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"
E2E_ITEMS = ROOT / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv"
E2E_ITEMS_WAVES = ROOT / "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"

ROW010_BLOCKER = f"{EVID}/TRK-W64-010_CLASS_A_F_USER_AUTHORITY_FACE_REF_BLOCKER_PACKAGE_20260720.json"
ROW010_CALIB = f"{EVID}/TRK-W64-010_RUNPOD_C1_LOCK_LORA_CALIB_20260721T035348Z.json"
ROW010_VLM_IDENTITY = f"{EVID}/TRK-W64-010_RUNPOD_C1_LOCK_LORA_VLM_IDENTITY_20260721T041518Z.json"
ROW010_VLM_SUMMARY = f"{EVID}/TRK-W64-010_RUNPOD_C1_LOCK_LORA_VLM_IDENTITY_SUMMARY_20260721T041518Z.json"
FLUX_CANARY = f"{RUNTIME_EVID}/RUNPOD_1q4ji0gg1fkhvt_FLUX_CANARY_GENERATION_PASS_20260721T034826Z.json"
ROW084_VLM = f"{EVID}/TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_PRODUCTION_READINESS_PACKET_20260721.json"


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8"))


def dump_json(rel: str, obj: dict) -> None:
    path = ROOT / rel.replace("/", "\\")
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rewrite_csv(path: Path, id_col: str, updates: dict[str, dict[str, str]]) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    assert fields
    for row in rows:
        key = row[id_col]
        if key in updates:
            row.update(updates[key])
    for key in updates:
        assert any(r[id_col] == key for r in rows), f"missing {key} in {path}"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    tip = git_short()
    prove = ["73f185c5", tip]

    row010_notes = (
        "Class A/F USER_AUTHORITY face-ref blocker (b9085976/db81ab66): per-character reference "
        "crops absent and not inventable; proof_tier=OFFLINE_INVENTORY_BLOCKER_BOUNDED; "
        "RunPod personal-calibration RUNTIME_PASS_BOUNDED noncanonical (cf72e756): C1 lock+LoRA "
        "calib does NOT clear generic multi-character USER_AUTHORITY chain; RunPod C1 lock+LoRA "
        "VLM identity RUNTIME_SCORED_PERSONAL_CALIBRATION_VLM_BELOW_GATE_NONCANONICAL "
        f"({prove[0]}/{prove[1]}): qwen2.5vl:7b face 0.44/body 0.45 below gate (min 0.55); "
        "solo lock 0.95 ok; personal-calibration VLM scored against existing C1 USER_AUTHORITY "
        "refs; does NOT clear portable multi-character USER_AUTHORITY chain; row_complete=false; "
        "no COMPLETE. Blockers: USER_AUTHORITY_PER_CHARACTER_REFERENCE_CROPS_ABSENT|"
        "USER_AUTHORITY_FACE_BODY_REFERENCES_NOT_INVENTABLE|"
        "PORTABLE_MULTI_CHARACTER_REFERENCE_CHAIN_ABSENT|PERSONAL_CALIBRATION_CHARACTER1_EXCLUDED. "
        f"Evidence: {ROW010_BLOCKER}; {ROW010_CALIB}; {ROW010_VLM_IDENTITY}"
    )

    autonomy_vlm_note = (
        "Autonomy/VLM bounded RunPod probe landed (77dac184): ROW084-011 Class E "
        "RUNTIME_PROBE_VISUAL_BOUNDED on pod 1q4ji0gg1fkhvt; ROW084-011 remains HOLD; "
        f"no product COMPLETE. Evidence: {ROW084_VLM}"
    )

    row010_evidence = (
        f"{ROW010_BLOCKER}; {ROW010_CALIB}; {ROW010_VLM_IDENTITY}; {ROW010_VLM_SUMMARY}; "
        f"{FLUX_CANARY}"
    )

    e2e_tracker_updates = {
        "TRK-W64-010": {
            "Status": "Blocked_Identity_Reference_Proof_Missing_Separation_And_Merge_Rejection_Pass",
            "Notes": row010_notes + " " + autonomy_vlm_note,
            "Evidence_Path": row010_evidence,
        },
    }
    e2e_item_updates = {
        "ITEM-W64-010": {
            "Status": "Blocked_Identity_Reference_Proof_Missing_Separation_And_Merge_Rejection_Pass",
            "Notes": row010_notes,
        },
    }

    rewrite_csv(E2E_TRACKER, "Tracker_ID", e2e_tracker_updates)
    rewrite_csv(E2E_TRACKER_WAVES, "Tracker_ID", e2e_tracker_updates)
    rewrite_csv(E2E_ITEMS, "Item_ID", e2e_item_updates)
    rewrite_csv(E2E_ITEMS_WAVES, "Item_ID", e2e_item_updates)

    for rel in (ROW010_VLM_IDENTITY, ROW010_VLM_SUMMARY):
        stamp = load_json(rel)
        stamp["csv_sync"] = "synced_by_primary_csv_mutator_row010_vlm_identity_20260721"
        stamp["csv_sync_tip"] = tip
        stamp["csv_sync_prove_commits"] = prove
        stamp["updated_at"] = NOW
        dump_json(rel, stamp)

    print("tip", tip)
    print("synced TRK/ITEM-W64-010 only; Row074 untouched")


if __name__ == "__main__":
    main()
