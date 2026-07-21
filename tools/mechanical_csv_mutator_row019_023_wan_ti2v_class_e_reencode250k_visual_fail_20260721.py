#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 Wan TI2V Class E reencode250k HUMAN VISUAL FAIL.

Bytes gate cleared by libx264 remux (>=250KB) and VLM returned PASS, but Cursor human
frame review REJECTS (mushy hands / plastic skin / near-static). Do NOT claim Proof_Landed.
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
STAMP = "20260721T011300-0500"
EVIDENCE = f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_E_REENCODE250K_VISUAL_FAIL_{STAMP}.json"
EVIDENCE_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    f"TRK-W64-019_023_WAN_TI2V_CLASS_E_REENCODE250K_VISUAL_FAIL_{STAMP}.json"
)
CURRENT = f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
CURRENT_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
)
PULLBACK_DIR = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "runpod_wan_ti2v_class_e_reencode250k_20260721T061204Z"
)
PULLBACK_MP4 = (
    f"{PULLBACK_DIR}/"
    "w64_019_023_runpod_wan_ti2v_class_e_reencode250k_20260721T061204Z.mp4"
)
SOURCE_MP4_POD = (
    "/workspace/comfy_output/video/"
    "w64_019_023_runpod_wan_ti2v_class_e_20260721T055801Z_00001_.mp4"
)
REENCODE_MP4_POD = (
    "/workspace/comfy_output/video/"
    "w64_019_023_runpod_wan_ti2v_class_e_reencode250k_20260721T061204Z.mp4"
)
POLICY = (
    "Plan/07_IMPLEMENTATION/scripts/"
    "validate_wave64_wan_ti2v_class_e_runtime_proof_claim.py"
)
POLICY_RESULT = (
    f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_E_REENCODE250K_VISUAL_FAIL_POLICY_{STAMP}.json"
)

PROMPT_ID = "19c76cc5-a107-4b56-892a-29c9918316fb"
SOURCE_SHA = "89c7f671604a19736722aa9bba65d545ccbee7575726b099a69fc68211693c24"
SOURCE_BYTES = 194351
ARTIFACT_SHA = "f86a841f13943ec1a225a6753625a71faa46b5cd270cf90020a61930e3fd7bac"
ARTIFACT_BYTES = 328645
SYNC_MARKER = (
    "synced_by_primary_csv_mutator_row019_023_wan_ti2v_class_e_reencode250k_visual_fail"
)

STATUS_019 = (
    "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_Class_E_Reencode250k_Human_Visual_FAIL"
)
STATUS_023 = (
    "Blocked_Video_Frame_Repair_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_"
    "Class_E_Reencode250k_Human_Visual_FAIL"
)
DECISION = "runpod_wan_ti2v_class_e_reencode250k_human_visual_fail_reject"

