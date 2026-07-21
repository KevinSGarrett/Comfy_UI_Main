#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 NO_SHARP_HAND_START_STILL blocker.

After hands/skin climb FAIL (5d9adb26), search RunPod C1 USER_AUTHORITY +
comfy_input for an I2V start still with already-sharp separated fingers and
pore texture. None qualify. Prefer stop-with-blocker over another soft-start
Wan FAIL. No Comfy submit. Status stays FAIL/open; row_complete=false.
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
STAMP = "20260721T035530-0500"
EVIDENCE = f"{EVID}/TRK-W64-019_023_NO_SHARP_HAND_START_STILL_{STAMP}.json"
EVIDENCE_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    f"TRK-W64-019_023_NO_SHARP_HAND_START_STILL_{STAMP}.json"
)
CURRENT = f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
CURRENT_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
)
SCAN_DIR = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "sharp_hand_start_still_scan_20260721"
)
PRIOR_FAIL = (
    f"{EVID}/TRK-W64-019_023_WAN_TI2V_HANDS_SKIN_HUMAN_VISUAL_FAIL_"
    "20260721T035115-0500.json"
)

SYNC_MARKER = (
    "synced_by_primary_csv_mutator_row019_023_wan_ti2v_no_sharp_hand_start_still"
)
BLOCKER_ID = "NO_SHARP_HAND_START_STILL"

STATUS_019 = (
    "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_NO_SHARP_HAND_START_STILL"
)
STATUS_023 = (
    "Blocked_Video_Frame_Repair_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_"
    "NO_SHARP_HAND_START_STILL"
)
DECISION = "runpod_wan_ti2v_no_sharp_hand_start_still_blocker"

