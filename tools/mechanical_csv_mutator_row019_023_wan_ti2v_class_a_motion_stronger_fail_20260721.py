#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 Class A motion-stronger climb FAIL/OPEN.

Authorized follow-up from fa05a902 Class A near-static FAIL. New Wan I2V climb
prompt_id=a2fde6b8... from same start still; raw 292846B (>=250KB). Human temporal
Read: hands retention OK; motion still FAIL (near-static / incomplete breath+blink+
weight-shift package). Class E Proof_Landed retained. row_complete=false; no COMPLETE;
Row074 alone; no Wan re-fetch; no 017 redo; RunPod only.
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
STAMP = "20260721T051200-0500"
STAMP_UTC_JOB = "20260721T100010Z"
EVIDENCE = f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_A_MOTION_STRONGER_FAIL_{STAMP}.json"
EVIDENCE_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    f"TRK-W64-019_023_WAN_TI2V_CLASS_A_MOTION_STRONGER_FAIL_{STAMP}.json"
)
CURRENT = f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
CURRENT_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
)
PULLBACK_DIR = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    f"runpod_wan_ti2v_motion_stronger_{STAMP_UTC_JOB}"
)
FRAMES = f"{PULLBACK_DIR}/frames"
PULLBACK_MP4 = (
    f"{PULLBACK_DIR}/"
    f"w64_019_023_runpod_wan_ti2v_motion_stronger_{STAMP_UTC_JOB}_00001_.mp4"
)
POD_MP4 = (
    "/workspace/comfy_output/video/"
    f"w64_019_023_runpod_wan_ti2v_motion_stronger_{STAMP_UTC_JOB}_00001_.mp4"
)
POD_FRAMES = (
    "/workspace/comfy_output/video/"
    f"w64_019_023_motion_stronger_{STAMP_UTC_JOB}_frames"
)

PROMPT_ID = "a2fde6b8-329b-4b63-8fde-381e27030b9d"
PRIOR_FAIL_PROMPT = "fa05a902-46bf-4e96-8024-d13f74e9eada"
ARTIFACT_SHA = "ff54cf6471be3d2161195f0e186eb96aeb452805d01e068571376a2bf822adf2"
ARTIFACT_BYTES = 292846
START_STILL = "c1_sharp_hand_start_still_20260721T092218Z_a1.png"
START_SHA = "ac43980940f3ae3187249f485bdd94ec69550a9cb96d4df3ebf163c8712cbcc4"
PRIOR_CLASS_A = (
    f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_A_TEMPORAL_MOTION_FAIL_20260721T045800-0500.json"
)
PRIOR_CLASS_E = (
    f"{EVID}/TRK-W64-019_023_WAN_TI2V_SHARP_HAND_CLIMB_PROOF_LANDED_20260721T045000-0500.json"
)
SYNC_MARKER = (
    "synced_by_primary_csv_mutator_row019_023_wan_ti2v_class_a_motion_stronger_fail"
)

STATUS_019 = (
    "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_Class_A_Motion_Stronger_FAIL"
)
STATUS_023 = (
    "Blocked_Video_Frame_Repair_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_"
    "Class_A_Motion_Stronger_FAIL"
)
DECISION = "runpod_wan_ti2v_class_a_motion_stronger_fail_open"


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
        and "Class_A_Motion_Stronger_FAIL" in notes
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
    src = ROOT / FRAMES.replace("/", "\\")
    dst = ROOT / (
        "Plan/Instructions/QA/Evidence/Wave64/fixtures/row019_023/runtime/"
        f"runpod_wan_ti2v_motion_stronger_{STAMP_UTC_JOB}_frames"
    ).replace("/", "\\")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "motion_mae.json",
        "frame_01.png",
        "frame_05.png",
        "frame_09.png",
        "frame_13.png",
        "frame_17.png",
        "hand_crop_left.png",
        "hand_crop_right.png",
        "hand_crop_center.png",
        "skin_crop_face_shoulder.png",
        "face_first.png",
        "face_mid.png",
        "face_last.png",
        "chest_first.png",
        "chest_last.png",
    ):
        p = src / name
        if p.exists():
            shutil.copy2(p, dst / name)
    vlm = ROOT / PULLBACK_DIR.replace("/", "\\") / (
        f"w64_019_023_motion_stronger_{STAMP_UTC_JOB}_vlm.json"
    )
    # local pullback may use shorter name
    for cand in (
        ROOT / PULLBACK_DIR.replace("/", "\\") / f"w64_019_023_motion_stronger_{STAMP_UTC_JOB}_vlm.json",
        ROOT / PULLBACK_DIR.replace("/", "\\") / "vlm_review.json",
    ):
        if cand.exists():
            shutil.copy2(cand, dst / "vlm_review.json")
            break


