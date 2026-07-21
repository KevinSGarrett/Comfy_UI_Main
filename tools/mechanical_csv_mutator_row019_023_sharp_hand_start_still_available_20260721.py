#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 sharp-hand start still AVAILABLE.

Flux+PuLID medium/hands-forward personal-calib still produced on RunPod and
human-gated PASS (separated fingers + pore microtexture). Stages sha256-bound
comfy_input still. Does NOT Wan I2V. Does NOT claim COMPLETE. row_complete=false.
"""
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
STAMP = "20260721T042230-0500"
EVIDENCE = f"{EVID}/TRK-W64-019_023_SHARP_HAND_START_STILL_AVAILABLE_{STAMP}.json"
EVIDENCE_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    f"TRK-W64-019_023_SHARP_HAND_START_STILL_AVAILABLE_{STAMP}.json"
)
CURRENT = f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
CURRENT_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
)
PULLBACK = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "sharp_hand_start_still_20260721T092218Z"
)
PRIOR_BLOCKER = (
    f"{EVID}/TRK-W64-019_023_NO_SHARP_HAND_START_STILL_20260721T035530-0500.json"
)

SYNC_MARKER = (
    "synced_by_primary_csv_mutator_row019_023_sharp_hand_start_still_available"
)

STAGED_NAME = "c1_sharp_hand_start_still_20260721T092218Z_a1.png"
STAGED_POD = f"/workspace/comfy_input/{STAGED_NAME}"
STAGED_SHA = "ac43980940f3ae3187249f485bdd94ec69550a9cb96d4df3ebf163c8712cbcc4"
PROMPT_ID = "2f011290-0463-4135-aa4a-da0ea0d2a8b8"
SEED = 17721261901

STATUS_019 = (
    "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_SHARP_HAND_START_STILL_AVAILABLE"
)
STATUS_023 = (
    "Blocked_Video_Frame_Repair_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_"
    "SHARP_HAND_START_STILL_AVAILABLE"
)
DECISION = "runpod_flux_pulid_sharp_hand_start_still_available_wan_climb_deferred"


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


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
        and "SHARP_HAND_START_STILL_AVAILABLE" in notes
        and tip in notes
        and "no COMPLETE" in notes
        and "Row074 left alone" in notes
        and STAGED_SHA[:16] in notes
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


def build_packet(tip: str) -> dict:
    return {
        "schema_version": "1.0",
        "evidence_id": f"TRK-W64-019_023_SHARP_HAND_START_STILL_AVAILABLE_{STAMP}",
        "created_utc": "2026-07-21T09:22:30Z",
        "created_iso": "2026-07-21T04:22:30-05:00",
        "claim_tier": "class_e_start_still_available_wan_climb_deferred",
        "status": "SHARP_HAND_START_STILL_AVAILABLE_WAN_CLIMB_DEFERRED",
        "verdict": "SHARP_HAND_START_STILL_AVAILABLE",
        "blocker_id_cleared": "NO_SHARP_HAND_START_STILL",
        "proof_tier": "RUNPOD_FLUX_PULID_SHARP_HAND_START_STILL_HUMAN_PASS",
        "highest_proof_tier_achieved": (
            "RUNPOD_FLUX_PULID_SHARP_HAND_START_STILL_HUMAN_PASS"
        ),
        "mutation_this_landing": "bounded_runpod_flux_pulid_sharp_hand_start_still",
        "csv_sync": SYNC_MARKER,
        "item_ids": ["ITEM-W64-019", "ITEM-W64-023"],
        "tracker_ids": ["TRK-W64-019", "TRK-W64-023"],
        "tip": tip,
        "binding": {
            "sole_runtime": "RunPod",
            "pod_id": "1q4ji0gg1fkhvt",
            "ssh": "root@195.26.233.100:52077",
            "forbidden": [
                "EC2",
                "local_Comfy",
                "Row074",
                "COMPLETE",
                "Wan_refetch",
                "017_redo",
                "Wan_I2V_this_landing",
            ],
        },
        "row_complete": False,
        "production_completion_allowed": False,
        "production_video_complete_claimed": False,
        "wan_refetch": False,
        "wan_i2v_submitted": False,
        "row017_touched": False,
        "row074_touched": False,
        "ec2_touched": False,
        "local_comfy_touched": False,
        "class_ladder": {
            "class_a": "product_visual_qa_open_human_claude_still_required",
            "class_e": (
                "start still NOW AVAILABLE; Wan Class E climb deferred to later "
                "landing (not this commit)"
            ),
            "class_f": "ASSET_PRESENT retained",
            "not_claimed": [
                "row_complete",
                "COMPLETE",
                "class_e_runtime_proof_success",
                "Runtime_Proof_Landed",
                "Proof_Landed",
                "production_video_lane_certification",
            ],
        },
        "generation": {
            "engine": "Flux+PuLID",
            "checkpoint": "flux1-dev-fp8.safetensors",
            "pulid_file": "pulid_flux_v0.9.1.safetensors",
            "pulid_weight": 1.0,
            "face_ref": (
                "/workspace/Characters/Scenes_xxx_001/01_CHARACTER_LOCKS/"
                "C1_female/refs/C1_USER_AUTHORITY_FACE_01.png"
            ),
            "face_sha256": (
                "eae4bc45cd029a812df8f8530d5c296eede73800b7ad9eeab35665468742602c"
            ),
            "composition": "medium_hands_forward_waist_up",
            "resolution": [832, 1152],
            "steps": 30,
            "seed": SEED,
            "prompt_id": PROMPT_ID,
            "attempt": 1,
            "prior_runtime_interrupt_discarded": (
                "ce7eb9fb-e446-4445-83f7-e9ed33d7cc7d global_/interrupt storm"
            ),
            "loras_flux_only": [
                "character1_flux_calibration/Latina_milf_flux.safetensors",
                "character1_flux_calibration/saggy_flux.safetensors",
                "character1_flux_calibration/FLUX_FD-LargeButt-SkinnyWaist-FP8.safetensors",
                "scenes_xxx_session/09_hands_feet/Realistic_Hands_Flux_v1.safetensors",
                "scenes_xxx_session/05_skin_hyperreal/Skin_Pore_Flux1D_v1.2.safetensors",
                "scenes_xxx_session/05_skin_hyperreal/Flux_Skin_Detailer.safetensors",
            ],
            "note": "Flux hand/skin LoRAs used for still only; NEVER wire into Wan.",
        },
        "staged_start_still": {
            "pod_path": STAGED_POD,
            "filename": STAGED_NAME,
            "sha256": STAGED_SHA,
            "bytes": 902892,
            "output_path": (
                "/workspace/comfy_output/Scenes_xxx_001/C1_sharp_hand_start/"
                "RUNPOD_C1_SHARP_HAND_START_a1_20260721T092218Z_00001_.png"
            ),
            "local_pullback": f"{PULLBACK}/{STAGED_NAME}",
            "hand_crops": [
                f"{PULLBACK}/hand_crop_left.png",
                f"{PULLBACK}/hand_crop_right.png",
            ],
        },
        "human_frame_read": {
            "performed": True,
            "scope": "full_still_plus_hand_crops",
            "pass": True,
            "blunt_human_verdict": (
                "PASS. Medium/hands-forward C1 still with both palms toward camera; "
                "all five digits per hand clearly separated with visible knuckle "
                "creases and nail beds; hand/palm skin shows pore grain and fine "
                "lines (not mushy/fused, not plastic). Suitable as Wan I2V start "
                "still. Wan climb NOT run this landing."
            ),
            "fail_conditions_checked": [
                "mushy_fused_fingers",
                "plastic_skin",
            ],
            "fail_conditions_observed": [],
        },
        "visual_qa": {
            "performed": True,
            "pass": True,
            "ollama_vlm_in_loop": False,
            "result": "sharp_hand_start_still_human_pass",
            "note": "Human Read gate on full still + hand crops; VLM not required.",
        },
        "next_action": (
            "Keep row_complete=false; Status FAIL/open with "
            "SHARP_HAND_START_STILL_AVAILABLE; no COMPLETE; Row074 alone; "
            "later one Wan I2V climb from staged still "
            f"{STAGED_NAME} (sha={STAGED_SHA[:16]}...) "
            "≤704x1280/81f/36-40 steps simple breathing/blink; "
            "human_frame_read required; never attach Flux hand/skin LoRAs to Wan."
        ),
        "next_fix_advice": (
            "1) Use staged comfy_input still as Wan I2V start. "
            "2) Do not re-fetch Wan weights. "
            "3) Never attach Flux hand/skin LoRAs to Wan. "
            "4) Do not redo consumed 017 lanes. "
            "5) Leave Row074 alone; no COMPLETE until Class E human pass."
        ),
        "prior_blocker": PRIOR_BLOCKER,
        "summary": (
            f"SHARP_HAND_START_STILL_AVAILABLE tip={tip}. Flux+PuLID "
            f"prompt_id={PROMPT_ID} seed={SEED} staged {STAGED_POD} "
            f"sha256={STAGED_SHA}. Human gate PASS (separated fingers + pore "
            "microtexture). No Wan I2V this landing; Class E climb may resume "
            "later. row_complete=false; no COMPLETE; Row074 untouched; EC2 "
            "untouched; no 017 redo; no Wan re-fetch."
        ),
    }


def build_notes(tip: str, row: str) -> str:
    row_bit = (
        "immutable Row023 product visual QA reject retained until Wan climb; "
        if row == "023"
        else "video pipeline unblocked for later Wan climb from staged still; "
    )
    return (
        f"Wan TI2V RunPod SHARP_HAND_START_STILL_AVAILABLE ({tip}/{STAMP}): "
        f"Flux+PuLID medium/hands-forward personal-calib still "
        f"prompt_id={PROMPT_ID} seed={SEED}; staged {STAGED_POD} "
        f"sha256={STAGED_SHA}; human_gate PASS separated fingers + pore "
        "microtexture (hand crops); NO_SHARP_HAND_START_STILL cleared; "
        "no Wan I2V this landing (climb deferred); no Wan re-fetch; no 017 redo; "
        "not Proof_Landed; not COMPLETE; "
        f"{row_bit}"
        f"claim_tier=class_e_start_still_available_wan_climb_deferred; "
        f"proof_tier=RUNPOD_FLUX_PULID_SHARP_HAND_START_STILL_HUMAN_PASS; "
        "Status stays FAIL/open; row_complete=false; no COMPLETE; "
        "Row074 left alone; EC2 untouched; local Comfy untouched. "
        f"Evidence: {EVIDENCE}; {PULLBACK}; prior_blocker={PRIOR_BLOCKER}"
    )


def main() -> None:
    tip = git_short()
    pull = ROOT / PULLBACK.replace("/", "\\")
    still = pull / STAGED_NAME
    if not still.is_file():
        raise SystemExit(f"missing pullback still: {still}")
    import hashlib

    h = hashlib.sha256(still.read_bytes()).hexdigest()
    if h != STAGED_SHA:
        raise SystemExit(f"sha mismatch got={h} expected={STAGED_SHA}")

    packet = build_packet(tip)
    dump_json(EVIDENCE, packet)
    dump_json(EVIDENCE_TRACKER, packet)
    dump_json(CURRENT, packet)
    dump_json(CURRENT_TRACKER, packet)

    if already_synced(read_notes("TRK-W64-019"), tip) and already_synced(
        read_notes("TRK-W64-023"), tip
    ):
        print("tip", tip)
        print("no-op: Notes already synced")
        print("Row074 untouched")
        return

    notes019 = build_notes(tip, "019")
    notes023 = build_notes(tip, "023")
    evid = f"{EVIDENCE}; {PULLBACK}; {PRIOR_BLOCKER}"
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
        "stamp": STAMP,
        "verdict": "SHARP_HAND_START_STILL_AVAILABLE",
        "blocker_id_cleared": "NO_SHARP_HAND_START_STILL",
        "prompt_id": PROMPT_ID,
        "staged_pod": STAGED_POD,
        "staged_sha256": STAGED_SHA,
        "wan_submit": False,
        "proof_landed": False,
        "rows": ["TRK-W64-019", "TRK-W64-023", "ITEM-W64-019", "ITEM-W64-023"],
        "status_019": STATUS_019,
        "status_023": STATUS_023,
        "status_decision": DECISION,
        "claim_tier": "class_e_start_still_available_wan_climb_deferred",
        "row074_touched": False,
        "complete_claimed": False,
        "row_complete": False,
        "evidence": EVIDENCE,
    }
    dump_json(
        f"{EVID}/TRK-W64-019_023_SHARP_HAND_START_STILL_AVAILABLE_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    dump_json(
        "Plan/Tracker/Evidence/Wave64/"
        f"TRK-W64-019_023_SHARP_HAND_START_STILL_AVAILABLE_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    print("tip", tip)
    print("synced TRK/ITEM-W64-019/023 SHARP_HAND_START_STILL_AVAILABLE")
    print("staged", STAGED_POD, STAGED_SHA)
    print("Status FAIL/open; NOT Proof_Landed; no COMPLETE; Row074 untouched")


if __name__ == "__main__":
    main()
