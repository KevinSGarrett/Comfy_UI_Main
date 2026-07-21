#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: sync TRK/ITEM-W64-010 Notes for PuLID SIDE VLM.

Scores are read from landed evidence (not hard-coded) so pass/fail stays honest.
"""
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
ROW010_BF_VLM = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_PULID_BODYFORWARD_VLM_20260721T145516Z.json"
)
OLLAMA_VLM_SMOKE = (
    f"{RUNTIME_EVID}/RUNPOD_1q4ji0gg1fkhvt_OLLAMA_VLM_FLUX_CANARY_SMOKE_PASS_20260721T041729Z.json"
)
VLM_ENDPOINT = "WAVE64_VLM_URL=http://127.0.0.1:11434"
SYNC_MARKER = "synced_by_primary_csv_mutator_row010_pulid_side_vlm_sync_20260721"


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8"))


def dump_json(rel: str, obj: dict) -> None:
    path = ROOT / rel.replace("/", "\\")
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def latest_side_pair() -> tuple[Path, Path]:
    calibs = sorted(EVID.glob("TRK-W64-010_RUNPOD_C1_PULID_SIDE_CALIB_*.json"))
    vlms = sorted(EVID.glob("TRK-W64-010_RUNPOD_C1_PULID_SIDE_VLM_*.json"))
    if not calibs or not vlms:
        raise RuntimeError("missing landed SIDE calib/vlm evidence under QA Evidence")
    return calibs[-1], vlms[-1]


def read_row010_notes() -> str:
    with E2E_TRACKER.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("Tracker_ID") == "TRK-W64-010":
                return row.get("Notes", "")
    raise RuntimeError("TRK-W64-010 missing from tracker CSV")


def already_synced(notes: str, vlm_stamp: str) -> bool:
    return (
        "PuLID SIDE" in notes
        and vlm_stamp in notes
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
    calib_path, vlm_path = latest_side_pair()
    calib = json.loads(calib_path.read_text(encoding="utf-8"))
    vlm = json.loads(vlm_path.read_text(encoding="utf-8"))
    vlm_id = vlm["evidence_id"]
    calib_id = calib["evidence_id"]
    vlm_stamp = vlm_id.rsplit("_", 1)[-1]
    notes = read_row010_notes()
    if already_synced(notes, vlm_stamp):
        print("tip", tip)
        print("no-op: TRK/ITEM-W64-010 PuLID SIDE VLM Notes already synced")
        print("Row074 untouched")
        return

    assert vlm.get("row_complete") is False
    assert calib.get("row_complete") is False
    agg = vlm["aggregate_scores"]
    gate = vlm["gate"]
    face = agg["face_consistency_mean"]
    body = agg["body_silhouette_consistency_mean"]
    same = agg["same_person_likelihood_mean"]
    solo = agg["solo_lock_trait_alignment_score"]
    face_n = agg["face_consistency_n"]
    body_n = agg["body_silhouette_consistency_n"]
    status = vlm["status"]
    prompt_id = calib.get("prompt_id") or vlm.get("prompt_id")

    # Honest status tag for Notes
    if "LOCK_TRAIT_NOT_IMPROVED" in status:
        outcome = "LOCK_TRAIT_NOT_IMPROVED"
    elif "BELOW_GATE" in status:
        outcome = "BELOW_GATE"
    elif "RUNTIME_PASS" in status:
        outcome = "RUNTIME_PASS_BOUNDED"
    else:
        outcome = status.split("_PULID_")[0] if "_PULID_" in status else status

    row074_notes_before = None
    with E2E_TRACKER.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("Tracker_ID") == "TRK-W64-074":
                row074_notes_before = row.get("Notes", "")
                break

    row010_calib_rel = f"{EVID}/{calib_id}.json".replace("\\", "/")
    row010_vlm_rel = f"{EVID}/{vlm_id}.json".replace("\\", "/")
    # Prefer repo-relative paths like prior mutators
    row010_calib_rel = f"Plan/Instructions/QA/Evidence/Wave64/{calib_id}.json"
    row010_vlm_rel = f"Plan/Instructions/QA/Evidence/Wave64/{vlm_id}.json"

    row010_notes = (
        "Class A/F USER_AUTHORITY face-ref blocker retained: portable multi-character "
        "reference pack still ABSENT (character_id_count=1 personal C1 only); "
        "prior PuLID FACE04 GATE CLEARED retained (142428Z face_mean 0.7375); "
        "prior PuLID BODYFORWARD lock-trait FAIL retained (145516Z solo_lock 0.0); "
        "RunPod PuLID SIDE (FACE_04 PuLID + C1_USER_AUTHORITY_SIDE_20260719 full-body "
        f"side composition + latina 0.78/0.58 weight 1.12) VLM {outcome} "
        f"({tip}/{vlm_stamp} prompt_id={prompt_id}): "
        f"qwen2.5vl:7b side_by_side_panel_v2 face_consistency_mean {face} (n={face_n})/"
        f"body_silhouette_mean {body} (n={body_n})/same_person_likelihood_mean {same}/"
        f"solo_lock_trait_alignment {solo}; faces_ok={gate.get('faces_ok')} "
        f"body_ok={gate.get('body_ok')} lock_ok={gate.get('lock_ok')} "
        f"lock_improved={gate.get('lock_improved_vs_prior_zero')} "
        f"runtime_pass_bounded={gate.get('runtime_pass_bounded')}; "
        "distinct from exhausted FACE_01/03/FACE_02-tighter-v2/FACE_04 face-crop, "
        "LOCKFRONT FACE_01, and BODYFORWARD FRONT envelopes; no invented faces; "
        "still NONCANONICAL; does NOT clear generic multi-character USER_AUTHORITY chain; "
        "row_complete=false; NEVER Complete. Blockers: "
        "USER_AUTHORITY_PER_CHARACTER_REFERENCE_CROPS_ABSENT|"
        "PORTABLE_MULTI_CHARACTER_ID_REFERENCE_PACKET_ABSENT|"
        "USER_AUTHORITY_FACE_BODY_REFERENCES_NOT_INVENTABLE|"
        "PERSONAL_CALIBRATION_CHARACTER1_EXCLUDED|"
        "SOLO_LOCK_TRAIT_ALIGNMENT_NOT_CLEARED. "
        f"Evidence: {ROW010_BLOCKER}; {ROW010_PROMOTION}; {ROW010_LOCKFRONT_VLM}; "
        f"{ROW010_FACE04_VLM}; {ROW010_BF_VLM}; {row010_calib_rel}; {row010_vlm_rel}"
    )

    vlm_endpoint_note = (
        f"Durable RunPod Ollama VLM/LLM reviewer UP: {VLM_ENDPOINT} "
        f"(qwen2.5vl:7b). Evidence: {OLLAMA_VLM_SMOKE}"
    )

    row010_evidence = (
        f"{ROW010_BLOCKER}; {ROW010_PROMOTION}; {ROW010_LOCKFRONT_VLM}; "
        f"{ROW010_FACE04_VLM}; {ROW010_BF_VLM}; {row010_calib_rel}; {row010_vlm_rel}; "
        f"{OLLAMA_VLM_SMOKE}"
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
        row010_vlm_rel,
        f"Plan/Tracker/Evidence/{vlm_id}.json",
        row010_calib_rel,
        f"Plan/Tracker/Evidence/{calib_id}.json",
    ):
        obj = load_json(rel)
        obj.update(stamp_fields)
        assert obj.get("row_complete") is False
        dump_json(rel, obj)

    print("tip", tip)
    print(
        f"synced TRK/ITEM-W64-010 PuLID SIDE VLM {outcome}; "
        f"face_mean {face} body {body} solo_lock {solo}; "
        f"prompt_id={prompt_id}; NEVER Complete; row_complete=false"
    )
    print("Row074 untouched")


if __name__ == "__main__":
    main()
