#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 Class A product visual+temporal QA FAIL.

Exact clip: prompt_id fa05a902... sharp-hand climb raw 340905B (Class E Proof_Landed
retained). Dense 17-frame timeline human Read: hands anatomy retention mostly OK;
identity stable; residual FAIL = near-static / weak temporal motion. row_complete=false;
no COMPLETE; Row074 alone; no Wan re-fetch; no 017 redo; RunPod only.
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
STAMP = "20260721T045800-0500"
STAMP_UTC_JOB = "20260721T094222Z"
EVIDENCE = f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_A_TEMPORAL_MOTION_FAIL_{STAMP}.json"
EVIDENCE_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    f"TRK-W64-019_023_WAN_TI2V_CLASS_A_TEMPORAL_MOTION_FAIL_{STAMP}.json"
)
CURRENT = f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
CURRENT_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
)
PULLBACK_DIR = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    f"runpod_wan_ti2v_sharp_hand_climb_{STAMP_UTC_JOB}"
)
CLASS_A_FRAMES = f"{PULLBACK_DIR}/class_a_frames16"
PULLBACK_MP4 = (
    f"{PULLBACK_DIR}/"
    f"w64_019_023_runpod_wan_ti2v_sharp_hand_climb_{STAMP_UTC_JOB}_00001_.mp4"
)
POD_MP4 = (
    "/workspace/comfy_output/video/"
    f"w64_019_023_runpod_wan_ti2v_sharp_hand_climb_{STAMP_UTC_JOB}_00001_.mp4"
)
POD_FRAMES = (
    "/workspace/comfy_output/video/"
    f"w64_019_023_sharp_hand_climb_{STAMP_UTC_JOB}_class_a_frames16"
)

PROMPT_ID = "fa05a902-46bf-4e96-8024-d13f74e9eada"
ARTIFACT_SHA = "6b5d5aed6e90a75dbdb9fd3a18026b7eb8d5e328c3a076da7cd7fb6d4993196d"
ARTIFACT_BYTES = 340905
START_STILL = "c1_sharp_hand_start_still_20260721T092218Z_a1.png"
START_SHA = "ac43980940f3ae3187249f485bdd94ec69550a9cb96d4df3ebf163c8712cbcc4"
PRIOR_PROOF = (
    f"{EVID}/TRK-W64-019_023_WAN_TI2V_SHARP_HAND_CLIMB_PROOF_LANDED_20260721T045000-0500.json"
)
SYNC_MARKER = (
    "synced_by_primary_csv_mutator_row019_023_wan_ti2v_class_a_temporal_motion_fail"
)

STATUS_019 = (
    "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_Class_A_Temporal_Motion_FAIL"
)
STATUS_023 = (
    "Blocked_Video_Frame_Repair_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_"
    "Class_A_Temporal_Motion_FAIL"
)
DECISION = "runpod_wan_ti2v_class_a_temporal_motion_fail_open"


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
        and "Class_A_Temporal_Motion_FAIL" in notes
        and PROMPT_ID in notes
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
    src = ROOT / CLASS_A_FRAMES.replace("/", "\\")
    dst = ROOT / (
        "Plan/Instructions/QA/Evidence/Wave64/fixtures/row019_023/runtime/"
        f"runpod_wan_ti2v_sharp_hand_climb_{STAMP_UTC_JOB}_class_a_frames16"
    ).replace("/", "\\")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "ffprobe.json",
        "motion_mae.json",
        "frame_01.png",
        "frame_05.png",
        "frame_09.png",
        "frame_13.png",
        "frame_17.png",
        "face_region_first.png",
        "face_region_last.png",
        "hands_band_first.png",
        "hands_band_mid.png",
        "hands_band_last.png",
        "hand_left_first.png",
        "hand_left_mid.png",
        "hand_left_last.png",
        "hand_right_first.png",
        "hand_right_mid.png",
        "hand_right_last.png",
    ):
        p = src / name
        if p.exists():
            shutil.copy2(p, dst / name)