PRIOR_PROMPT = "5d9adb26-ce70-46a4-8824-1ba048982cc2"


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
        and BLOCKER_ID in notes
        and tip in notes
        and "no COMPLETE" in notes
        and "Row074 left alone" in notes
        and "no Wan submit" in notes
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
        "evidence_id": f"TRK-W64-019_023_NO_SHARP_HAND_START_STILL_{STAMP}",
        "created_utc": "2026-07-21T08:55:30Z",
        "created_iso": "2026-07-21T03:55:30-05:00",
        "claim_tier": "class_e_start_still_blocker",
        "status": "CLASS_E_PROOF_ATTEMPT_FAIL_OPEN_NO_SHARP_HAND_START_STILL",
        "verdict": "NO_SHARP_HAND_START_STILL",
        "blocker_id": BLOCKER_ID,
        "proof_tier": "RUNPOD_WAN_TI2V_BOUNDED_NO_SHARP_HAND_START_STILL",
        "highest_proof_tier_achieved": (
            "RUNPOD_WAN_TI2V_BOUNDED_HANDS_SKIN_HUMAN_VISUAL_FAIL"
        ),
        "mutation_this_landing": "bounded_runpod_wan_ti2v_no_sharp_hand_start_still",
        "csv_sync": SYNC_MARKER,
        "item_ids": ["ITEM-W64-019", "ITEM-W64-023"],
        "tracker_ids": ["TRK-W64-019", "TRK-W64-023"],
        "binding": {
            "sole_runtime": "RunPod",
            "pod_id": "1q4ji0gg1fkhvt",
            "ssh": "root@195.26.233.100:52077",
            "forbidden": ["EC2", "local_Comfy", "Row074", "COMPLETE", "Wan_refetch", "017_redo"],
        },
        "prior_fail": {
            "prompt_id": PRIOR_PROMPT,
            "evidence": PRIOR_FAIL,
            "defects": [
                "mushy_fused_hands",
                "plastic_skin",
                "soft_start_still_tips",
            ],
            "commit": "37f03e3a",
        },
        "comfy_regen": {
            "attempted": False,
            "reason": BLOCKER_ID,
            "did_not_kill_foreign_jobs": True,
            "did_not_refetch_wan": True,
            "did_not_touch_row017": True,
            "did_not_touch_row074": True,
            "queue_at_scan": "idle",
            "note": (
                "Prefer stop-with-blocker over another soft-start FAIL. "
                "No I2V Wan submit this landing."
            ),
        },
        "start_still_search": {
            "performed": True,
            "runtime": "runpod",
            "paths_env_sourced": True,
            "prefer": (
                "C1 USER_AUTHORITY face/front/body showing hands clearly with "
                "already-sharp separated fingers + pore texture; medium/hands-forward"
            ),
            "local_pullback_scan": SCAN_DIR,
            "candidates_reviewed": [
                {
                    "path": (
                        "/workspace/comfy_input/C1_USER_AUTHORITY_FACE_01.png"
                    ),
                    "role": "C1_USER_AUTHORITY_face",
                    "hands": "absent_face_crop",
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/comfy_input/C1_USER_AUTHORITY_FACE_02.png"
                    ),
                    "role": "C1_USER_AUTHORITY_face",
                    "hands": "absent_face_crop",
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/comfy_input/C1_USER_AUTHORITY_FACE_03.png"
                    ),
                    "role": "C1_USER_AUTHORITY_face",
                    "hands": "absent_shoulders_up",
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/comfy_input/C1_USER_AUTHORITY_FACE_04.png"
                    ),
                    "role": "C1_USER_AUTHORITY_face",
                    "hands": "absent_face_crop",
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/comfy_input/C1_USER_AUTHORITY_FRONT_20260719.png"
                    ),
                    "role": "C1_USER_AUTHORITY_front_body",
                    "hands": (
                        "visible_but_left_hip_hand_soft_mushy; "
                        "no_sharp_pore_microtexture_on_hands"
                    ),
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/comfy_input/C1_USER_AUTHORITY_SIDE_20260719.png"
                    ),
                    "role": "C1_USER_AUTHORITY_side_body",
                    "hands": (
                        "separated_fingers_better_but_soft_studio_skin; "
                        "pore_microtexture_not_sharp_enough_for_I2V_start"
                    ),
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/comfy_input/wan22_ti2v_fullbody_seed711670301.png"
                    ),
                    "role": "prior_fail_athletic_start",
                    "hands": "soft_tips_already_rejected_by_prior_FAIL",
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/Characters/Scenes_xxx_001/01_CHARACTER_LOCKS/"
                        "C1_female/refs/LOCK_FRONT_passA.png"
                    ),
                    "role": "promoted_front_lock",
                    "hands": "separated_left_fingers_but_no_hand_pore_texture",
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/Characters/Scenes_xxx_001/01_CHARACTER_LOCKS/"
                        "C1_female/refs/C1_METHOD_V177_FRONT_ECBD18E86514.png"
                    ),
                    "role": "method_front",
                    "hands": "semi_fists_soft_mushy_no_separated_sharp_fingers",
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/Characters/Scenes_xxx_001/01_CHARACTER_LOCKS/"
                        "C1_female/refs/stack_proof_C1_SOLO_FRONT_00001_.png"
                    ),
                    "role": "stack_proof_front",
                    "hands": "soft_blurry_hands",
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/Characters/Scenes_xxx_001/01_CHARACTER_LOCKS/"
                        "C1_female/refs/reference_front_body.jpg"
                    ),
                    "role": "reference_front_body",
                    "hands": "separated_left_but_plastic_smooth_hands",
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/comfy_input/"
                        "character1_hand_v79_user_reference.png"
                    ),
                    "role": "hand_lane_full_ref",
                    "hands": "fingertips_soft_plastic_vs_body_texture",
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/comfy_input/"
                        "character1_hand_v67_user_reference_full.png"
                    ),
                    "role": "hand_lane_full_ref",
                    "hands": "fingertips_soft_not_razor_sharp",
                    "viable_i2v_start": False,
                },
                {
                    "path": (
                        "/workspace/comfy_input/"
                        "character1_user_hand_topology_reference_crop_v12.png"
                    ),
                    "role": "hand_topology_crop_only",
                    "hands": (
                        "crop_has_separated_fingers_and_pores_but_512x512_crop_"
                        "not_a_medium_or_full_I2V_start_still"
                    ),
                    "viable_i2v_start": False,
                    "note": "topology crop cannot substitute for framed start still",
                },
                {
                    "path": (
                        "/workspace/comfy_input/"
                        "character1_v231_front_flux_source_for_detail.png"
                    ),
                    "role": "face_detail_source",
                    "hands": "absent_headshot",
                    "viable_i2v_start": False,
                },
            ],
            "viable_count": 0,
            "decision": "do_not_generate",
        },
        "human_frame_read": {
            "performed": True,
            "scope": "start_still_candidates_only_no_video_frames",
            "pass": False,
            "verdict": "blocker",
            "blunt_human_verdict": (
                "No C1 USER_AUTHORITY face/front/body still shows already-sharp "
                "separated fingers with pore microtexture suitable as Wan I2V "
                "start. Face refs have no hands. FRONT left hip hand soft/mushy. "
                "SIDE better separation but soft studio skin. Prior athletic "
                "still already rejected. Hand topology crop is not a start still. "
                "Stop; do not Wan climb."
            ),
        },
        "visual_qa": {
            "performed": True,
            "pass": False,
            "result": "blocker_no_sharp_hand_start_still",
            "ollama_vlm_in_loop": False,
            "note": "No video generated; VLM deferred. human start-still gate failed.",
        },
        "vlm_review": {
            "performed": False,
            "reason": "no_video_artifact_no_submit",
        },
        "bytes_gate": {
            "ok": False,
            "note": "N/A — no mp4 generated this landing",
        },
        "class_ladder": {
            "class_a": "product_visual_qa_open_human_claude_still_required",
            "class_e": (
                "prior hands/skin climb FAIL retained; new climb blocked by "
                "NO_SHARP_HAND_START_STILL"
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
        "detail_lora_note": {
            "flux_hand_skin_loras_present_on_pod": True,
            "wan_compatible_detail_lora_found": False,
            "note": (
                "Do not wire Flux hand/skin LoRAs into Wan. Need a sharp-hand "
                "start still (medium/hands-forward) or Wan-native detail LoRA."
            ),
        },
        "row_complete": False,
        "production_completion_allowed": False,
        "production_video_complete_claimed": False,
        "row074_touched": False,
        "ec2_touched": False,
        "local_comfy_touched": False,
        "wan_refetch": False,
        "row017_touched": False,
        "summary": (
            f"NO_SHARP_HAND_START_STILL after prior FAIL prompt_id={PRIOR_PROMPT}. "
            "Scanned RunPod C1 USER_AUTHORITY face/front/side + comfy_input hand/"
            "front plates; viable_count=0 for already-sharp separated fingers + "
            "pore texture I2V start. No Wan submit. Status FAIL/open not "
            f"Proof_Landed. row_complete=false; no COMPLETE; Row074 untouched; "
            f"EC2 untouched; no 017 redo; no Wan re-fetch. tip={tip}."
        ),
        "next_fix_advice": (
            "1) Produce or promote a medium/hands-forward C1 still with "
            "already-sharp separated fingers and visible pore microtexture "
            "(do not invent identity). "
            "2) Do not re-use wan22_ti2v_fullbody_seed711670301.png or soft "
            "USER_AUTHORITY FRONT. "
            "3) Never attach Flux hand/skin LoRAs to Wan. "
            "4) Only then one I2V Wan climb ≥704x1280/81f/36-40 steps simple "
            "breathing/blink; human_frame_read required."
        ),
        "next_action": (
            "Keep row_complete=false; Status FAIL open with "
            f"{BLOCKER_ID}; no COMPLETE; Row074 alone; acquire sharp-hand "
            "start still before any Wan TI2V attempt."
        ),
        "tip": tip,
    }


def build_notes(tip: str, row: str) -> str:
    row_bit = (
        "immutable Row023 product visual QA reject retained; "
        if row == "023"
        else "video pipeline blocked pending sharp-hand start still; "
    )
    return (
        f"Wan TI2V RunPod {BLOCKER_ID} ({tip}/{STAMP}): "
        f"prior_fail_prompt_id={PRIOR_PROMPT}; "
        "scanned C1_USER_AUTHORITY face/front/side + comfy_input hand/front "
        "plates on pod 1q4ji0gg1fkhvt; viable_sharp_hand_start_still_count=0; "
        "FACE=no hands; FRONT=soft/mushy hip hand; SIDE=soft pores; "
        "prior athletic still soft tips retained reject; hand topology crop "
        "not a framed I2V start; prefer stop-with-blocker; no Wan submit; "
        "no Wan re-fetch; no 017 redo; not Proof_Landed; "
        f"{row_bit}"
        f"claim_tier=class_e_start_still_blocker; "
        f"proof_tier=RUNPOD_WAN_TI2V_BOUNDED_NO_SHARP_HAND_START_STILL; "
        "Status stays FAIL/open; row_complete=false; no COMPLETE; "
        "Row074 left alone; EC2 untouched; local Comfy untouched. "
        f"Evidence: {EVIDENCE}; {SCAN_DIR}; {PRIOR_FAIL}"
    )


def main() -> None:
    tip = git_short()
    scan = ROOT / SCAN_DIR.replace("/", "\\")
    if not scan.is_dir():
        raise SystemExit(f"missing scan pullback dir: {scan}")
    required = [
        "C1_USER_AUTHORITY_FRONT_20260719.png",
        "C1_USER_AUTHORITY_SIDE_20260719.png",
        "C1_USER_AUTHORITY_FACE_03.png",
        "wan22_ti2v_fullbody_seed711670301.png",
    ]
    for name in required:
        if not (scan / name).exists():
            raise SystemExit(f"missing scan file: {scan / name}")

    packet = build_packet(tip)
    dump_json(EVIDENCE, packet)
    dump_json(EVIDENCE_TRACKER, packet)
    dump_json(CURRENT, packet)
    dump_json(CURRENT_TRACKER, packet)
    dump_json(f"{SCAN_DIR}/scan_inventory.json", packet["start_still_search"])

    if already_synced(read_notes("TRK-W64-019"), tip) and already_synced(
        read_notes("TRK-W64-023"), tip
    ):
        print("tip", tip)
        print("no-op: Notes already synced")
        print("Row074 untouched")
        return

    notes019 = build_notes(tip, "019")
    notes023 = build_notes(tip, "023")
    evid = f"{EVIDENCE}; {SCAN_DIR}; {PRIOR_FAIL}"
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
        "blocker_id": BLOCKER_ID,
        "prior_prompt_id": PRIOR_PROMPT,
        "wan_submit": False,
        "viable_sharp_hand_start_still_count": 0,
        "proof_landed": False,
        "rows": ["TRK-W64-019", "TRK-W64-023", "ITEM-W64-019", "ITEM-W64-023"],
        "status_019": STATUS_019,
        "status_023": STATUS_023,
        "status_decision": DECISION,
        "claim_tier": "class_e_start_still_blocker",
        "row074_touched": False,
        "complete_claimed": False,
        "row_complete": False,
        "evidence": EVIDENCE,
    }
    dump_json(
        f"{EVID}/TRK-W64-019_023_NO_SHARP_HAND_START_STILL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    dump_json(
        "Plan/Tracker/Evidence/Wave64/"
        f"TRK-W64-019_023_NO_SHARP_HAND_START_STILL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    print("tip", tip)
    print("synced TRK/ITEM-W64-019/023", BLOCKER_ID)
    print("viable_sharp_hand_start_still_count=0; no Wan submit")
    print("Status FAIL/open; NOT Proof_Landed; no COMPLETE; Row074 untouched")


if __name__ == "__main__":
    main()
