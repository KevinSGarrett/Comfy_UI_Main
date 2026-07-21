#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 Wan TI2V Class E motion regen HUMAN VISUAL FAIL.

Raw mp4 cleared ≥250KB (no bitrate pad) and VLM PASS, but Cursor human frame Read
REJECTS (mushy hands / plastic skin). Motion improved vs prior near-static, but still
not Proof_Landed. Policy now requires human_frame_read=pass for Proof_Landed.
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
STAMP = "20260721T034100-0500"
EVIDENCE = f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_E_MOTION_REGEN_HUMAN_VISUAL_FAIL_{STAMP}.json"
EVIDENCE_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    f"TRK-W64-019_023_WAN_TI2V_CLASS_E_MOTION_REGEN_HUMAN_VISUAL_FAIL_{STAMP}.json"
)
CURRENT = f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
CURRENT_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
)
PULLBACK_DIR = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "runpod_wan_ti2v_class_e_motion_20260721T083156Z"
)
PULLBACK_MP4 = (
    f"{PULLBACK_DIR}/"
    "w64_019_023_runpod_wan_ti2v_class_e_motion_20260721T083156Z_00001_.mp4"
)
POD_MP4 = (
    "/workspace/comfy_output/video/"
    "w64_019_023_runpod_wan_ti2v_class_e_motion_20260721T083156Z_00001_.mp4"
)
POLICY = (
    "Plan/07_IMPLEMENTATION/scripts/"
    "validate_wave64_wan_ti2v_class_e_runtime_proof_claim.py"
)
POLICY_RESULT = (
    f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_E_MOTION_REGEN_HUMAN_VISUAL_FAIL_POLICY_{STAMP}.json"
)

PROMPT_ID = "bc7623d0-f4bd-455b-9e19-b99e23455af6"
ARTIFACT_SHA = "52af821b60397f497df3080397129ebdf0d7d5676abd1b94437af0b0cfc615b1"
ARTIFACT_BYTES = 351164
SYNC_MARKER = (
    "synced_by_primary_csv_mutator_row019_023_wan_ti2v_class_e_motion_regen_human_visual_fail"
)

STATUS_019 = (
    "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_Class_E_Motion_Regen_Human_Visual_FAIL"
)
STATUS_023 = (
    "Blocked_Video_Frame_Repair_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_"
    "Class_E_Motion_Regen_Human_Visual_FAIL"
)
DECISION = "runpod_wan_ti2v_class_e_motion_regen_human_visual_fail_reject"

BLUNT_DEFECTS = [
    "mushy_blurred_hands_fingers_poorly_separated",
    "plastic_waxy_oversmoothed_skin_low_pore_detail",
    "motion_improved_but_still_mid_tier_ai_look",
    "stylized_pelvis_v_seam_still_present",
    "vlm_pass_insufficient_without_human_frame_read_pass",
]


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
        and "Motion_Regen" in notes
        and "Human_Visual_FAIL" in notes
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
        "runpod_wan_ti2v_class_e_motion_20260721T083156Z"
    ).replace("/", "\\")
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("ffprobe.json", "vlm_review.json"):
        p = src / name
        if p.exists():
            shutil.copy2(p, dst / name)
    frames_src = src / "frames"
    frames_dst = dst / "frames"
    if frames_src.is_dir():
        frames_dst.mkdir(parents=True, exist_ok=True)
        for frame in list(frames_src.glob("*.jpg")) + list(frames_src.glob("*.png")):
            shutil.copy2(frame, frames_dst / frame.name)
    mp4 = src / Path(PULLBACK_MP4).name
    if mp4.exists():
        shutil.copy2(mp4, dst / mp4.name)