def load_mae() -> dict:
    p = ROOT / CLASS_A_FRAMES.replace("/", "\\") / "motion_mae.json"
    return json.loads(p.read_text(encoding="utf-8"))


def build_packet(tip: str) -> dict:
    mae = load_mae()
    frames_reviewed = [
        f"{CLASS_A_FRAMES}/frame_01.png",
        f"{CLASS_A_FRAMES}/frame_05.png",
        f"{CLASS_A_FRAMES}/frame_09.png",
        f"{CLASS_A_FRAMES}/frame_13.png",
        f"{CLASS_A_FRAMES}/frame_17.png",
        f"{CLASS_A_FRAMES}/face_region_first.png",
        f"{CLASS_A_FRAMES}/face_region_last.png",
        f"{CLASS_A_FRAMES}/hands_band_first.png",
        f"{CLASS_A_FRAMES}/hands_band_mid.png",
        f"{CLASS_A_FRAMES}/hands_band_last.png",
        f"{CLASS_A_FRAMES}/hand_left_first.png",
        f"{CLASS_A_FRAMES}/hand_left_mid.png",
        f"{CLASS_A_FRAMES}/hand_left_last.png",
        f"{CLASS_A_FRAMES}/hand_right_first.png",
        f"{CLASS_A_FRAMES}/hand_right_mid.png",
        f"{CLASS_A_FRAMES}/hand_right_last.png",
    ]
    return {
        "schema_version": "1.0",
        "evidence_id": f"TRK-W64-019_023_WAN_TI2V_CLASS_A_TEMPORAL_MOTION_FAIL_{STAMP}",
        "created_utc": "2026-07-21T09:58:00Z",
        "created_iso": "2026-07-21T04:58:00-05:00",
        "claim_tier": "class_a_product_visual_temporal_qa",
        "status": "CLASS_A_PRODUCT_VISUAL_TEMPORAL_FAIL_OPEN",
        "verdict": "WAN_TI2V_CLASS_A_TEMPORAL_MOTION_FAIL_OPEN",
        "class_a_verdict": "FAIL_OPEN",
        "proof_tier": "RUNPOD_WAN_TI2V_CLASS_A_TEMPORAL_MOTION_FAIL",
        "highest_proof_tier_achieved": (
            "RUNPOD_WAN_TI2V_BOUNDED_SHARP_HAND_CLIMB_RUNTIME_PROOF_LANDED"
        ),
        "class_e_runtime_proof_retained": True,
        "prior_class_e_evidence": PRIOR_PROOF,
        "mutation_this_landing": (
            "bounded_runpod_wan_ti2v_class_a_product_visual_temporal_qa_fail"
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
            "steps": 40,
            "cfg": 6.0,
            "seed": 2272711,
            "bit_depth": 10,
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
                    "bit_rate": 808071,
                    "pix_fmt": "yuv420p10le",
                },
            },
        },
        "pod_locate": {
            "performed": True,
            "pod_path": POD_MP4,
            "sha256_match": True,
            "bytes_match": True,
            "ffprobe_ok": True,
            "dense_frames_pod_dir": POD_FRAMES,
            "dense_frames_local_dir": CLASS_A_FRAMES,
            "dense_frame_count": mae.get("n_frames"),
            "source_frame_indices": mae.get("source_frame_indices"),
            "motion_mae": (
                {k: v for k, v in mae.get("mae_pairs", [])}
                if isinstance(mae.get("mae_pairs"), list)
                else mae.get("mae_pairs")
            ),
        },
        "bytes_gate": {
            "min_class_e_proof_bytes": 250000,
            "artifact_bytes": ARTIFACT_BYTES,
            "ok": True,
            "note": (
                "Class E bytes gate still PASS; this landing is Class A product "
                "visual+temporal QA on the same raw clip — not a bytes re-gate."
            ),
        },
        "technical_qa": {
            "performed": True,
            "technical_pass": True,
            "result": "pass_decode_and_dense_extract",
            "note": (
                "ffprobe OK 704x1280/81f/h264/yuv420p10le/3.375s/~808kbps; "
                "extracted 17 frames every 5 source frames across full timeline."
            ),
        },
        "class_a_human_temporal_read": {
            "performed": True,
            "pass": False,
            "verdict": "FAIL_OPEN",
            "scope": "product_visual_and_temporal_qa_dense_timeline",
            "frames_reviewed": frames_reviewed,
            "axes": {
                "hands_retention_over_time": {
                    "verdict": "PASS_WITH_SOFTENING",
                    "note": (
                        "Palms-forward raised hands keep five separated fingers across "
                        "timeline samples; knuckle/palm structure readable early/mid. "
                        "Late frames show softer/blurrier hand edges vs start."
                    ),
                },
                "skin_retention_over_time": {
                    "verdict": "PASS_ANATOMY_SMOOTH",
                    "note": (
                        "No mushy melt or color tear across timeline; skin stays "
                        "hyper-smooth/airbrushed. Class E hands+skin anatomy PASS retained; "
                        "not the Class A residual FAIL."
                    ),
                },
                "motion_naturalness": {
                    "verdict": "FAIL",
                    "note": (
                        "Pose-locked near-static: same palms-forward raised-hand "
                        "composition across 17 samples spanning full 3.375s. No "
                        "unmistakable chest breathing cycle, full blink, or weight-shift. "
                        f"MAE first_last={dict(mae.get('mae_pairs', [])).get('first_last')}; "
                        f"mid_last={dict(mae.get('mae_pairs', [])).get('mid_last')} "
                        "(RGB0-255) = modest drift, not product-grade motion."
                    ),
                },
                "identity": {
                    "verdict": "PASS",
                    "note": (
                        "Face/hair/earrings/body identity stable first→last; no identity swap."
                    ),
                },
                "artifacts": {
                    "verdict": "SECONDARY_ISSUES",
                    "note": (
                        "Late-hand softening; hyper-smooth skin; stiff locked pose. "
                        "No catastrophic morph/melt."
                    ),
                },
            },
            "fail_conditions_checked": [
                "near_static_pose_lock",
                "missing_breathing_blink_weight_shift",
                "hands_melt_over_time",
                "identity_drift",
                "catastrophic_artifacts",
            ],
            "fail_conditions_observed": [
                "near_static_pose_lock",
                "missing_breathing_blink_weight_shift",
            ],
            "exact_defects": [
                {
                    "id": "near_static_pose_lock",
                    "severity": "primary",
                    "detail": (
                        "Subject pose and camera framing essentially frozen across dense "
                        "timeline (indices 0..80 step 5); reads as still-with-microdrift."
                    ),
                },
                {
                    "id": "missing_requested_temporal_actions",
                    "severity": "primary",
                    "detail": (
                        "Requested clearer breathing/blink/weight-shift not visibly "
                        "delivered as unmistakable human motion events."
                    ),
                },
                {
                    "id": "late_hand_softening",
                    "severity": "secondary",
                    "detail": (
                        "Hands remain anatomically countable but soften/blur toward end "
                        "vs start sharpness."
                    ),
                },
                {
                    "id": "skin_hyper_smooth",
                    "severity": "secondary",
                    "detail": (
                        "Skin remains airbrushed/pore-weak vs photographic microtexture "
                        "expectation at Class A product bar."
                    ),
                },
            ],
            "blunt_human_verdict": (
                "Class A FAIL/OPEN. Hands+skin anatomy retention mostly holds "
                "(digits separated, no melt) — that was the Class E win. Product "
                "temporal QA fails hard: clip is near-static; locked palms-forward "
                "pose for ~3.4s with no clear breath/blink/weight-shift. Identity OK. "
                "Do not COMPLETE. Prefer evidence over another climb this increment."
            ),
        },
        "visual_qa": {
            "performed": True,
            "pass": False,
            "result": "fail_class_a_temporal_motion_open",
            "reviewer": "cursor_human_dense_timeline_read",
            "high_end_llm_in_loop": False,
            "ollama_vlm_in_loop": False,
            "prior_vlm_secondary": {
                "performed": True,
                "model": "qwen2.5vl:7b",
                "verdict": "FAIL",
                "near_static": True,
                "note": (
                    "Prior Class E landing VLM FAIL/near_static retained as secondary; "
                    "not re-run this increment (human dense timeline is decisive)."
                ),
                "local_path": f"{PULLBACK_DIR}/vlm_review.json",
            },
            "blunt_human_verdict": (
                "Class A product visual+temporal FAIL/OPEN on near-static motion. "
                "Class E Proof_Landed (human hands+skin + bytes) retained. "
                "row_complete=false; no COMPLETE."
            ),
        },
        "motion_climb_recommendation": {
            "auto_run_this_increment": False,
            "reason_not_auto_run": (
                "Job prefers evidence-first; residual is clearly motion; do not burn "
                "queue unless idle and climb explicitly authorized next."
            ),
            "bounded_next_climb": {
                "allowed": True,
                "same_start_still": START_STILL,
                "same_start_sha256": START_SHA,
                "keep": [
                    "704x1280",
                    "81f",
                    "steps~40",
                    "cfg6.0",
                    "CreateVideo.bit_depth=10",
                    "no Flux LoRAs on Wan",
                    "no Wan weight re-fetch",
                    "no 017 redo",
                    "Row074 alone",
                ],
                "strengthen": [
                    "explicit multi-cycle chest breathing rise/fall",
                    "one unmistakable full blink eyelids close then open",
                    "visible relaxed weight-shift or micro head turn",
                    "motion language stronger than prior climb prompt",
                ],
                "hard_gates_after": [
                    "human dense timeline Read must show unmistakable motion events",
                    "hands must not melt vs Class E PASS",
                    "raw bytes stay >=250KB",
                ],
            },
        },
        "comfy_regen": {
            "attempted": False,
            "note": (
                "No regen this increment — Class A evaluation only on existing "
                f"prompt_id={PROMPT_ID}."
            ),
        },
        "wan_refetch": False,
        "row017_touched": False,
        "class_ladder": {
            "class_f": "ASSET_PRESENT retained",
            "class_e": (
                "sharp-hand climb human hands+skin PASS and raw bytes>=250KB — "
                "Runtime_Proof_Landed RETAINED"
            ),
            "class_a": (
                "product visual+temporal QA FAIL/OPEN — near-static residual motion defect"
            ),
            "not_claimed": [
                "row_complete",
                "COMPLETE",
                "class_a_pass",
                "production_video_lane_certification",
            ],
        },
        "row_complete": False,
        "production_completion_allowed": False,
        "production_video_complete_claimed": False,
        "row074_touched": False,
        "ec2_touched": False,
        "local_comfy_touched": False,
        "summary": (
            f"Class A FAIL/OPEN on sharp-hand climb prompt_id={PROMPT_ID} "
            f"raw {ARTIFACT_BYTES}B ({Path(PULLBACK_MP4).name}). Dense 17-frame "
            "human Read: hands retention PASS_WITH_SOFTENING; identity PASS; "
            "motion FAIL near-static (no clear breath/blink/weight-shift). "
            "Class E Proof_Landed retained. row_complete=false; no COMPLETE; "
            f"Row074 untouched; EC2 untouched; no Wan refetch; no 017 redo. tip={tip}."
        ),
        "next_fix_advice": (
            "1) Later one bounded motion-stronger Wan I2V climb from same start still "
            f"{START_STILL} (sha=ac439809...) — only when queue free / authorized. "
            "2) Keep bit_depth=10 + hands integrity; never Flux LoRAs on Wan. "
            "3) No Wan re-fetch; no 017 redo; Row074 alone. "
            "4) Do not mark COMPLETE from Class E alone or this Class A FAIL."
        ),
        "next_action": (
            "Keep row_complete=false; Status Class A Temporal Motion FAIL/open; "
            "no COMPLETE; Row074 alone; recommend later motion-stronger climb; "
            "do not auto-run this increment."
        ),
        "tip": tip,
    }