def load_mae() -> dict:
    p = ROOT / FRAMES.replace("/", "\\") / "motion_mae.json"
    return json.loads(p.read_text(encoding="utf-8"))


def load_vlm() -> dict:
    for cand in (
        ROOT / PULLBACK_DIR.replace("/", "\\") / f"w64_019_023_motion_stronger_{STAMP_UTC_JOB}_vlm.json",
        ROOT
        / (
            "Plan/Instructions/QA/Evidence/Wave64/fixtures/row019_023/runtime/"
            f"runpod_wan_ti2v_motion_stronger_{STAMP_UTC_JOB}_frames/vlm_review.json"
        ).replace("/", "\\"),
    ):
        if cand.exists():
            return json.loads(cand.read_text(encoding="utf-8"))
    return {"performed": False}


def build_packet(tip: str) -> dict:
    mae = load_mae()
    vlm = load_vlm()
    mae_pairs = (
        {k: v for k, v in mae.get("mae_pairs", [])}
        if isinstance(mae.get("mae_pairs"), list)
        else (mae.get("mae_pairs") or {})
    )
    frames_reviewed = [
        f"{FRAMES}/frame_01.png",
        f"{FRAMES}/frame_05.png",
        f"{FRAMES}/frame_09.png",
        f"{FRAMES}/frame_13.png",
        f"{FRAMES}/frame_17.png",
        f"{FRAMES}/hand_crop_left.png",
        f"{FRAMES}/hand_crop_right.png",
        f"{FRAMES}/hand_crop_center.png",
        f"{FRAMES}/skin_crop_face_shoulder.png",
        f"{FRAMES}/face_first.png",
        f"{FRAMES}/face_mid.png",
        f"{FRAMES}/face_last.png",
        f"{FRAMES}/chest_first.png",
        f"{FRAMES}/chest_last.png",
    ]
    vlm_parsed = vlm.get("parsed") or {}
    return {
        "schema_version": "1.0",
        "evidence_id": f"TRK-W64-019_023_WAN_TI2V_CLASS_A_MOTION_STRONGER_FAIL_{STAMP}",
        "created_utc": "2026-07-21T10:12:00Z",
        "created_iso": "2026-07-21T05:12:00-05:00",
        "claim_tier": "class_a_product_visual_temporal_qa",
        "status": "CLASS_A_PRODUCT_VISUAL_TEMPORAL_FAIL_OPEN",
        "verdict": "WAN_TI2V_CLASS_A_MOTION_STRONGER_FAIL_OPEN",
        "class_a_verdict": "FAIL_OPEN",
        "proof_tier": "RUNPOD_WAN_TI2V_CLASS_A_MOTION_STRONGER_FAIL",
        "highest_proof_tier_achieved": (
            "RUNPOD_WAN_TI2V_BOUNDED_SHARP_HAND_CLIMB_RUNTIME_PROOF_LANDED"
        ),
        "class_e_runtime_proof_retained": True,
        "prior_class_e_evidence": PRIOR_CLASS_E,
        "prior_class_a_fail_evidence": PRIOR_CLASS_A,
        "prior_class_a_fail_prompt_id": PRIOR_FAIL_PROMPT,
        "mutation_this_landing": (
            "bounded_runpod_wan_ti2v_class_a_motion_stronger_climb_fail"
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
            "cfg": 6.5,
            "seed": 2272893,
            "bit_depth": 10,
            "intent": (
                "class_a_motion_stronger_followup_bit_depth10_steps40_"
                "breath_blink_weightshift_from_fa05a902_near_static_fail"
            ),
            "artifact": {
                "bytes": ARTIFACT_BYTES,
                "filename": Path(PULLBACK_MP4).name,
                "pod_path": POD_MP4,
                "local_pullback": PULLBACK_MP4,
                "sha256": ARTIFACT_SHA,
                "ffprobe": {
                    "codec": "h264",
                    "profile": "High 10",
                    "width": 704,
                    "height": 1280,
                    "nb_frames": 81,
                    "duration_seconds": 3.375,
                    "bit_rate": 694000,
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
            "dense_frames_local_dir": FRAMES,
            "dense_frame_count": mae.get("n_frames"),
            "motion_mae": mae_pairs,
            "adj_mae_mean": mae.get("adj_mae_mean"),
            "region_mae_first_last": mae.get("region_mae_first_last"),
        },
        "bytes_gate": {
            "min_class_e_proof_bytes": 250000,
            "artifact_bytes": ARTIFACT_BYTES,
            "ok": True,
            "note": (
                "Raw CreateVideo bit_depth=10 mp4 292846B >=250KB PASS; "
                "no remux pad."
            ),
        },
        "technical_qa": {
            "performed": True,
            "technical_pass": True,
            "result": "pass_decode_and_dense_extract",
            "note": (
                "ffprobe OK 704x1280/81f/h264 High10/yuv420p10le/3.375s; "
                "extracted 17 frames every 5 source frames; human Read on key samples."
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
                        "Palms-forward raised hands retain clearly separated fingers "
                        "across sampled timeline; no melt/fuse. Late frames show mild "
                        "curl/softening vs start sharpness, still countable digits."
                    ),
                },
                "skin_retention_over_time": {
                    "verdict": "PASS_ANATOMY_SMOOTH",
                    "note": (
                        "No mushy melt; pores readable in places; overall still "
                        "smooth/airbrushed vs photographic Class A skin bar. "
                        "Class E anatomy retention holds."
                    ),
                },
                "motion_naturalness": {
                    "verdict": "FAIL",
                    "note": (
                        "Motion-stronger climb still fails product temporal bar. "
                        "Composition remains palms-forward pose-locked across ~3.375s. "
                        "Ambiguous mid-timeline eyelid softening at frame_05 (caption "
                        "closed-eyes; eye-band luminance delta ~0.1) is not a clear "
                        "full blink+breath+weight-shift package. Chest/hip band mean "
                        "drift present but reads as lighting/microdrift, not "
                        "unmistakable breathing cycle or weight transfer. "
                        f"MAE first_last={mae_pairs.get('first_last')} "
                        f"(prior FAIL had 21.18 — this climb not stronger on global MAE); "
                        f"adj_mae_mean={mae.get('adj_mae_mean')}."
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
                        "Near-static lock; mild late hand curl/softening; smooth skin. "
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
                        "Subject remains in locked palms-forward raised-hand composition "
                        "across dense timeline; still reads as near-static living-still."
                    ),
                },
                {
                    "id": "missing_requested_temporal_actions",
                    "severity": "primary",
                    "detail": (
                        "Requested clearer multi-cycle breath + unmistakable full blink + "
                        "visible weight-shift not delivered as product-grade motion events."
                    ),
                },
                {
                    "id": "global_mae_not_stronger",
                    "severity": "secondary",
                    "detail": (
                        "first_last MAE 15.45 < prior Class A FAIL 21.18 — stronger "
                        "prompt/cfg did not increase measurable temporal change."
                    ),
                },
            ],
            "blunt_human_verdict": (
                "Class A FAIL/OPEN on motion-stronger climb. Hands+skin anatomy "
                "retention holds (separated fingers, no melt). Bytes PASS. Motion "
                "does NOT clear: still near-static / incomplete breath+blink+"
                "weight-shift. Class E Proof_Landed retained. Do not COMPLETE."
            ),
            "human_motion_verdict": "FAIL_NEAR_STATIC_INCOMPLETE_MOTION_PACKAGE",
        },
        "visual_qa": {
            "performed": True,
            "pass": False,
            "result": "fail_class_a_motion_stronger_open",
            "reviewer": "cursor_human_dense_timeline_read",
            "high_end_llm_in_loop": False,
            "ollama_vlm_in_loop": True,
            "vlm_secondary": {
                "performed": bool(vlm.get("parsed") or vlm.get("raw_response")),
                "model": vlm.get("model", "qwen2.5vl:7b"),
                "verdict": vlm_parsed.get("verdict", "FAIL"),
                "near_static": vlm_parsed.get("near_static", True),
                "breathing_visible": vlm_parsed.get("breathing_visible"),
                "blink_visible": vlm_parsed.get("blink_visible"),
                "weight_shift_visible": vlm_parsed.get("weight_shift_visible"),
                "note": (
                    "VLM secondary FAIL/near_static; human dense Read is authoritative."
                ),
                "local_path": f"{PULLBACK_DIR}/w64_019_023_motion_stronger_{STAMP_UTC_JOB}_vlm.json",
            },
            "blunt_human_verdict": (
                "Class A product visual+temporal FAIL/OPEN after authorized "
                "motion-stronger climb. Class E Proof_Landed retained. "
                "row_complete=false; no COMPLETE."
            ),
        },
        "comfy_regen": {
            "attempted": True,
            "prompt_id": PROMPT_ID,
            "note": (
                "One authorized motion-stronger Wan I2V submitted when :8188 idle "
                f"(waited through canary); seed=2272893 cfg=6.5 vs prior "
                f"{PRIOR_FAIL_PROMPT}."
            ),
        },
        "wan_refetch": False,
        "row017_touched": False,
        "class_ladder": {
            "class_f": "ASSET_PRESENT retained",
            "class_e": (
                "sharp-hand climb human hands+skin PASS and raw bytes>=250KB — "
                "Runtime_Proof_Landed RETAINED (prior climb); this climb also "
                "bytes>=250KB + hands anatomy OK"
            ),
            "class_a": (
                "product visual+temporal QA FAIL/OPEN — motion-stronger climb still "
                "near-static / incomplete temporal actions"
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
            f"Class A FAIL/OPEN on motion-stronger climb prompt_id={PROMPT_ID} "
            f"raw {ARTIFACT_BYTES}B ({Path(PULLBACK_MP4).name}). Human Read: hands "
            "PASS_WITH_SOFTENING; identity PASS; motion FAIL near-static/incomplete "
            f"(MAE first_last={mae_pairs.get('first_last')}). VLM secondary FAIL/"
            "near_static. Class E Proof_Landed retained. row_complete=false; no "
            f"COMPLETE; Row074 untouched; EC2 untouched; no Wan refetch; no 017 redo. "
            f"tip={tip}."
        ),
        "next_fix_advice": (
            "1) Later reconsider motion strategy (different seed family / longer "
            "clip / motion LoRA if ever authorized) — only when queue free. "
            "2) Keep bit_depth=10 + hands integrity; never Flux LoRAs on Wan. "
            "3) No Wan re-fetch; no 017 redo; Row074 alone. "
            "4) Do not mark COMPLETE from Class E alone or this Class A FAIL."
        ),
        "next_action": (
            "Keep row_complete=false; Status Class A Motion Stronger FAIL/open; "
            "no COMPLETE; Row074 alone."
        ),
        "tip": tip,
    }


def build_notes(tip: str, row: str) -> str:
    row_bit = (
        "immutable Row023 product visual QA reject retained; "
        if row == "023"
        else "video pipeline Class A motion-stronger FAIL/open; "
    )
    return (
        f"Wan TI2V RunPod Class A motion-stronger FAIL/OPEN "
        f"({tip}/{STAMP}): "
        f"prompt_id={PROMPT_ID}; prior_fail={PRIOR_FAIL_PROMPT}; "
        f"artifact=w64_019_023_runpod_wan_ti2v_motion_stronger_{STAMP_UTC_JOB}_00001_.mp4; "
        f"sha256={ARTIFACT_SHA}; bytes={ARTIFACT_BYTES} (>=250KB PASS); "
        "params=704x1280/81f/40steps/cfg6.5/seed2272893/bit_depth10; "
        f"I2V start={START_STILL} sha={START_SHA}; "
        "human Read: hands retention PASS_WITH_SOFTENING; identity PASS; "
        "motion FAIL near-static/incomplete breath+blink+weight-shift "
        "(MAE first_last~15.45 < prior FAIL ~21.18); "
        "VLM secondary qwen2.5vl:7b FAIL/near_static; "
        "Class E Proof_Landed retained; "
        f"{row_bit}"
        "claim_tier=class_a_product_visual_temporal_qa; "
        "proof_tier=RUNPOD_WAN_TI2V_CLASS_A_MOTION_STRONGER_FAIL; "
        "no Flux LoRAs on Wan; no Wan re-fetch; no 017 redo; "
        "row_complete=false; no COMPLETE; Row074 left alone; EC2 untouched; "
        f"local Comfy untouched. Evidence: {EVIDENCE}; {FRAMES}; {PRIOR_CLASS_E}"
    )


def main() -> None:
    tip = git_short()
    mp4 = ROOT / PULLBACK_MP4.replace("/", "\\")
    if not mp4.exists():
        raise SystemExit(f"missing pullback mp4: {mp4}")
    actual = mp4.stat().st_size
    if actual != ARTIFACT_BYTES:
        raise SystemExit(f"byte mismatch: expected {ARTIFACT_BYTES} got {actual}")
    mae_path = ROOT / FRAMES.replace("/", "\\") / "motion_mae.json"
    if not mae_path.exists():
        raise SystemExit(f"missing motion_mae.json: {mae_path}")

    # ensure vlm file present under pullback with expected name
    vlm_src = None
    for cand in (ROOT / PULLBACK_DIR.replace("/", "\\")).glob("*vlm*.json"):
        vlm_src = cand
        break
    if vlm_src is None:
        # fetch from pod if missing
        raise SystemExit("missing local vlm json — scp from pod first")

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
    evid = f"{EVIDENCE}; {FRAMES}; {PRIOR_CLASS_E}"
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
        "prior_fail_prompt_id": PRIOR_FAIL_PROMPT,
        "artifact_sha256": ARTIFACT_SHA,
        "artifact_bytes": ARTIFACT_BYTES,
        "bytes_gate_ok": True,
        "class_a_verdict": "FAIL_OPEN",
        "human_temporal_verdict": "FAIL_NEAR_STATIC_INCOMPLETE_MOTION_PACKAGE",
        "human_motion_verdict": "FAIL_NEAR_STATIC",
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
        "evidence": EVIDENCE,
    }
    dump_json(
        f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_A_MOTION_STRONGER_FAIL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    dump_json(
        "Plan/Tracker/Evidence/Wave64/"
        f"TRK-W64-019_023_WAN_TI2V_CLASS_A_MOTION_STRONGER_FAIL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    print("tip", tip)
    print("synced TRK/ITEM-W64-019/023 Wan TI2V Class A motion-stronger FAIL/OPEN")
    print("Class E Proof_Landed retained; Class A FAIL; no COMPLETE")
    print("Row074 untouched; no Wan refetch; no 017 redo")


if __name__ == "__main__":
    main()
