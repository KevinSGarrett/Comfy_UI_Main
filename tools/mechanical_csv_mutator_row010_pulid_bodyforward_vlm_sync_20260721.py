#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: sync TRK/ITEM-W64-010 Notes for PuLID BODYFORWARD VLM."""
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
ROW010_LOCKFRONT_VLM = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_PULID_LOCKFRONT_VLM_20260721T061340Z.json"
)
ROW010_FACE04_VLM = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_PULID_FACE04_VLM_20260721T142428Z.json"
)
ROW010_BF_CALIB = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_PULID_BODYFORWARD_CALIB_20260721T145336Z.json"
)
ROW010_BF_VLM = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_PULID_BODYFORWARD_VLM_20260721T145516Z.json"
)
OLLAMA_VLM_SMOKE = (
    f"{RUNTIME_EVID}/RUNPOD_1q4ji0gg1fkhvt_OLLAMA_VLM_FLUX_CANARY_SMOKE_PASS_20260721T041729Z.json"
)
VLM_ENDPOINT = "WAVE64_VLM_URL=http://127.0.0.1:11434"
SYNC_MARKER = "synced_by_primary_csv_mutator_row010_pulid_bodyforward_vlm_sync_20260721"


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
        "PuLID BODYFORWARD" in notes
        and "145516Z" in notes
        and "LOCK_TRAIT_NOT_IMPROVED" in notes
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
        print("no-op: TRK/ITEM-W64-010 PuLID BODYFORWARD VLM Notes already synced")
        print("Row074 untouched")
        return

    vlm = load_json(ROW010_BF_VLM)
    calib = load_json(ROW010_BF_CALIB)
    assert vlm.get("row_complete") is False
    assert calib.get("row_complete") is False
    assert vlm["aggregate_scores"]["face_consistency_mean"] == 0.6
    assert vlm["aggregate_scores"]["body_silhouette_consistency_mean"] == 0.9
    assert vlm["aggregate_scores"]["solo_lock_trait_alignment_score"] == 0.0
    assert vlm["gate"]["faces_ok"] is True
    assert vlm["gate"]["body_ok"] is True
    assert vlm["gate"]["lock_ok"] is False
    assert vlm["gate"]["lock_improved_vs_prior_zero"] is False
    assert "LOCK_TRAIT_NOT_IMPROVED" in vlm["status"]

    row074_notes_before = None
    with E2E_TRACKER.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("Tracker_ID") == "TRK-W64-074":
                row074_notes_before = row.get("Notes", "")
                break

    row010_notes = (
        "Class A/F USER_AUTHORITY face-ref blocker retained: portable multi-character "
        "reference pack still ABSENT (character_id_count=1 personal C1 only); "
        "prior PuLID FACE04 GATE CLEARED retained (142428Z face_mean 0.7375); "
        "prior PuLID LOCKFRONT lock-trait FAIL retained (061340Z solo_lock 0.0); "
        "RunPod PuLID BODYFORWARD (FACE_04 PuLID + FRONT/LOCK_FRONT full-body composition "
        f"+ latina 0.78/0.58 weight 1.12) VLM LOCK_TRAIT_NOT_IMPROVED ({tip}/145516Z): "
        "qwen2.5vl:7b side_by_side_panel_v2 face_consistency_mean 0.6 (n=4 all 0.6)/"
        "body_silhouette_mean 0.9 (n=3)/same_person_likelihood_mean 0.6143/"
        "solo_lock_trait_alignment 0.0; faces_ok=true body_ok=true lock_ok=false "
        "lock_improved=false runtime_pass_bounded=false; "
        "distinct from exhausted FACE_01/03/FACE_02-tighter-v2/FACE_04 face-crop and "
        "from prior LOCKFRONT FACE_01 envelope; no invented faces; still NONCANONICAL; "
        "does NOT clear generic multi-character USER_AUTHORITY chain; "
        "row_complete=false; NEVER Complete. Blockers: "
        "USER_AUTHORITY_PER_CHARACTER_REFERENCE_CROPS_ABSENT|"
        "PORTABLE_MULTI_CHARACTER_ID_REFERENCE_PACKET_ABSENT|"
        "USER_AUTHORITY_FACE_BODY_REFERENCES_NOT_INVENTABLE|"
        "PERSONAL_CALIBRATION_CHARACTER1_EXCLUDED|"
        "SOLO_LOCK_TRAIT_ALIGNMENT_NOT_IMPROVED_REMAINS_ZERO. "
        f"Evidence: {ROW010_BLOCKER}; {ROW010_PROMOTION}; {ROW010_LOCKFRONT_VLM}; "
        f"{ROW010_FACE04_VLM}; {ROW010_BF_CALIB}; {ROW010_BF_VLM}"
    )

    vlm_endpoint_note = (
        f"Durable RunPod Ollama VLM/LLM reviewer UP: {VLM_ENDPOINT} "
        f"(qwen2.5vl:7b). Evidence: {OLLAMA_VLM_SMOKE}"
    )

    row010_evidence = (
        f"{ROW010_BLOCKER}; {ROW010_PROMOTION}; {ROW010_LOCKFRONT_VLM}; "
        f"{ROW010_FACE04_VLM}; {ROW010_BF_CALIB}; {ROW010_BF_VLM}; {OLLAMA_VLM_SMOKE}"
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
        ROW010_BF_VLM,
        "Plan/Tracker/Evidence/TRK-W64-010_RUNPOD_C1_PULID_BODYFORWARD_VLM_20260721T145516Z.json",
        ROW010_BF_CALIB,
        "Plan/Tracker/Evidence/TRK-W64-010_RUNPOD_C1_PULID_BODYFORWARD_CALIB_20260721T145336Z.json",
    ):
        obj = load_json(rel)
        obj.update(stamp_fields)
        assert obj.get("row_complete") is False
        dump_json(rel, obj)

    print("tip", tip)
    print(
        "synced TRK/ITEM-W64-010 PuLID BODYFORWARD VLM LOCK_TRAIT_NOT_IMPROVED; "
        "face_mean 0.6 body 0.9 solo_lock 0.0; NEVER Complete; row_complete=false"
    )
    print("Row074 untouched")


if __name__ == "__main__":
    main()