def build_notes(tip: str, row: str) -> str:
    row_bit = (
        "immutable Row023 product visual QA reject retained; "
        if row == "023"
        else "video pipeline Class A temporal FAIL/open; "
    )
    return (
        f"Wan TI2V RunPod Class A product visual+temporal FAIL/OPEN "
        f"({tip}/{STAMP}): "
        f"prompt_id={PROMPT_ID}; "
        f"artifact=w64_019_023_runpod_wan_ti2v_sharp_hand_climb_{STAMP_UTC_JOB}_00001_.mp4; "
        f"sha256={ARTIFACT_SHA}; bytes={ARTIFACT_BYTES} (Class E bytes PASS retained); "
        "params=704x1280/81f/40steps/cfg6.0/seed2272711/bit_depth10; "
        f"I2V start={START_STILL} sha={START_SHA}; "
        "dense 17-frame human Read across timeline: hands retention PASS_WITH_SOFTENING; "
        "identity PASS; motion FAIL near-static (no clear breath/blink/weight-shift; "
        "MAE first_last~21.2); Class E Proof_Landed retained; "
        "prior VLM FAIL/near-static secondary not re-run; "
        f"{row_bit}"
        "claim_tier=class_a_product_visual_temporal_qa; "
        "proof_tier=RUNPOD_WAN_TI2V_CLASS_A_TEMPORAL_MOTION_FAIL; "
        "next=optional later one motion-stronger climb same start still when authorized; "
        "no auto-run this increment; no Flux LoRAs on Wan; no Wan re-fetch; no 017 redo; "
        "row_complete=false; no COMPLETE; Row074 left alone; EC2 untouched; "
        f"local Comfy untouched. Evidence: {EVIDENCE}; {CLASS_A_FRAMES}; {PRIOR_PROOF}"
    )


