#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: sync TRK/ITEM-W64-010 Notes for PuLID FACE_04 VLM."""
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

ROW010_BLOCKER = (
    f"{EVID}/TRK-W64-010_CLASS_A_F_USER_AUTHORITY_FACE_REF_BLOCKER_PACKAGE_20260720.json"
)
ROW010_PROMOTION = (
    f"{EVID}/TRK-W64-010_C1_NAMED_AUTHORITY_PROMOTION_BINDINGS_20260721T0039-0500.json"
)
ROW010_PULID03_VLM = f"{EVID}/TRK-W64-010_RUNPOD_C1_PULID_FACE03_VLM_20260721T045654Z.json"
ROW010_PULID01_VLM = f"{EVID}/TRK-W64-010_RUNPOD_C1_PULID_FACE01_VLM_20260721T055828Z.json"
ROW010_LOCKFRONT_VLM = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_PULID_LOCKFRONT_VLM_20260721T061340Z.json"
)
ROW010_FTV2_VLM = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_PULID_FACE_TIGHTER_V2_VLM_20260721T101156Z.json"
)
ROW010_FACE04_CALIB = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_PULID_FACE04_CALIB_20260721T142217Z.json"
)
ROW010_FACE04_VLM = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_PULID_FACE04_VLM_20260721T142428Z.json"
)
OLLAMA_VLM_SMOKE = (
    f"{RUNTIME_EVID}/RUNPOD_1q4ji0gg1fkhvt_OLLAMA_VLM_FLUX_CANARY_SMOKE_PASS_20260721T041729Z.json"
)
VLM_ENDPOINT = "WAVE64_VLM_URL=http://127.0.0.1:11434"
SYNC_MARKER = "synced_by_primary_csv_mutator_row010_pulid_face04_vlm_sync_20260721"


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