def build_packet(tip: str) -> dict:
    return {
        "schema_version": "1.0",
        "evidence_id": (
            f"TRK-W64-019_023_WAN_TI2V_CLASS_E_MOTION_REGEN_HUMAN_VISUAL_FAIL_{STAMP}"
        ),
        "created_utc": "2026-07-21T08:41:00Z",
        "created_iso": "2026-07-21T03:41:00-05:00",
        "claim_tier": "class_e_attempt_fail",
        "status": "CLASS_E_PROOF_ATTEMPT_FAIL_REJECT_HUMAN_VISUAL",
        "verdict": "WAN_TI2V_BOUNDED_CLASS_E_MOTION_REGEN_HUMAN_VISUAL_FAIL_REJECT",
        "proof_tier": "RUNPOD_WAN_TI2V_BOUNDED_CLASS_E_MOTION_REGEN_HUMAN_VISUAL_FAIL",
        "highest_proof_tier_achieved": (
            "RUNPOD_WAN_TI2V_BOUNDED_CLASS_E_MOTION_REGEN_HUMAN_VISUAL_FAIL"
        ),
        "mutation_this_landing": (
            "bounded_runpod_wan_ti2v_class_e_motion_regen_human_visual_fail"
        ),
        "csv_sync": SYNC_MARKER,
        "item_ids": ["ITEM-W64-019", "ITEM-W64-023"],
        "tracker_ids": ["TRK-W64-019", "TRK-W64-023"],
        "binding": {
            "sole_runtime": "RunPod",
            "pod_id": "1q4ji0gg1fkhvt",
            "ssh": "root@195.26.233.100:52077",
            "forbidden": ["EC2", "local_Comfy", "Row074", "COMPLETE"],
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
            "source_image": "wan22_ti2v_fullbody_seed711670301.png",
            "motion_prompt_strengthened": True,
        },
        "generation": {
            "prompt_id": PROMPT_ID,
            "completed": True,
            "status_str": "success",
            "width": 704,
            "height": 1280,
            "length": 81,
            "fps": 24,
            "steps": 40,
            "cfg": 6.0,
            "seed": 2272407,
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
                    "bit_rate": 821582,
                },
            },
        },
        "bytes_gate": {
            "min_class_e_proof_bytes": 250000,
            "artifact_bytes": ARTIFACT_BYTES,
            "ok": True,
            "note": (
                "raw Comfy SaveVideo mp4 cleared ≥250KB without bitrate-pad remux"
            ),
        },
        "reencode": {
            "performed": False,
            "note": "not needed; raw artifact already 351164B",
        },
        "technical_qa": {
            "performed": True,
            "technical_pass": True,
            "result": "pass_bounded_video_technical_qa",
            "note": (
                "ffprobe OK 704x1280/81f/h264/3.375s/bit_rate~822kbps. Technical decode "
                "and ≥250KB do NOT authorize Proof_Landed when human frames look bad."
            ),
        },
        "human_frame_read": {
            "performed": True,
            "pass": False,
            "verdict": "fail",
            "frames_reviewed": [
                f"{PULLBACK_DIR}/frames/frame_01.png",
                f"{PULLBACK_DIR}/frames/frame_02.png",
                f"{PULLBACK_DIR}/frames/frame_03.png",
                f"{PULLBACK_DIR}/frames/frame_04.png",
                f"{PULLBACK_DIR}/frames/frame_05.png",
            ],
            "blunt_defects": BLUNT_DEFECTS,
            "blunt_human_verdict": (
                "Motion is better than the prior near-static clip (standing → closed-eye "
                "blink cue → athletic crouch/weight shift across 5 frames), and raw bytes "
                "clear 250KB. Still FAIL: mushy/poorly separated fingers, plastic "
                "oversmoothed skin, mid-tier AI look. Do not Proof_Landed. Do not COMPLETE."
            ),
        },
        "visual_qa": {
            "performed": True,
            "pass": False,
            "result": "fail_human_frame_review_reject_despite_vlm_pass",
            "reviewer": "cursor_human_frame_read_overrides_ollama_vlm",
            "blunt_defects": BLUNT_DEFECTS,
            "high_end_llm_in_loop": False,
            "ollama_vlm_in_loop": True,
            "global_review_stamp": None,
            "global_review_note": (
                "Row017 GLOBAL_REVIEW schema is localized-image producer specific; "
                "not applied to this TI2V motion clip."
            ),
            "blunt_human_verdict": (
                "Motion improved vs prior near-static, raw ≥250KB, VLM PASS — but human "
                "Cursor frame Read still rejects mushy hands + plastic skin. "
                "Do not Proof_Landed. Do not COMPLETE."
            ),
            "note": (
                "VLM PASS ignored for Proof_Landed because human_frame_read=fail. "
                "Claim policy now requires human_frame_read pass for Proof_Landed."
            ),
        },
        "vlm_review": {
            "performed": True,
            "pass": True,
            "verdict": "PASS",
            "model": "qwen2.5vl:7b",
            "overridden_by_human": True,
            "override_reason": (
                "human_frame_read hard gate: mushy hands / plastic skin remain; "
                "VLM alone is not Proof_Landed"
            ),
            "parsed": {
                "verdict": "PASS",
                "identity_stable": True,
                "motion_plausible": True,
                "hands_ok": True,
                "garment_ok": True,
                "plastic_skin": False,
                "near_static": False,
                "defects": [],
                "summary": (
                    "The video features a person in athletic attire performing fluid, "
                    "dynamic movements against a neutral background."
                ),
            },
            "local_path": f"{PULLBACK_DIR}/vlm_review.json",
        },
        "comfy_regen": {
            "attempted": True,
            "prompt_id": PROMPT_ID,
            "params": "704x1280/81f/40steps/cfg6.0/seed2272407",
            "waited_for_idle": True,
            "did_not_kill_foreign_jobs": True,
            "note": (
                "Waited through foreign gold-tournament GPU ownership and Comfy "
                "respawn block; restarted Comfy only when down; submitted stronger "
                "motion prompt on wan_2_2_ti2v_5b_primary_lane."
            ),
        },
        "high_end_note": (
            "Ollama qwen2.5vl:7b is necessary but not sufficient. Proof_Landed now "
            "requires human_frame_read=pass (policy tightened). Product visual accept "
            "still needs human/Claude; no COMPLETE."
        ),
        "class_ladder": {
            "class_f": "ASSET_PRESENT retained",
            "class_e": (
                "motion regen raw ≥250KB + VLM PASS, but HUMAN visual FAIL/REJECT "
                "— not Proof_Landed"
            ),
            "class_a": "product_visual_qa_open_human_claude_still_required",
            "not_claimed": [
                "row_complete",
                "COMPLETE",
                "class_e_runtime_proof_success",
                "Runtime_Proof_Landed",
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
            f"Motion regen prompt_id={PROMPT_ID} raw {ARTIFACT_BYTES}B "
            f"({Path(PULLBACK_MP4).name}) 704x1280/81f/40steps/cfg6.0. Bytes gate OK "
            "without reencode; Ollama qwen2.5vl:7b PASS; HUMAN Cursor frame Read FAIL "
            "(mushy hands/plastic skin; motion improved). Status FAIL/REJECT not "
            f"Proof_Landed. row_complete=false; no COMPLETE; Row074 untouched; "
            f"EC2 untouched. tip={tip}."
        ),
        "next_fix_advice": (
            "Next climb needs sharper hand anatomy + natural skin microtexture while "
            "keeping clear motion; keep human_frame_read hard gate. Do not claim "
            "Proof_Landed on VLM-only PASS."
        ),
        "next_action": (
            "Keep row_complete=false; no COMPLETE; Row074 alone; iterate visual quality."
        ),
    }


