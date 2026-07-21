#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 Wan TI2V ASSET_PRESENT Notes sync."""
from __future__ import annotations

import csv
import json
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
ASSET = f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_ASSET_PRESENT_20260721T003944-0500.json"
ASSET_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_RUNPOD_WAN_TI2V_ASSET_PRESENT_20260721T003944-0500.json"
)
FETCH_STARTED = (
    f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_FETCH_STARTED_20260721T001629-0500.json"
)
PRIOR_BLOCKER = (
    f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_NO_APPROVED_FETCH_SCRIPT_BLOCKER_20260721T000852-0500.json"
)

SCRIPT_LAND = "d7b93566"
FETCH_STARTED_COMMIT = "6a2a57ab"
STAMP = "20260721T003944-0500"
SYNC_MARKER = "synced_by_primary_csv_mutator_row019_023_runpod_wan_ti2v_asset_present"


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
    with E2E_TRACKER.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("Tracker_ID") == tracker_id:
                return row.get("Notes", "")
    raise RuntimeError(f"{tracker_id} missing from tracker CSV")


def already_synced(notes: str, tip: str) -> bool:
    return (
        STAMP in notes
        and "Wan TI2V ASSET_PRESENT 3/3" in notes
        and SCRIPT_LAND in notes
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
            row.update(updates[key])
    for key in updates:
        assert any(r[id_col] == key for r in rows), f"missing {key} in {path}"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_notes(tip: str, row: str) -> str:
    row_bit = (
        "immutable Row023 Wan reject reaffirmed until product visual QA; "
        if row == "023"
        else "video pipeline Wan dependency payloads now on pod; "
    )
    return (
        f"Class F cleared to ASSET_PRESENT only — Wan TI2V ASSET_PRESENT 3/3 "
        f"hash-verified on RunPod ({SCRIPT_LAND}/{FETCH_STARTED_COMMIT}/{tip}/{STAMP}): "
        "approved Fetch-RunPodWan22Ti2V5B.ps1 wget fetch completed on pod "
        "1q4ji0gg1fkhvt hostname 82caae576b8a; "
        f"{row_bit}"
        "paths "
        "/workspace/ComfyUI/models/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors|"
        "/workspace/ComfyUI/models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors|"
        "/workspace/ComfyUI/models/vae/wan2.2_vae.safetensors; "
        "sha256 bound "
        "456f901338bd9ead…|c3355d30191f1f06…|e40321bd36b97099…; "
        "proof_tier=RUNPOD_WAN_TI2V_ASSET_PRESENT_BOUNDED; "
        "row_complete=false; no COMPLETE; Row074 left alone; EC2 untouched; "
        f"local Comfy untouched. Evidence: {ASSET}; {FETCH_STARTED}; {PRIOR_BLOCKER}"
    )


def main() -> None:
    tip = git_short()
    packet = load_json(ASSET)
    assert packet.get("status") == "ASSET_PRESENT"
    assert packet.get("row_complete") is False
    assert packet.get("production_video_complete_claimed") is False
    assert packet.get("row074_touched") is False
    assert packet.get("fetch", {}).get("present_ratio") == "3/3"
    assert all(a.get("verified") is True for a in packet.get("assets", []))

    dump_json(ASSET_TRACKER, packet)
    dump_json(f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_ASSET_PRESENT_CURRENT.json", packet)
    dump_json(
        "Plan/Tracker/Evidence/Wave64/TRK-W64-019_023_RUNPOD_WAN_TI2V_ASSET_PRESENT_CURRENT.json",
        packet,
    )

    if already_synced(read_notes("TRK-W64-019"), tip) and already_synced(
        read_notes("TRK-W64-023"), tip
    ):
        print("tip", tip)
        print("no-op: TRK/ITEM-W64-019/023 ASSET_PRESENT Notes already synced")
        print("Row074 untouched")
        return

    notes019 = build_notes(tip, "019")
    notes023 = build_notes(tip, "023")
    evid = f"{ASSET}; {FETCH_STARTED}; {PRIOR_BLOCKER}"
    tracker_updates = {
        "TRK-W64-019": {"Notes": notes019, "Evidence_Path": evid},
        "TRK-W64-023": {"Notes": notes023, "Evidence_Path": evid},
    }
    item_updates = {
        "ITEM-W64-019": {"Notes": notes019},
        "ITEM-W64-023": {"Notes": notes023},
    }

    rewrite_csv(E2E_TRACKER, "Tracker_ID", tracker_updates)
    rewrite_csv(E2E_TRACKER_WAVES, "Tracker_ID", tracker_updates)
    rewrite_csv(E2E_ITEMS_WAVES, "Item_ID", item_updates)
    if E2E_ITEMS.exists():
        with E2E_ITEMS.open(encoding="utf-8", newline="") as handle:
            present = {row.get("Item_ID") for row in csv.DictReader(handle)}
        subset = {k: v for k, v in item_updates.items() if k in present}
        if subset:
            rewrite_csv(E2E_ITEMS, "Item_ID", subset)

    receipt = {
        "schema_version": "1.0",
        "mutator": SYNC_MARKER,
        "updated_utc": NOW,
        "tip": tip,
        "script_land": SCRIPT_LAND,
        "fetch_started_commit": FETCH_STARTED_COMMIT,
        "stamp": STAMP,
        "rows": ["TRK-W64-019", "TRK-W64-023", "ITEM-W64-019", "ITEM-W64-023"],
        "row074_touched": False,
        "complete_claimed": False,
        "asset_present_claimed": True,
        "evidence": ASSET,
    }
    dump_json(
        f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_ASSET_PRESENT_NOTES_SYNC_RECEIPT_{STAMP}.json",
        receipt,
    )
    dump_json(
        "Plan/Tracker/Evidence/Wave64/"
        f"TRK-W64-019_023_RUNPOD_WAN_TI2V_ASSET_PRESENT_NOTES_SYNC_RECEIPT_{STAMP}.json",
        receipt,
    )
    print("tip", tip)
    print("synced TRK/ITEM-W64-019/023 ASSET_PRESENT Notes")
    print("Row074 untouched; no COMPLETE")


if __name__ == "__main__":
    main()