def main() -> None:
    tip = git_short()
    mp4 = ROOT / PULLBACK_MP4.replace("/", "\\")
    if not mp4.exists():
        raise SystemExit(f"missing pullback mp4: {mp4}")
    actual = mp4.stat().st_size
    if actual != ARTIFACT_BYTES:
        raise SystemExit(f"byte mismatch: expected {ARTIFACT_BYTES} got {actual}")
    mae_path = ROOT / CLASS_A_FRAMES.replace("/", "\\") / "motion_mae.json"
    if not mae_path.exists():
        raise SystemExit(f"missing motion_mae.json: {mae_path}")

    sync_fixtures()
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
    evid = f"{EVIDENCE}; {CLASS_A_FRAMES}; {PRIOR_PROOF}"
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
        "class_a_verdict": "FAIL_OPEN",
        "human_temporal_verdict": "FAIL_NEAR_STATIC",
        "hands_retention": "PASS_WITH_SOFTENING",
        "identity": "PASS",
        "class_e_proof_retained": True,
        "proof_landed": False,
        "rows": ["TRK-W64-019", "TRK-W64-023", "ITEM-W64-019", "ITEM-W64-023"],
        "status_019": STATUS_019,
        "status_023": STATUS_023,
        "status_decision": DECISION,
        "claim_tier": "class_a_product_visual_temporal_qa",
        "row074_touched": False,
        "complete_claimed": False,
        "row_complete": False,
        "motion_climb_auto_run": False,
        "evidence": EVIDENCE,
    }
    dump_json(
        f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_A_TEMPORAL_MOTION_FAIL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    dump_json(
        "Plan/Tracker/Evidence/Wave64/"
        f"TRK-W64-019_023_WAN_TI2V_CLASS_A_TEMPORAL_MOTION_FAIL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    print("tip", tip)
    print("synced TRK/ITEM-W64-019/023 Wan TI2V Class A temporal motion FAIL/OPEN")
    print("Class E Proof_Landed retained; Class A FAIL near-static; no COMPLETE")
    print("Row074 untouched; no Wan refetch; no 017 redo")


if __name__ == "__main__":
    main()
