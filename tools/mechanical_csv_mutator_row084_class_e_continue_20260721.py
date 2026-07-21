#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row084 Class E continue (c44d1dd9/83da2a63) only. Row074 untouched."""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
NOW = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

SOUND_TRACKER = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_TRACKER_ROWS.csv"
SOUND_ITEMS = ROOT / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_ITEM_ROWS.csv"

EVID = "Plan/Instructions/QA/Evidence/Wave64"
ROW084_PACKET = f"{EVID}/TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_PRODUCTION_READINESS_PACKET_20260721.json"
ROW084_VLM_REVIEW = f"{EVID}/TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_VLM_REVIEW_20260721.json"
ROW084_DELTA = f"{EVID}/TRK-W64-084_CANONICAL_VIDEO_TIMELINE_CURRENT_DELTA_20260719.json"
ROW084_ARTIFACT = f"{EVID}/TRK-W64-084_canonical_video_timeline.json"
ROW084_HOLD_012 = (
    f"{EVID}/TRK-W64-084_ROW084-012_CLASS_C_SCHEMA_NATIVE_REVERSED_PTS_HOLD_PACKET_20260720.json"
)
PROVE = ["c44d1dd9", "83da2a63"]


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
    prove = PROVE + [tip]
    packet = load_json(ROW084_PACKET)
    vlm = load_json(ROW084_VLM_REVIEW)

    assert packet.get("row_complete") is False
    assert packet.get("production_completion_allowed") is False
    assert packet.get("row084_011_status") == "FAIL"
    assert packet.get("hold_012_unchanged", {}).get("status") == "OPEN_HOLD"
    assert vlm.get("row084_011_status") == "FAIL"
    assert vlm.get("vlm_ok_frame_count", sum(1 for r in vlm.get("reviews", []) if r.get("ok"))) == 3

    row084_status = (
        "Blocked_Visual_Qa_Pass_Bounded_Class_C_Schema_Native_Hold_And_Production_Completion_Blocked"
    )
    row084_decision = "row084_class_e_runpod_readiness_vlm_probed_no_complete"
    row084_proof = "RUNTIME_PROBE_VISUAL_BOUNDED_WITH_VLM_REVIEW"
    row084_blockers = [
        "PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED",
        "CLOCK_SPAN_REVERSED_PTS_JSON_SCHEMA_NATIVE_ABSENT",
        "COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED",
    ]
    row084_notes = (
        "Class E continue (c44d1dd9/83da2a63): RunPod Comfy :8188 re-probe "
        f"{row084_proof}; Ollama qwen2.5vl:7b 3/3 frames reviewed. "
        "ROW084-011 Class E FAIL/OPEN retained (production COMPLETE withheld); "
        "ROW084-012 Class C OPEN_HOLD unchanged (0e0c3d86); ROW084-015/017/013 PASS retained; "
        f"row_complete=false; NEVER Complete; Row074 left alone. Evidence: {ROW084_PACKET}; "
        f"{ROW084_VLM_REVIEW}; {ROW084_DELTA}; {ROW084_HOLD_012}"
    )
    row084_evidence = (
        f"{ROW084_ARTIFACT}; {ROW084_DELTA}; {ROW084_PACKET}; "
        f"{ROW084_VLM_REVIEW}; {ROW084_HOLD_012}"
    )

    sound_tracker_updates = {
        "TRK-W64-084": {
            "Status": row084_status,
            "Status_Decision": row084_decision,
            "Notes": row084_notes,
            "Evidence_Path": row084_evidence,
        },
    }
    sound_item_updates = {
        "ITEM-W64-084": {
            "Status": row084_status,
            "Notes": row084_notes,
        },
    }

    rewrite_csv(SOUND_TRACKER, "Tracker_ID", sound_tracker_updates)
    rewrite_csv(SOUND_ITEMS, "Item_ID", sound_item_updates)

    delta = load_json(ROW084_DELTA)
    delta["updated_at"] = NOW
    delta["row_complete"] = False
    delta["proof_tier"] = row084_proof
    delta["highest_proof_tier_achieved"] = row084_proof
    delta["ledger_vocabulary_sync"] = {
        "ledger_status": row084_status,
        "note": f"Mechanical CSV mutator Row084 Class E continue from {','.join(prove)}; no COMPLETE.",
        "product_completion": False,
        "runtime_completion": False,
        "synced_at": NOW,
        "prove_commits": prove,
        "row074_left_alone": True,
    }
    delta["csv_sync"] = "synced_by_primary_csv_mutator_row084_class_e_continue"
    delta["csv_sync_tip"] = tip
    dump_json(ROW084_DELTA, delta)

    packet["csv_sync"] = "synced_by_primary_csv_mutator_row084_class_e_continue"
    packet["csv_sync_tip"] = tip
    dump_json(ROW084_PACKET, packet)

    vlm["csv_sync"] = "synced_by_primary_csv_mutator_row084_class_e_continue"
    vlm["csv_sync_tip"] = tip
    dump_json(ROW084_VLM_REVIEW, vlm)

    print("tip", tip)
    print("synced TRK/ITEM-W64-084 Class E continue", prove)
    print("ROW084-011 FAIL/OPEN retained; ROW084-012 OPEN_HOLD; row_complete=false")
    print("Row074 left alone")


if __name__ == "__main__":
    main()
