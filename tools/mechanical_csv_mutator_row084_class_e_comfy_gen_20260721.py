#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row084 Class E Comfy gen+VLM only. Row074 untouched."""
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
ROW084_PACKET = f"{EVID}/TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_COMFY_GENERATION_PACKET_20260721.json"
ROW084_VLM = f"{EVID}/TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_COMFY_GENERATION_VLM_REVIEW_20260721.json"
ROW084_DELTA = f"{EVID}/TRK-W64-084_CANONICAL_VIDEO_TIMELINE_CURRENT_DELTA_20260719.json"
ROW084_ARTIFACT = f"{EVID}/TRK-W64-084_canonical_video_timeline.json"
ROW084_HOLD_012 = (
    f"{EVID}/TRK-W64-084_ROW084-012_CLASS_C_SCHEMA_NATIVE_REVERSED_PTS_HOLD_PACKET_20260720.json"
)
ROW084_RECEIPT = (
    f"{EVID}/fixtures/row084/runtime/runpod_class_e_comfy_gen_20260721T050810Z/"
    "class_e_comfy_generation_receipt.json"
)
PROMPT_ID = "8681ba01-58a4-4a92-92cf-171d5c2daaf3"
PROOF = "RUNTIME_COMFY_GENERATION_RECEIPT_WITH_VLM_REVIEW"


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
        # hard guard: never touch 074
        assert "074" not in key or key in updates
    # verify 074 rows unchanged by ensuring we never listed them
    assert "TRK-W64-074" not in updates
    assert "ITEM-W64-074" not in updates
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    tip = git_short()
    packet = load_json(ROW084_PACKET)
    vlm = load_json(ROW084_VLM)
    receipt = load_json(ROW084_RECEIPT)

    assert packet.get("row_complete") is False
    assert packet.get("production_completion_allowed") is False
    assert packet.get("row084_011_status") == "FAIL"
    assert packet.get("cleared") is False
    assert packet.get("hold_012_unchanged", {}).get("status") == "OPEN_HOLD"
    assert packet.get("prompt_id") == PROMPT_ID
    assert receipt.get("generation", {}).get("prompt_id") == PROMPT_ID
    assert receipt.get("generation", {}).get("completed") is True
    assert vlm.get("row084_011_status") == "FAIL"
    assert vlm.get("vlm_ok_frame_count", 0) >= 1

    row084_status = (
        "Blocked_Visual_Qa_Pass_Bounded_Class_C_Schema_Native_Hold_And_Production_Completion_Blocked"
    )
    row084_decision = "row084_class_e_runpod_comfy_gen_vlm_probed_no_complete"
    row084_notes = (
        f"Class E Comfy+VLM deepen: live RunPod generation prompt_id={PROMPT_ID} "
        f"ckpt=realvisxlV50_v50Bakedvae ({PROOF}); Ollama qwen2.5vl:7b 1/1 frame. "
        "ROW084-011 Class E FAIL/OPEN retained (production COMPLETE withheld); "
        "ROW084-012 Class C OPEN_HOLD unchanged (0e0c3d86); ROW084-015/017/013 PASS retained; "
        f"row_complete=false; NEVER Complete; Row074 left alone; RunPod ONLY (no EC2). "
        f"Evidence: {ROW084_PACKET}; {ROW084_VLM}; {ROW084_RECEIPT}; {ROW084_DELTA}; "
        f"{ROW084_HOLD_012}"
    )
    row084_evidence = (
        f"{ROW084_ARTIFACT}; {ROW084_DELTA}; {ROW084_PACKET}; "
        f"{ROW084_VLM}; {ROW084_RECEIPT}; {ROW084_HOLD_012}"
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
    delta["proof_tier"] = PROOF
    delta["highest_proof_tier_achieved"] = PROOF
    delta["ledger_vocabulary_sync"] = {
        "ledger_status": row084_status,
        "note": f"Mechanical CSV mutator Row084 Class E Comfy gen+VLM from tip {tip}; no COMPLETE.",
        "product_completion": False,
        "runtime_completion": False,
        "synced_at": NOW,
        "prove_commits": [tip],
        "prompt_id": PROMPT_ID,
        "row074_left_alone": True,
        "ec2_unused": True,
    }
    delta["csv_sync"] = "synced_by_primary_csv_mutator_row084_class_e_comfy_gen"
    delta["csv_sync_tip"] = tip
    dump_json(ROW084_DELTA, delta)

    packet["csv_sync"] = "synced_by_primary_csv_mutator_row084_class_e_comfy_gen"
    packet["csv_sync_tip"] = tip
    dump_json(ROW084_PACKET, packet)

    vlm["csv_sync"] = "synced_by_primary_csv_mutator_row084_class_e_comfy_gen"
    vlm["csv_sync_tip"] = tip
    dump_json(ROW084_VLM, vlm)

    print("tip", tip)
    print("synced TRK/ITEM-W64-084 Class E Comfy gen+VLM", PROMPT_ID)
    print("ROW084-011 FAIL/OPEN retained; ROW084-012 OPEN_HOLD; row_complete=false")
    print("Row074 left alone; EC2 unused")


if __name__ == "__main__":
    main()
