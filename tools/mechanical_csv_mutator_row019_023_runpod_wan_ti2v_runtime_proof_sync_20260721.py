#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 Wan TI2V bounded runtime proof Notes sync."""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
NOW = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

E2E_TRACKER = ROOT / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv"
E2E_TRACKER_WAVES = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"
E2E_ITEMS = ROOT / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv"
E2E_ITEMS_WAVES = ROOT / "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"

EVID = "Plan/Instructions/QA/Evidence/Wave64"
PROOF = f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_20260721T004726-0500.json"
PROOF_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_20260721T004726-0500.json"
)
ASSET = f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_ASSET_PRESENT_20260721T003944-0500.json"
RECEIPT = (
    f"{EVID}/fixtures/row019_023/runtime/runpod_wan_ti2v_proof_20260721T054626Z/"
    "generation_receipt.json"
)
PULLBACK = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "runpod_wan_ti2v_proof_20260721T054626Z/"
    "w64_019_023_runpod_wan_ti2v_proof_20260721T054626Z_00001_.mp4"
)

PROMPT_ID = "3c525270-e87d-4fe0-9930-4c564e512626"
ARTIFACT_SHA = "bb3a6d02d07dad4cb9e65c357296c6345f08d9fa184231eb2c430ffbd51960e3"
STAMP = "20260721T004726-0500"
ASSET_COMMIT = "e76aaac6"
SYNC_MARKER = "synced_by_primary_csv_mutator_row019_023_runpod_wan_ti2v_runtime_proof"

STATUS_019 = (
    "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_Class_E_Runtime_Proof_Landed"
)
STATUS_023 = (
    "Blocked_Video_Frame_Repair_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_Class_E_Runtime_Proof_Landed"
)
DECISION = "runpod_wan_ti2v_class_e_runtime_proof_landed_no_complete"


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8"))


def dump_json(rel: str, obj: dict) -> None:
    path = ROOT / rel.replace("/", "\\")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_notes(tracker_id: str) -> str:
    with E2E_TRACKER_WAVES.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("Tracker_ID") == tracker_id:
                return row.get("Notes", "")
    raise RuntimeError(f"{tracker_id} missing from tracker CSV")


def already_synced(notes: str, tip: str) -> bool:
    return (
        STAMP in notes
        and PROMPT_ID in notes
        and "Class E Wan TI2V bounded runtime proof" in notes
        and tip in notes
        and "no COMPLETE" in notes
        and "Row074 left alone" in notes
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
            # hard guard: never touch Row074
            assert "074" not in key
            for col, val in updates[key].items():
                if col in row:
                    row[col] = val
    for key in updates:
        assert any(r[id_col] == key for r in rows), f"missing {key} in {path}"
    assert "TRK-W64-074" not in updates
    assert "ITEM-W64-074" not in updates
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_notes(tip: str, row: str) -> str:
    row_bit = (
        "immutable Row023 product visual QA reject retained; "
        if row == "023"
        else "video pipeline Class E runtime receipt landed; "
    )
    return (
        f"Class E Wan TI2V bounded runtime proof on RunPod "
        f"({ASSET_COMMIT}/{tip}/{STAMP}): "
        f"prompt_id={PROMPT_ID}; "
        "workflow=wan_2_2_ti2v_5b_primary_lane; "
        "artifact=/workspace/comfy_output/video/"
        "w64_019_023_runpod_wan_ti2v_proof_20260721T054626Z_00001_.mp4; "
        f"sha256={ARTIFACT_SHA}; bytes=94378; "
        f"{row_bit}"
        "Class F ASSET_PRESENT 3/3 retained; "
        "proof_tier=RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_GENERATION_RECEIPT; "
        "row_complete=false; no COMPLETE; Row074 left alone; EC2 untouched; "
        f"local Comfy untouched. Evidence: {PROOF}; {RECEIPT}; {ASSET}; {PULLBACK}"
    )


def main() -> None:
    tip = git_short()
    packet = load_json(PROOF)
    receipt = load_json(RECEIPT)
    assert packet.get("row_complete") is False
    assert packet.get("production_video_complete_claimed") is False
    assert packet.get("row074_touched") is False
    assert packet.get("generation", {}).get("prompt_id") == PROMPT_ID
    assert packet.get("generation", {}).get("completed") is True
    assert packet.get("generation", {}).get("artifact", {}).get("sha256") == ARTIFACT_SHA
    assert receipt.get("prompt_id") == PROMPT_ID
    assert receipt.get("completed") is True
    assert receipt.get("row_complete") is False

    dump_json(PROOF_TRACKER, packet)
    dump_json(f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json", packet)
    dump_json(
        "Plan/Tracker/Evidence/Wave64/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json",
        packet,
    )
    # mirror QA packet into Tracker evidence tree
    shutil.copy2(ROOT / PROOF.replace("/", "\\"), ROOT / PROOF_TRACKER.replace("/", "\\"))

    if already_synced(read_notes("TRK-W64-019"), tip) and already_synced(
        read_notes("TRK-W64-023"), tip
    ):
        print("tip", tip)
        print("no-op: TRK/ITEM-W64-019/023 runtime proof Notes already synced")
        print("Row074 untouched")
        return

    notes019 = build_notes(tip, "019")
    notes023 = build_notes(tip, "023")
    evid = f"{PROOF}; {RECEIPT}; {ASSET}; {PULLBACK}"
    tracker_updates = {
        "TRK-W64-019": {
            "Status": STATUS_019,
            "Status_Decision": DECISION,
            "Notes": notes019,
            "Evidence_Path": evid,
        },
        "TRK-W64-023": {
            "Status": STATUS_023,
            "Status_Decision": DECISION,
            "Notes": notes023,
            "Evidence_Path": evid,
        },
    }
    item_updates = {
        "ITEM-W64-019": {"Status": STATUS_019, "Notes": notes019},
        "ITEM-W64-023": {"Status": STATUS_023, "Notes": notes023},
    }

    rewrite_csv(E2E_TRACKER_WAVES, "Tracker_ID", tracker_updates)
    if E2E_TRACKER.exists():
        rewrite_csv(E2E_TRACKER, "Tracker_ID", tracker_updates)
    rewrite_csv(E2E_ITEMS_WAVES, "Item_ID", item_updates)
    if E2E_ITEMS.exists():
        with E2E_ITEMS.open(encoding="utf-8", newline="") as handle:
            present = {row.get("Item_ID") for row in csv.DictReader(handle)}
        subset = {k: v for k, v in item_updates.items() if k in present}
        if subset:
            rewrite_csv(E2E_ITEMS, "Item_ID", subset)

    sync_receipt = {
        "schema_version": "1.0",
        "mutator": SYNC_MARKER,
        "updated_utc": NOW,
        "tip": tip,
        "asset_present_commit": ASSET_COMMIT,
        "stamp": STAMP,
        "prompt_id": PROMPT_ID,
        "artifact_sha256": ARTIFACT_SHA,
        "rows": ["TRK-W64-019", "TRK-W64-023", "ITEM-W64-019", "ITEM-W64-023"],
        "status_019": STATUS_019,
        "status_023": STATUS_023,
        "status_decision": DECISION,
        "row074_touched": False,
        "complete_claimed": False,
        "row_complete": False,
        "evidence": PROOF,
    }
    dump_json(
        f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    dump_json(
        "Plan/Tracker/Evidence/Wave64/"
        f"TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    print("tip", tip)
    print("synced TRK/ITEM-W64-019/023 runtime proof Notes+Status")
    print("prompt_id", PROMPT_ID)
    print("Row074 untouched; no COMPLETE")


if __name__ == "__main__":
    main()