def already_synced(notes: str) -> bool:
    return (
        "PuLID FACE04 VLM GATE CLEARED" in notes
        and "face_consistency_mean 0.7375" in notes
        and "142428Z" in notes
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
    notes = read_row010_notes()
    if already_synced(notes):
        print("tip", tip)
        print("no-op: TRK/ITEM-W64-010 PuLID FACE04 VLM Notes already synced")
        print("Row074 untouched")
        return

    vlm = load_json(ROW010_FACE04_VLM)
    calib = load_json(ROW010_FACE04_CALIB)
    assert vlm.get("row_complete") is False
    assert calib.get("row_complete") is False
    assert vlm["aggregate_scores"]["face_consistency_mean"] == 0.7375
    assert vlm["aggregate_scores"]["per_face_scores"]["face_04"] == 0.9
    assert vlm["gate"]["runtime_pass_bounded"] is True
    assert vlm["gate"]["faces_ok"] is True
    assert vlm["prompt_id"] == "b4be5abf-ae94-40cc-838b-4ff377484966"

    row074_notes_before = None
    with E2E_TRACKER.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("Tracker_ID") == "TRK-W64-074":
                row074_notes_before = row.get("Notes", "")
                break

    row010_notes = (
        "Class A/F USER_AUTHORITY face-ref blocker retained: portable multi-character "
        "reference pack still ABSENT (character_id_count=1 personal C1 only); "
        "C1 named-authority promotion bindings retained; "
        "RunPod PuLID FACE03 prior retained (a10b643b/045654Z face_mean 0.775); "
        "RunPod PuLID FACE01 prior retained (8a99678d/055828Z face_mean 0.7375); "
        "RunPod PuLID LOCKFRONT lock-trait FAIL retained (74f7f746/061340Z solo_lock 0.0); "
        "prior LoRA-only face-tighter BELOW_GATE retained (0.475); "
        "prior PuLID FACE_TIGHTER_V2 retained (79ea889f/101156Z face_mean 0.75; face_04=0.6); "
        "RunPod PuLID FACE04 (FACE_04 + head-shoulders crop + latina 0.78/0.58 weight 1.12) "
        f"VLM GATE CLEARED ({tip}/142428Z): qwen2.5vl:7b side_by_side_panel_v2 "
        "face_consistency_mean 0.7375 (n=4; face_01=0.6/face_02=0.85/face_03=0.6/face_04=0.9)/"
        "body_silhouette_mean 0.9/same_person_likelihood_mean 0.6833/"
        "solo_lock_trait_alignment 0.0; faces_ok=true body_ok=true lock_ok=false "
        "runtime_pass_bounded=true; prompt_id b4be5abf-ae94-40cc-838b-4ff377484966; "
        "face_04 panel improved 0.6->0.9 vs FACE_TIGHTER_V2; "
        "distinct from exhausted FACE_01/03/FACE_02-tighter-v2 envelopes; no invented faces; "
        "still NONCANONICAL; does NOT clear generic multi-character USER_AUTHORITY chain; "
        "row_complete=false; NEVER Complete. Blockers: "
        "USER_AUTHORITY_PER_CHARACTER_REFERENCE_CROPS_ABSENT|"
        "PORTABLE_MULTI_CHARACTER_ID_REFERENCE_PACKET_ABSENT|"
        "USER_AUTHORITY_FACE_BODY_REFERENCES_NOT_INVENTABLE|"
        "PERSONAL_CALIBRATION_CHARACTER1_EXCLUDED|"
        "SOLO_LOCK_TRAIT_ALIGNMENT_NOT_IMPROVED_REMAINS_ZERO. "
        f"Evidence: {ROW010_BLOCKER}; {ROW010_PROMOTION}; {ROW010_PULID03_VLM}; "
        f"{ROW010_PULID01_VLM}; {ROW010_LOCKFRONT_VLM}; {ROW010_FTV2_VLM}; "
        f"{ROW010_FACE04_CALIB}; {ROW010_FACE04_VLM}"
    )

    vlm_endpoint_note = (
        f"Durable RunPod Ollama VLM/LLM reviewer UP: {VLM_ENDPOINT} "
        f"(qwen2.5vl:7b). Evidence: {OLLAMA_VLM_SMOKE}"
    )

    row010_evidence = (
        f"{ROW010_BLOCKER}; {ROW010_PROMOTION}; {ROW010_PULID03_VLM}; "
        f"{ROW010_PULID01_VLM}; {ROW010_LOCKFRONT_VLM}; {ROW010_FTV2_VLM}; "
        f"{ROW010_FACE04_CALIB}; {ROW010_FACE04_VLM}; {OLLAMA_VLM_SMOKE}"
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

    if row074_notes_before is not None:
        with E2E_TRACKER.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("Tracker_ID") == "TRK-W64-074":
                    assert row.get("Notes", "") == row074_notes_before
                    break

    stamp_fields = {
        "csv_sync": SYNC_MARKER,
        "csv_sync_tip": tip,
        "csv_sync_prove_commits": [tip],
        "updated_at": NOW,
    }

    for rel in (
        ROW010_FACE04_VLM,
        "Plan/Tracker/Evidence/TRK-W64-010_RUNPOD_C1_PULID_FACE04_VLM_20260721T142428Z.json",
        ROW010_FACE04_CALIB,
        "Plan/Tracker/Evidence/TRK-W64-010_RUNPOD_C1_PULID_FACE04_CALIB_20260721T142217Z.json",
    ):
        obj = load_json(rel)
        obj.update(stamp_fields)
        assert obj.get("row_complete") is False
        dump_json(rel, obj)

    print("tip", tip)
    print(
        "synced TRK/ITEM-W64-010 PuLID FACE04 VLM GATE CLEARED Notes; "
        "face_mean 0.7375; face_04 0.9; NEVER Complete; row_complete=false"
    )
    print("Row074 untouched")


if __name__ == "__main__":
    main()
