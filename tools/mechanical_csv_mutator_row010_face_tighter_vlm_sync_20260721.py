#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: sync TRK/ITEM-W64-010 Notes for e0a7830e face-tighter VLM."""
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
ROW010_VLM_PANEL_V2 = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_LOCK_LORA_VLM_IDENTITY_20260721T041746Z.json"
)
ROW010_FACE_TIGHTER_CALIB = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_FACE_TIGHTER_CALIB_20260721T043424Z.json"
)
ROW010_FACE_TIGHTER_VLM = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_FACE_TIGHTER_VLM_20260721T043808Z.json"
)
OLLAMA_VLM_SMOKE = (
    f"{RUNTIME_EVID}/RUNPOD_1q4ji0gg1fkhvt_OLLAMA_VLM_FLUX_CANARY_SMOKE_PASS_20260721T041729Z.json"
)
VLM_ENDPOINT = "WAVE64_VLM_URL=http://127.0.0.1:11434"
SYNC_MARKER = "synced_by_primary_csv_mutator_row010_face_tighter_vlm_sync_20260721"
PANEL_V2_PROVE = "f7081a0d"
FACE_TIGHTER_PROVE = "e0a7830e"


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8"))


def dump_json(rel: str, obj: dict) -> None:
    path = ROOT / rel.replace("/", "\\")
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_row010_notes() -> str:
    with E2E_TRACKER.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("Tracker_ID") == "TRK-W64-010":
                return row.get("Notes", "")
    raise RuntimeError("TRK-W64-010 missing from tracker CSV")


def already_synced(notes: str, prove: list[str]) -> bool:
    return (
        "face-tighter VLM BELOW_GATE" in notes
        and "face_consistency_mean 0.475" in notes
        and f"panel-v2 VLM GATE CLEARED ({PANEL_V2_PROVE}/041746Z)" in notes
        and prove[0] in notes
        and "NEVER Complete" in notes
    )


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
    prove = [FACE_TIGHTER_PROVE, tip]
    notes = read_row010_notes()
    if already_synced(notes, prove):
        print("tip", tip)
        print("no-op: TRK/ITEM-W64-010 face-tighter VLM Notes already synced")
        print("Row074 untouched")
        return

    vlm = load_json(ROW010_FACE_TIGHTER_VLM)
    assert vlm.get("row_complete") is False
    assert vlm["aggregate_scores"]["face_consistency_mean"] == 0.475
    assert vlm["gate"]["runtime_pass_bounded"] is False

    row010_notes = (
        "Class A/F USER_AUTHORITY face-ref blocker (b9085976/db81ab66): per-character reference "
        "crops absent and not inventable; proof_tier=OFFLINE_INVENTORY_BLOCKER_BOUNDED; "
        "RunPod personal-calibration panel-v2 VLM GATE CLEARED "
        f"({PANEL_V2_PROVE}/041746Z): qwen2.5vl:7b side_by_side_panel_v2 face_consistency_mean "
        "0.5625 (n=4)/body_silhouette_mean 0.9/solo_lock_trait_alignment 0.95; "
        "runtime_pass_bounded=true; still NONCANONICAL; C1 lock+LoRA calib (035348Z/cf72e756) "
        "retained; RunPod personal-calibration face-tighter VLM BELOW_GATE "
        f"({prove[0]}/043808Z): qwen2.5vl:7b side_by_side_panel_v2 face_consistency_mean 0.475 "
        "(n=4)/body_silhouette_mean 0.9/solo_lock_trait_alignment 0.95; runtime_pass_bounded=false; "
        "face-tighter calib (043424Z) retained; multi-character USER_AUTHORITY retained blocked; "
        "does NOT clear generic multi-character USER_AUTHORITY chain; row_complete=false; "
        "NEVER Complete. Blockers: USER_AUTHORITY_PER_CHARACTER_REFERENCE_CROPS_ABSENT|"
        "USER_AUTHORITY_FACE_BODY_REFERENCES_NOT_INVENTABLE|"
        "PORTABLE_MULTI_CHARACTER_REFERENCE_CHAIN_ABSENT|PERSONAL_CALIBRATION_CHARACTER1_EXCLUDED. "
        f"Evidence: {ROW010_BLOCKER}; {ROW010_CALIB}; {ROW010_VLM_PANEL_V2}; "
        f"{ROW010_FACE_TIGHTER_CALIB}; {ROW010_FACE_TIGHTER_VLM}"
    )

    vlm_endpoint_note = (
        f"Durable RunPod Ollama VLM/LLM reviewer UP (e1401895/{tip}): {VLM_ENDPOINT} "
        f"(llava:13b / qwen2.5:7b-instruct); Flux canary VLM smoke PASS_WITH_NOTES. "
        f"Evidence: {OLLAMA_VLM_SMOKE}"
    )

    row010_evidence = (
        f"{ROW010_BLOCKER}; {ROW010_CALIB}; {ROW010_VLM_PANEL_V2}; "
        f"{ROW010_FACE_TIGHTER_CALIB}; {ROW010_FACE_TIGHTER_VLM}; {OLLAMA_VLM_SMOKE}"
    )

    e2e_tracker_updates = {
        "TRK-W64-010": {
            "Status": "Blocked_Identity_Reference_Proof_Missing_Separation_And_Merge_Rejection_Pass",
            "Notes": row010_notes + " " + vlm_endpoint_note,
            "Evidence_Path": row010_evidence,
        },
    }
    e2e_item_updates = {
        "ITEM-W64-010": {
            "Status": "Blocked_Identity_Reference_Proof_Missing_Separation_And_Merge_Rejection_Pass",
            "Notes": row010_notes + " " + vlm_endpoint_note,
        },
    }

    rewrite_csv(E2E_TRACKER, "Tracker_ID", e2e_tracker_updates)
    rewrite_csv(E2E_TRACKER_WAVES, "Tracker_ID", e2e_tracker_updates)
    rewrite_csv(E2E_ITEMS, "Item_ID", e2e_item_updates)
    rewrite_csv(E2E_ITEMS_WAVES, "Item_ID", e2e_item_updates)

    stamp_fields = {
        "csv_sync": SYNC_MARKER,
        "csv_sync_tip": tip,
        "csv_sync_prove_commits": prove,
        "updated_at": NOW,
    }

    for rel in (
        ROW010_FACE_TIGHTER_VLM,
        "Plan/Tracker/Evidence/TRK-W64-010_RUNPOD_C1_FACE_TIGHTER_VLM_20260721T043808Z.json",
        ROW010_FACE_TIGHTER_CALIB,
        "Plan/Tracker/Evidence/TRK-W64-010_RUNPOD_C1_FACE_TIGHTER_CALIB_20260721T043424Z.json",
    ):
        obj = load_json(rel)
        obj.update(stamp_fields)
        dump_json(rel, obj)

    print("tip", tip)
    print("synced TRK/ITEM-W64-010 face-tighter VLM BELOW_GATE Notes; panel-v2 GATE CLEARED retained")
    print("Row074 untouched")


if __name__ == "__main__":
    main()