def build_notes(tip: str, row: str) -> str:
    row_bit = (
        "immutable Row023 product visual QA reject retained; "
        if row == "023"
        else "video pipeline Class E motion regen human visual FAIL; "
    )
    return (
        f"Wan TI2V RunPod Class E motion regen HUMAN VISUAL FAIL/REJECT "
        f"({tip}/{STAMP}): "
        f"prompt_id={PROMPT_ID}; "
        "artifact=w64_019_023_runpod_wan_ti2v_class_e_motion_20260721T083156Z_00001_.mp4; "
        f"sha256={ARTIFACT_SHA}; bytes={ARTIFACT_BYTES} (>=250000 OK raw, no pad); "
        "params=704x1280/81f/40steps/cfg6.0/seed2272407; "
        "Ollama qwen2.5vl:7b VLM PASS OVERRIDDEN by Cursor human_frame_read FAIL "
        "(mushy hands, plastic/waxy skin; motion improved vs prior near-static); "
        "not Proof_Landed; claim policy requires human_frame_read=pass; "
        f"{row_bit}"
        "claim_tier=class_e_attempt_fail; "
        "proof_tier=RUNPOD_WAN_TI2V_BOUNDED_CLASS_E_MOTION_REGEN_HUMAN_VISUAL_FAIL; "
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
        f"TRK-W64-019_023_WAN_TI2V_CLASS_E_MOTION_REGEN_HUMAN_VISUAL_FAIL_POLICY_{STAMP}.json",
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
        "bytes_gate_ok": True,
        "vlm_verdict": "PASS",
        "human_visual_verdict": "FAIL",
        "human_frame_read": "fail",
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
        f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_E_MOTION_REGEN_HUMAN_VISUAL_FAIL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    dump_json(
        "Plan/Tracker/Evidence/Wave64/"
        f"TRK-W64-019_023_WAN_TI2V_CLASS_E_MOTION_REGEN_HUMAN_VISUAL_FAIL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    print("tip", tip)
    print("synced TRK/ITEM-W64-019/023 Wan TI2V Class E motion regen HUMAN VISUAL FAIL")
    print("bytes", ARTIFACT_BYTES, "gate OK; VLM PASS overridden; human FAIL")
    print("NOT Proof_Landed; no COMPLETE; Row074 untouched")


if __name__ == "__main__":
    main()