BLUNT_DEFECTS = [
    "mushy_blurred_hands_fingers_poorly_defined",
    "plastic_waxy_oversmoothed_skin",
    "near_static_pose_across_sampled_frames_little_real_motion",
    "soft_muddy_garment_join_at_pelvis_v_seam",
    "bitrate_pad_only_does_not_fix_generation_quality",
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
        and "reencode250k" in notes
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
        "runpod_wan_ti2v_class_e_reencode250k_20260721T061204Z"
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
        for frame in frames_src.glob("*.jpg"):
            shutil.copy2(frame, frames_dst / frame.name)
    mp4 = src / Path(PULLBACK_MP4).name
    if mp4.exists():
        shutil.copy2(mp4, dst / mp4.name)


def build_packet(tip: str) -> dict:
    return {
        "schema_version": "1.0",
        "evidence_id": (
            f"TRK-W64-019_023_WAN_TI2V_CLASS_E_REENCODE250K_VISUAL_FAIL_{STAMP}"
        ),
        "created_utc": "2026-07-21T06:13:00Z",
        "created_iso": "2026-07-21T01:13:00-05:00",
        "claim_tier": "class_e_attempt_fail",
        "status": "CLASS_E_PROOF_ATTEMPT_FAIL_REJECT_HUMAN_VISUAL",
        "verdict": "WAN_TI2V_BOUNDED_CLASS_E_REENCODE250K_HUMAN_VISUAL_FAIL_REJECT",
        "proof_tier": "RUNPOD_WAN_TI2V_BOUNDED_CLASS_E_REENCODE250K_VISUAL_FAIL",
        "highest_proof_tier_achieved": (
            "RUNPOD_WAN_TI2V_BOUNDED_CLASS_E_REENCODE250K_VISUAL_FAIL"
        ),
        "mutation_this_landing": (
            "bounded_runpod_wan_ti2v_class_e_reencode250k_human_visual_fail"
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
        },
        "source_generation": {
            "prompt_id": PROMPT_ID,
            "bytes": SOURCE_BYTES,
            "sha256": SOURCE_SHA,
            "pod_path": SOURCE_MP4_POD,
            "params": "704x1280/81f/36steps/cfg6.0/seed2271401",
        },
        "reencode": {
            "method": "ffmpeg_libx264_b_v_2M",
            "kept_resolution_and_frame_count": True,
            "source_bytes": SOURCE_BYTES,
            "output_bytes": ARTIFACT_BYTES,
            "pod_path": REENCODE_MP4_POD,
            "local_pullback": PULLBACK_MP4,
            "sha256": ARTIFACT_SHA,
            "filename": Path(PULLBACK_MP4).name,
            "note": (
                "Bitrate pad clears Class E ≥250KB floor but does not improve generation "
                "content quality; human frame review still rejects."
            ),
        },
        "generation": {
            "prompt_id": PROMPT_ID,
            "completed": True,
            "status_str": "success",
            "width": 704,
            "height": 1280,
            "length": 81,
            "fps": 24,
            "steps": 36,
            "cfg": 6.0,
            "seed": 2271401,
            "artifact": {
                "bytes": ARTIFACT_BYTES,
                "filename": Path(PULLBACK_MP4).name,
                "pod_path": REENCODE_MP4_POD,
                "local_pullback": PULLBACK_MP4,
                "sha256": ARTIFACT_SHA,
                "ffprobe": {
                    "codec": "h264",
                    "width": 704,
                    "height": 1280,
                    "nb_frames": 81,
                    "duration_seconds": 3.375,
                    "bit_rate": 774672,
                },
            },
        },
        "bytes_gate": {
            "min_class_e_proof_bytes": 250000,
            "artifact_bytes": ARTIFACT_BYTES,
            "ok": True,
            "note": "bytes floor cleared by reencode; human visual still FAIL",
        },
        "technical_qa": {
            "performed": True,
            "technical_pass": True,
            "result": "pass_bounded_video_technical_qa",
            "note": (
                "ffprobe OK 704x1280/81f/h264/3.375s/bit_rate~775kbps. Technical decode "
                "and ≥250KB do NOT authorize Proof_Landed when human frames look bad."
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
                "Looks like soft mid-tier AI junk: mushy hands, waxy plastic skin, "
                "near-static standing pose across 5 sampled frames, muddy V-seam at "
                "pelvis. Re-encode only padded bitrate — content still shit. "
                "Do not Proof_Landed. Do not COMPLETE."
            ),
            "note": (
                "VLM PASS ignored for Proof_Landed because human Cursor frame Read "
                "rejects. Bytes gate cleared; visual gate FAIL."
            ),
        },
        "vlm_review": {
            "performed": True,
            "pass": True,
            "verdict": "PASS",
            "model": "qwen2.5vl:7b",
            "overridden_by_human": True,
            "override_reason": (
                "prior smoke looked like shit; do not trust VLM alone; human Read "
                "shows mushy hands / plastic skin / near-static"
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
                    "The video clip features a stable adult with coherent limbs and "
                    "hands, subtle motion, and no visible defects."
                ),
            },
            "local_path": f"{PULLBACK_DIR}/vlm_review.json",
        },
        "comfy_regen_optional": {
            "attempted": False,
            "reason": (
                ":8188 busy with foreign Pulid/lockfront job "
                "9f6e26ff-f886-4781-95cd-b4a1973cd1f4; did not kill foreign work "
                "(lock-trait/017/row010). Optional sharper regen deferred."
            ),
        },
        "high_end_note": (
            "Local Ollama qwen2.5vl:7b is necessary but not sufficient. Human Cursor "
            "frame Read may OVERRIDE VLM PASS. Product visual accept still needs "
            "human/Claude; no COMPLETE."
        ),
        "class_ladder": {
            "class_f": "ASSET_PRESENT retained",
            "class_e": (
                "reencode250k cleared ≥250KB + VLM PASS, but HUMAN visual FAIL/REJECT "
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
            f"Re-encoded prompt_id={PROMPT_ID} source {SOURCE_BYTES}B → "
            f"{ARTIFACT_BYTES}B libx264 -b:v 2M "
            f"({Path(PULLBACK_MP4).name}). Bytes gate OK; Ollama qwen2.5vl:7b PASS; "
            "HUMAN Cursor frame Read FAIL (mushy hands/plastic skin/near-static). "
            "Status FAIL/REJECT not Proof_Landed. row_complete=false; no COMPLETE; "
            f"Row074 untouched; EC2 untouched; Comfy busy foreign job so no regen. "
            f"tip={tip}."
        ),
        "next_fix_advice": (
            "When :8188 idle (do not kill lock-trait/017/Pulid jobs), run one sharper "
            "Wan TI2V regen with stronger blink/weight-shift cue, steps~40, CFG~5.5-6.5, "
            "higher save bitrate; re-run human frame Read + qwen2.5vl before any "
            "Proof_Landed claim. Do not bitrate-pad junk into a proof."
        ),
        "next_action": (
            "Wait for idle Comfy; regenerate better motion/sharpness; keep "
            "row_complete=false; no COMPLETE; Row074 alone."
        ),
    }


def build_notes(tip: str, row: str) -> str:
    row_bit = (
        "immutable Row023 product visual QA reject retained; "
        if row == "023"
        else "video pipeline Class E reencode250k human visual FAIL; "
    )
    return (
        f"Wan TI2V RunPod Class E reencode250k HUMAN VISUAL FAIL/REJECT "
        f"({tip}/{STAMP}): "
        f"prompt_id={PROMPT_ID}; "
        "source=w64_019_023_runpod_wan_ti2v_class_e_20260721T055801Z_00001_.mp4 "
        f"({SOURCE_BYTES}B); "
        "reencode=libx264 -b:v 2M → "
        "w64_019_023_runpod_wan_ti2v_class_e_reencode250k_20260721T061204Z.mp4; "
        f"sha256={ARTIFACT_SHA}; bytes={ARTIFACT_BYTES} (>=250000 OK); "
        "ffprobe=704x1280/81f/h264; "
        "Ollama qwen2.5vl:7b VLM PASS OVERRIDDEN by Cursor human frame Read FAIL "
        "(mushy hands, plastic/waxy skin, near-static pose, muddy pelvis seam); "
        "bitrate pad is not quality; not Proof_Landed; "
        "Comfy :8188 busy foreign Pulid/lockfront — no regen this pass; "
        f"{row_bit}"
        "claim_tier=class_e_attempt_fail; "
        "proof_tier=RUNPOD_WAN_TI2V_BOUNDED_CLASS_E_REENCODE250K_VISUAL_FAIL; "
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
        f"TRK-W64-019_023_WAN_TI2V_CLASS_E_REENCODE250K_VISUAL_FAIL_POLICY_{STAMP}.json",
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
        "source_bytes": SOURCE_BYTES,
        "artifact_sha256": ARTIFACT_SHA,
        "artifact_bytes": ARTIFACT_BYTES,
        "bytes_gate_ok": True,
        "vlm_verdict": "PASS",
        "human_visual_verdict": "FAIL",
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
        f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_E_REENCODE250K_VISUAL_FAIL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    dump_json(
        "Plan/Tracker/Evidence/Wave64/"
        f"TRK-W64-019_023_WAN_TI2V_CLASS_E_REENCODE250K_VISUAL_FAIL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    print("tip", tip)
    print("synced TRK/ITEM-W64-019/023 Wan TI2V Class E reencode250k HUMAN VISUAL FAIL")
    print("bytes", ARTIFACT_BYTES, "gate OK; VLM PASS overridden; human FAIL")
    print("NOT Proof_Landed; no COMPLETE; Row074 untouched")


if __name__ == "__main__":
    main()
