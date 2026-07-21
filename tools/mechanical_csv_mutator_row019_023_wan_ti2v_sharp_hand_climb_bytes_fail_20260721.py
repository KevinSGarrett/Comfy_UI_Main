#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 Wan TI2V sharp-hand climb FAIL.

I2V from c1_sharp_hand_start_still (human-pass still). Raw mp4 under 250KB
(238646). Human frame Read hands+skin PASS; Ollama VLM FAIL/near-static.
Not Proof_Landed (bytes gate miss). row_complete=false; no COMPLETE; Row074 alone.
"""
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
STAMP = "20260721T043700-0500"
EVIDENCE = f"{EVID}/TRK-W64-019_023_WAN_TI2V_SHARP_HAND_CLIMB_BYTES_FAIL_{STAMP}.json"
EVIDENCE_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    f"TRK-W64-019_023_WAN_TI2V_SHARP_HAND_CLIMB_BYTES_FAIL_{STAMP}.json"
)
CURRENT = f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
CURRENT_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
)
PULLBACK_DIR = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "runpod_wan_ti2v_sharp_hand_climb_20260721T092833Z"
)
PULLBACK_MP4 = (
    f"{PULLBACK_DIR}/"
    "w64_019_023_runpod_wan_ti2v_sharp_hand_climb_20260721T092833Z_00001_.mp4"
)
POD_MP4 = (
    "/workspace/comfy_output/video/"
    "w64_019_023_runpod_wan_ti2v_sharp_hand_climb_20260721T092833Z_00001_.mp4"
)
POLICY = (
    "Plan/07_IMPLEMENTATION/scripts/"
    "validate_wave64_wan_ti2v_class_e_runtime_proof_claim.py"
)
POLICY_RESULT = (
    f"{EVID}/TRK-W64-019_023_WAN_TI2V_SHARP_HAND_CLIMB_BYTES_FAIL_POLICY_{STAMP}.json"
)

PROMPT_ID = "12690f6a-06f4-43e8-b1b3-8708c9243547"
ARTIFACT_SHA = "f2569ee7a6f42c232d67d6760cb972f459ceb35b8679a405effdad3d7e7832f2"
ARTIFACT_BYTES = 238646
START_STILL = "c1_sharp_hand_start_still_20260721T092218Z_a1.png"
START_SHA = "ac43980940f3ae3187249f485bdd94ec69550a9cb96d4df3ebf163c8712cbcc4"
SYNC_MARKER = (
    "synced_by_primary_csv_mutator_row019_023_wan_ti2v_sharp_hand_climb_bytes_fail"
)

STATUS_019 = (
    "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_Sharp_Hand_Climb_Bytes_FAIL"
)
STATUS_023 = (
    "Blocked_Video_Frame_Repair_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_"
    "Sharp_Hand_Climb_Bytes_FAIL"
)
DECISION = "runpod_wan_ti2v_sharp_hand_climb_bytes_fail_reject"


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
        and "Sharp_Hand_Climb" in notes
        and "Bytes_FAIL" in notes
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


def sync_fixtures() -> None:
    src = ROOT / PULLBACK_DIR.replace("/", "\\")
    dst = ROOT / (
        "Plan/Instructions/QA/Evidence/Wave64/fixtures/row019_023/runtime/"
        "runpod_wan_ti2v_sharp_hand_climb_20260721T092833Z"
    ).replace("/", "\\")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "ffprobe.json",
        "vlm_review.json",
        "w64_019_023_sharp_hand_climb_20260721T092833Z_vlm.json",
        "w64_019_023_sharp_hand_climb_submit_20260721T092833Z.json",
    ):
        p = src / name
        if not p.exists() and name == "ffprobe.json":
            p = src / "frames" / "ffprobe.json"
        if p.exists():
            shutil.copy2(p, dst / name)
    frames_src = src / "frames"
    frames_dst = dst / "frames"
    if frames_src.is_dir():
        frames_dst.mkdir(parents=True, exist_ok=True)
        for frame in list(frames_src.glob("*.jpg")) + list(frames_src.glob("*.png")):
            shutil.copy2(frame, frames_dst / frame.name)


def build_packet(tip: str) -> dict:
    return {
        "schema_version": "1.0",
        "evidence_id": (
            f"TRK-W64-019_023_WAN_TI2V_SHARP_HAND_CLIMB_BYTES_FAIL_{STAMP}"
        ),
        "created_utc": "2026-07-21T09:37:00Z",
        "created_iso": "2026-07-21T04:37:00-05:00",
        "claim_tier": "class_e_attempt_fail",
        "status": "CLASS_E_PROOF_ATTEMPT_FAIL_REJECT_BYTES",
        "verdict": "WAN_TI2V_BOUNDED_SHARP_HAND_CLIMB_BYTES_FAIL_REJECT",
        "proof_tier": "RUNPOD_WAN_TI2V_BOUNDED_SHARP_HAND_CLIMB_BYTES_FAIL",
        "highest_proof_tier_achieved": (
            "RUNPOD_FLUX_PULID_SHARP_HAND_START_STILL_HUMAN_PASS"
        ),
        "mutation_this_landing": (
            "bounded_runpod_wan_ti2v_sharp_hand_climb_bytes_fail"
        ),
        "csv_sync": SYNC_MARKER,
        "item_ids": ["ITEM-W64-019", "ITEM-W64-023"],
        "tracker_ids": ["TRK-W64-019", "TRK-W64-023"],
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
            ],
        },
        "lane": {
            "lane_id": "wan_2_2_ti2v_5b_primary_lane",
            "repo_workflow": (
                "Workflows/video_generation/wan_2_2_ti2v_5b_primary_lane/workflow.api.json"
            ),
            "pod_workflow": (
                "/workspace/wave64/Workflows/video_generation/"
                "wan_2_2_ti2v_5b_primary_lane/workflow.api.json"
            ),
            "identity_safe_prompt": True,
            "source_image": START_STILL,
            "source_sha256": START_SHA,
            "i2v_from_start_image": True,
            "flux_loras_attached_to_wan": False,
        },
        "generation": {
            "prompt_id": PROMPT_ID,
            "completed": True,
            "status_str": "success",
            "width": 704,
            "height": 1280,
            "length": 81,
            "fps": 24,
            "steps": 38,
            "cfg": 6.0,
            "seed": 2272611,
            "artifact": {
                "bytes": ARTIFACT_BYTES,
                "filename": Path(PULLBACK_MP4).name,
                "pod_path": POD_MP4,
                "local_pullback": PULLBACK_MP4,
                "sha256": ARTIFACT_SHA,
                "ffprobe": {
                    "codec": "h264",
                    "width": 704,
                    "height": 1280,
                    "nb_frames": 81,
                    "duration_seconds": 3.375,
                    "bit_rate": 565679,
                },
            },
        },
        "bytes_gate": {
            "min_class_e_proof_bytes": 250000,
            "artifact_bytes": ARTIFACT_BYTES,
            "ok": False,
            "delta_under": 250000 - ARTIFACT_BYTES,
            "note": (
                "raw Comfy SaveVideo mp4 238646B < 250000; no bitrate-pad remux; "
                "bytes gate FAIL blocks Proof_Landed"
            ),
        },
        "reencode": {
            "performed": False,
            "note": "forbidden pad path; prior REENCODE250K landings rejected",
        },
        "technical_qa": {
            "performed": True,
            "technical_pass": False,
            "result": "fail_bytes_under_250kb",
            "note": (
                "ffprobe OK 704x1280/81f/h264/3.375s/bit_rate~566kbps but raw bytes "
                "238646 < 250000 Class E floor."
            ),
        },
        "human_frame_read": {
            "performed": True,
            "pass": True,
            "verdict": "pass",
            "scope": "hands_and_skin_full_frames_plus_crops",
            "frames_reviewed": [
                f"{PULLBACK_DIR}/frames/frame_01.png",
                f"{PULLBACK_DIR}/frames/frame_02.png",
                f"{PULLBACK_DIR}/frames/frame_03.png",
                f"{PULLBACK_DIR}/frames/frame_04.png",
                f"{PULLBACK_DIR}/frames/frame_05.png",
                f"{PULLBACK_DIR}/frames/hand_crop_center.png",
                f"{PULLBACK_DIR}/frames/hand_crop_left.png",
                f"{PULLBACK_DIR}/frames/hand_crop_right.png",
                f"{PULLBACK_DIR}/frames/skin_crop_face_shoulder.png",
            ],
            "fail_conditions_checked": [
                "mushy_fused_fingers",
                "plastic_skin",
            ],
            "fail_conditions_observed": [],
            "blunt_human_verdict": (
                "PASS hands+skin on full frames: palms-forward raised hands retain "
                "clearly separated fingers with knuckle/nail structure; torso/face skin "
                "shows pore grain (not mushy/fused, not plastic wax). Secondary: motion "
                "looks weak/near-static vs requested breathing/blink/weight-shift. "
                "Bytes gate FAIL (238646<250000) so not Proof_Landed."
            ),
        },
        "visual_qa": {
            "performed": True,
            "pass": False,
            "result": "fail_bytes_gate_despite_human_hands_skin_pass",
            "reviewer": "cursor_human_frame_read_hard_gate",
            "high_end_llm_in_loop": False,
            "ollama_vlm_in_loop": True,
            "blunt_human_verdict": (
                "Human hands+skin PASS; Ollama VLM FAIL (hands_ok=false, plastic_skin, "
                "near_static) secondary; raw bytes under 250KB. Do not Proof_Landed. "
                "Do not COMPLETE."
            ),
            "note": (
                "Proof_Landed requires human_frame_read=pass AND bytes OK; bytes miss."
            ),
        },
        "vlm_review": {
            "performed": True,
            "pass": False,
            "verdict": "FAIL",
            "model": "qwen2.5vl:7b",
            "overridden_by_human_hands_skin": True,
            "parsed": {
                "verdict": "FAIL",
                "hands_ok": False,
                "plastic_skin": True,
                "motion_plausible": False,
                "near_static": True,
                "identity_stable": True,
                "garment_ok": False,
                "defects": [
                    "Hands look mushy/fused/deformed",
                    "Skin looks plastic/waxy/oversmoothed",
                ],
                "summary": (
                    "The image exhibits issues with the hands and skin texture, "
                    "making it appear unnatural."
                ),
            },
            "local_path": f"{PULLBACK_DIR}/vlm_review.json",
        },
        "comfy_regen": {
            "attempted": True,
            "prompt_id": PROMPT_ID,
            "params": "704x1280/81f/38steps/cfg6.0/seed2272611",
            "waited_for_idle": True,
            "did_not_kill_foreign_jobs": True,
            "note": (
                f"Queue idle at submit; I2V from {START_STILL} "
                f"(sha={START_SHA[:16]}...); no Flux LoRAs on Wan; no Wan weight "
                "re-fetch; no 017 redo; Row074 untouched."
            ),
        },
        "wan_refetch": False,
        "row017_touched": False,
        "class_ladder": {
            "class_f": "ASSET_PRESENT retained",
            "class_e": (
                "sharp-hand climb completed but raw bytes <250KB — not Proof_Landed"
            ),
            "class_a": "product_visual_qa_open_human_claude_still_required",
            "not_claimed": [
                "row_complete",
                "COMPLETE",
                "class_e_runtime_proof_success",
                "Runtime_Proof_Landed",
                "Proof_Landed",
                "production_video_lane_certification",
            ],
        },
        "row_complete": False,
        "production_completion_allowed": False,
        "production_video_complete_claimed": False,
        "row074_touched": False,
        "ec2_touched": False,
        "local_comfy_touched": False,
        "policy_validator": POLICY,
        "summary": (
            f"Sharp-hand Wan climb prompt_id={PROMPT_ID} raw {ARTIFACT_BYTES}B "
            f"({Path(PULLBACK_MP4).name}) 704x1280/81f/38steps/cfg6.0 from "
            f"{START_STILL}. human_frame_read hands+skin PASS; VLM FAIL/near-static; "
            "bytes gate FAIL (238646<250000). Status FAIL/REJECT not Proof_Landed. "
            f"row_complete=false; no COMPLETE; Row074 untouched; EC2 untouched. tip={tip}."
        ),
        "next_fix_advice": (
            "1) Keep same sharp-hand start still; raise SaveVideo bitrate/quality or "
            "steps slightly so raw mp4 clears ≥250KB without pad remux. "
            "2) Strengthen motion (clearer blink + breathing) without crouch. "
            "3) Never attach Flux LoRAs to Wan; no Wan re-fetch; no 017 redo. "
            "4) Proof_Landed only if human_frame_read=pass AND bytes OK."
        ),
        "next_action": (
            "Keep row_complete=false; Status FAIL/open; no COMPLETE; Row074 alone; "
            "retry one Wan climb with higher raw bitrate targeting ≥250KB."
        ),
        "tip": tip,
    }


def build_notes(tip: str, row: str) -> str:
    row_bit = (
        "immutable Row023 product visual QA reject retained; "
        if row == "023"
        else "video pipeline sharp-hand climb bytes FAIL; "
    )
    return (
        f"Wan TI2V RunPod sharp-hand climb FAIL/REJECT bytes under 250KB "
        f"({tip}/{STAMP}): "
        f"prompt_id={PROMPT_ID}; "
        "artifact=w64_019_023_runpod_wan_ti2v_sharp_hand_climb_20260721T092833Z_00001_.mp4; "
        f"sha256={ARTIFACT_SHA}; bytes={ARTIFACT_BYTES} (<250000 FAIL raw, no pad); "
        "params=704x1280/81f/38steps/cfg6.0/seed2272611; "
        f"I2V start={START_STILL} sha={START_SHA}; "
        "Cursor human_frame_read hands+skin PASS; Ollama qwen2.5vl:7b VLM FAIL "
        "(near_static/plastic claims overridden for hands+skin by human Read); "
        "not Proof_Landed (bytes gate miss); "
        f"{row_bit}"
        "claim_tier=class_e_attempt_fail; "
        "proof_tier=RUNPOD_WAN_TI2V_BOUNDED_SHARP_HAND_CLIMB_BYTES_FAIL; "
        "next=one Wan climb with higher raw bitrate ≥250KB same start still; "
        "no Flux LoRAs on Wan; no Wan re-fetch; no 017 redo; "
        "row_complete=false; no COMPLETE; Row074 left alone; EC2 untouched; "
        f"local Comfy untouched. Evidence: {EVIDENCE}; {PULLBACK_MP4}; {POLICY}"
    )


def main() -> None:
    tip = git_short()
    mp4 = ROOT / PULLBACK_MP4.replace("/", "\\")
    if not mp4.exists():
        raise SystemExit(f"missing pullback mp4: {mp4}")
    actual = mp4.stat().st_size
    if actual != ARTIFACT_BYTES:
        raise SystemExit(f"byte mismatch: expected {ARTIFACT_BYTES} got {actual}")

    sync_fixtures()
    packet = build_packet(tip)
    dump_json(EVIDENCE, packet)
    dump_json(EVIDENCE_TRACKER, packet)
    dump_json(CURRENT, packet)
    dump_json(CURRENT_TRACKER, packet)

    policy = subprocess.run(
        [
            "python",
            str(ROOT / POLICY.replace("/", "\\")),
            "--packet",
            str(ROOT / EVIDENCE.replace("/", "\\")),
            "--out",
            str(ROOT / POLICY_RESULT.replace("/", "\\")),
            "--artifact-bytes",
            str(ARTIFACT_BYTES),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if policy.returncode != 0:
        raise SystemExit(
            f"policy validator failed rc={policy.returncode}\n"
            f"{policy.stdout}\n{policy.stderr}"
        )
    dump_json(
        "Plan/Tracker/Evidence/Wave64/"
        f"TRK-W64-019_023_WAN_TI2V_SHARP_HAND_CLIMB_BYTES_FAIL_POLICY_{STAMP}.json",
        json.loads((ROOT / POLICY_RESULT.replace("/", "\\")).read_text(encoding="utf-8")),
    )

    if already_synced(read_notes("TRK-W64-019"), tip) and already_synced(
        read_notes("TRK-W64-023"), tip
    ):
        print("tip", tip)
        print("no-op: Notes already synced")
        print("Row074 untouched")
        return

    notes019 = build_notes(tip, "019")
    notes023 = build_notes(tip, "023")
    evid = f"{EVIDENCE}; {PULLBACK_MP4}; {POLICY}; {POLICY_RESULT}"
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
        "prompt_id": PROMPT_ID,
        "artifact_sha256": ARTIFACT_SHA,
        "artifact_bytes": ARTIFACT_BYTES,
        "bytes_gate_ok": False,
        "vlm_verdict": "FAIL",
        "human_visual_verdict": "PASS_HANDS_SKIN",
        "human_frame_read": "pass",
        "proof_landed": False,
        "rows": ["TRK-W64-019", "TRK-W64-023", "ITEM-W64-019", "ITEM-W64-023"],
        "status_019": STATUS_019,
        "status_023": STATUS_023,
        "status_decision": DECISION,
        "claim_tier": "class_e_attempt_fail",
        "row074_touched": False,
        "complete_claimed": False,
        "row_complete": False,
        "evidence": EVIDENCE,
    }
    dump_json(
        f"{EVID}/TRK-W64-019_023_WAN_TI2V_SHARP_HAND_CLIMB_BYTES_FAIL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    dump_json(
        "Plan/Tracker/Evidence/Wave64/"
        f"TRK-W64-019_023_WAN_TI2V_SHARP_HAND_CLIMB_BYTES_FAIL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    print("tip", tip)
    print("synced TRK/ITEM-W64-019/023 Wan TI2V sharp-hand climb BYTES FAIL")
    print("bytes", ARTIFACT_BYTES, "gate FAIL; VLM FAIL; human hands+skin PASS")
    print("NOT Proof_Landed; no COMPLETE; Row074 untouched")


if __name__ == "__main__":
    main()
