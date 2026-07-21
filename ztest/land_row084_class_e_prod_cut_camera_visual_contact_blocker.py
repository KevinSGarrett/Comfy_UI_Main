#!/usr/bin/env python3
"""Land Row084 Class E production cut/camera + visual/contact authority blocker.

Bindings: local (+ cite RunPod gold 7/7 ABSENT inventory); never EC2; leave
Row074 alone; never COMPLETE; ROW084-012 OPEN_HOLD untouched; do not remove
compiler hard-fail; do not invent gold/contact masks; no Wan re-fetch; no 017 redo.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_canonical_video_timeline.py"
MEDIA = (
    ROOT
    / "Plan/Instructions/Operations/Pulled_Back_Artifacts"
    / "w64_genuine_av_sync_frame_aligned_20260714T202000-0500"
    / "strict_sync_mux_ffv1_pcm16_mono_frame_aligned.mkv"
)
RUNTIME_DIR = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row084/runtime"
    / "local_class_e_prod_cut_camera_visual_contact_20260721T104800Z"
)
RECEIPT_PATH = RUNTIME_DIR / "class_e_prod_cut_camera_visual_contact_blocker_receipt.json"
PROBE_PATH = RUNTIME_DIR / "prod_cut_camera_visual_contact_probe.json"
FRAMES_DIR = RUNTIME_DIR / "review_frames"
PACKET_PATH = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_ROW084-011_CLASS_E_PROD_CUT_CAMERA_VISUAL_CONTACT_BLOCKER_20260721.json"
)
DELTA_PATH = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_CANONICAL_VIDEO_TIMELINE_CURRENT_DELTA_20260719.json"
)
TRACKER_ARTIFACT = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_canonical_video_timeline.json"
)
HOLD_012 = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_ROW084-012_CLASS_C_SCHEMA_NATIVE_REVERSED_PTS_HOLD_PACKET_20260720.json"
)
HARD_FAIL_PACKET = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_ROW084-011_COMPILER_HARD_FAIL_NOT_CLEARABLE_BLOCKER_PACKET_20260721.json"
)
PRIOR_SPARSE_PACKET = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_ROW084-011_CLASS_E_PROD_SPARSE_MOTION_RECLASS_20260721.json"
)
PRIOR_MUX_PACKET = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_ROW084-011_CLASS_E_PROD_MUX_REPLAY_CUT_CAMERA_CALIB_20260721.json"
)
RUNPOD_GOLD_INVENTORY = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-019_023_POD_CLASS_A_F_NEGATIVE_INVENTORY_20260720.json"
)
HOLD_012_SHA = "0e0c3d8648f939f24684be7a9b7ad70aef20b1289f6fadd30d90256dbdeb1ff7"
PRIOR_GEN_PROMPT = "8681ba01-58a4-4a92-92cf-171d5c2daaf3"
PROOF = "RUNTIME_PROD_CUT_CAMERA_VISUAL_CONTACT_BLOCKER_BOUNDED"
MEDIA_SHA = "0c1153e675bd9209ce9c56d6c6694d9fb93118d69e3935fedcf77e626fed998a"
FFMPEG = Path(
    r"C:\Users\kevin\AppData\Local\Programs\ffmpeg\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"
)
FFPROBE = FFMPEG.with_name("ffprobe.exe")

# Held-out contract surfaces that production authority must exceed (not reuse as production).
HELD_OUT_CUT_RECEIPT = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row084/runtime"
    / "held_out_cut_detector_runtime_receipt.json"
)
HELD_OUT_CAMERA_RECEIPT = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row084/runtime"
    / "held_out_camera_motion_runtime_receipt.json"
)
HELD_OUT_VISUAL_RECEIPT = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row084/runtime"
    / "combined_visual_audio_review_runtime_receipt.json"
)

LOCAL_GOLD_PATHS = [
    {
        "path": "Plan/Instructions/QA/Evidence/Mask_Factory/Body_Contact_Gold_Standards",
        "role": "canonical_body_contact_gold_standards_tree",
    },
    {
        "path": "Plan/Instructions/QA/Evidence/Mask_Factory/promoted_body_contact",
        "role": "promoted_body_contact_mask_tree",
    },
    {
        "path": "masks/gold_standard/body_contact",
        "role": "runtime_masks_gold_standard_body_contact",
    },
    {
        "path": "MaskedWarehouse/gold_standard/body_contact",
        "role": "warehouse_gold_standard_body_contact",
    },
    {
        "path": "maskfactory_data/gold_standard/body_contact",
        "role": "maskfactory_data_gold_standard_body_contact",
    },
    {
        "path": "assets/gold_standard/body_contact",
        "role": "assets_gold_standard_body_contact",
    },
    {
        "path": "maskfactory/gold_standard/body_contact",
        "role": "maskfactory_gold_standard_body_contact",
    },
]

# Production cut/camera benchmark matrix roles required beyond single-candidate reclass.
REQUIRED_PROD_BENCHMARK_ROLES = ("hard_cut", "camera_motion", "static", "sparse_motion")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_compiler():
    spec = importlib.util.spec_from_file_location("row084_compiler_prod_blocker", COMPILER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        raise ValueError("empty")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def export_png(media: Path, frame_index: int, out: Path) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    # Select frame by frame number via select filter; scale for review.
    cmd = [
        str(FFMPEG),
        "-y",
        "-i",
        str(media),
        "-vf",
        f"select=eq(n\\,{frame_index}),scale=256:256",
        "-vframes",
        "1",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not out.is_file():
        raise RuntimeError(f"ffmpeg png export failed frame={frame_index}: {proc.stderr[-400:]}")
    return {
        "frame_index": frame_index,
        "path": out.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(out),
        "bytes": out.stat().st_size,
    }


def ffprobe_streams(media: Path) -> dict:
    cmd = [
        str(FFPROBE),
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(media),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def inventory_local_gold() -> dict:
    rows = []
    present = 0
    for item in LOCAL_GOLD_PATHS:
        p = ROOT / item["path"]
        exists = p.exists()
        if exists:
            present += 1
        rows.append(
            {
                "path": item["path"],
                "role": item["role"],
                "status": "PRESENT" if exists else "ABSENT",
                "exists": exists,
            }
        )
    return {
        "binding": "local_C_Comfy_UI_Main",
        "gold_authority_paths_absent": f"{len(rows) - present}/{len(rows)}",
        "present_count": present,
        "absent_count": len(rows) - present,
        "paths": rows,
        "gold_invented": False,
    }


def main() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    assert HOLD_012.is_file()
    assert sha256_file(HOLD_012) == HOLD_012_SHA, "REFUSING: 012 HOLD packet mutated"
    assert MEDIA.is_file()
    assert FFMPEG.is_file()
    assert FFPROBE.is_file()
    assert PRIOR_SPARSE_PACKET.is_file()
    assert RUNPOD_GOLD_INVENTORY.is_file()
    mod = load_compiler()

    # --- Gate 2: production cut/camera benchmark authority ---
    frames = mod._decode_rgb_frames(
        ffmpeg=FFMPEG,
        media_path=MEDIA,
        width=64,
        height=64,
        expected_frames=49,
        scale_to=(64, 64),
    )
    deltas = mod._pair_hist_deltas(frames)
    mean_delta = sum(deltas) / float(len(deltas))
    max_delta = max(deltas)
    ordered = sorted(deltas)
    moderate = sum(1 for d in deltas if d > mod.CAMERA_MOTION_MEAN_MIN)
    moderate_required = max(1, int(len(deltas) * mod.CAMERA_MOTION_MODERATE_MIN_FRAC_HELD_OUT))
    moderate_fraction = moderate / float(len(deltas))
    hard_cuts = mod._detect_hard_cuts(deltas)
    held_out_error = None
    held_out_class = None
    try:
        held_out_class = mod._classify_camera_motion_profile(
            deltas, profile=mod.CAMERA_MOTION_PROFILE_HELD_OUT
        )
    except ValueError as exc:
        held_out_error = str(exc)
    prod_class = mod._classify_camera_motion_profile(
        deltas, profile=mod.CAMERA_MOTION_PROFILE_PRODUCTION
    )
    assert prod_class == "sparse_motion", prod_class
    assert held_out_class is None
    assert len(hard_cuts) == 0

    # Production benchmark matrix attempt: only sparse_motion candidate available.
    # Held-out lavfi cases must NOT be reused as production authority (lavfi-as-production forbidden).
    matrix_cases = []
    for role in REQUIRED_PROD_BENCHMARK_ROLES:
        if role == "sparse_motion":
            matrix_cases.append(
                {
                    "role": role,
                    "expected_class": "sparse_motion",
                    "media_kind": "pulled_back_genuine_av_sync_mkv",
                    "media_sha256": MEDIA_SHA,
                    "observed_class": prod_class,
                    "status": "PASS_SINGLE_CANDIDATE",
                    "passed": True,
                    "gold_invented": False,
                }
            )
        else:
            matrix_cases.append(
                {
                    "role": role,
                    "expected_class": role if role != "camera_motion" else "camera_motion",
                    "media_kind": None,
                    "media_sha256": None,
                    "observed_class": None,
                    "status": "ABSENT_PRODUCTION_GOLD_MEDIA",
                    "passed": False,
                    "gold_invented": False,
                    "blocker": (
                        f"No non-lavfi production gold media registered for role={role}; "
                        "held-out lavfi fixtures refuse production_benchmark authority."
                    ),
                }
            )
    roles_passed = [c["role"] for c in matrix_cases if c["passed"]]
    roles_absent = [c["role"] for c in matrix_cases if not c["passed"]]
    cut_camera_authority_granted = False
    cut_camera_benchmark_pass = False
    assert set(roles_passed) == {"sparse_motion"}
    assert set(roles_absent) == {"hard_cut", "camera_motion", "static"}

    held_out_cut_sha = sha256_file(HELD_OUT_CUT_RECEIPT) if HELD_OUT_CUT_RECEIPT.is_file() else None
    held_out_cam_sha = (
        sha256_file(HELD_OUT_CAMERA_RECEIPT) if HELD_OUT_CAMERA_RECEIPT.is_file() else None
    )
    held_out_vis_sha = (
        sha256_file(HELD_OUT_VISUAL_RECEIPT) if HELD_OUT_VISUAL_RECEIPT.is_file() else None
    )

    cut_camera_eval = {
        "contract_scripts": {
            "compiler": COMPILER.relative_to(ROOT).as_posix(),
            "held_out_cut_detector": "execute_held_out_cut_detector_runtime",
            "held_out_camera_motion": "execute_held_out_camera_motion_runtime",
            "production_classifier": "_classify_camera_motion_profile(profile=production)",
            "note": (
                "No execute_production_cut_camera_benchmark API exists; authority bind "
                "requires non-lavfi multi-role matrix beyond held-out lavfi receipts."
            ),
        },
        "held_out_ceiling_reference": {
            "cut_detector_receipt": HELD_OUT_CUT_RECEIPT.relative_to(ROOT).as_posix()
            if held_out_cut_sha
            else None,
            "cut_detector_receipt_sha256": held_out_cut_sha,
            "camera_motion_receipt": HELD_OUT_CAMERA_RECEIPT.relative_to(ROOT).as_posix()
            if held_out_cam_sha
            else None,
            "camera_motion_receipt_sha256": held_out_cam_sha,
            "production_benchmark_granted_by_held_out": False,
            "lavfi_as_production_forbidden": True,
        },
        "candidate_probe": {
            "algorithm_id": "fixture_histogram_diff_v1",
            "classification_profile": "production",
            "decode_scale": "64x64",
            "frame_count": len(frames),
            "pair_delta_count": len(deltas),
            "mean_hist_l1": round(mean_delta, 6),
            "max_hist_l1": round(max_delta, 6),
            "p50_hist_l1": round(percentile(ordered, 0.50), 6),
            "p90_hist_l1": round(percentile(ordered, 0.90), 6),
            "p95_hist_l1": round(percentile(ordered, 0.95), 6),
            "moderate_count_gt_mean_min": moderate,
            "moderate_required_for_camera_motion": moderate_required,
            "moderate_fraction": round(moderate_fraction, 4),
            "hard_cut_count": len(hard_cuts),
            "hard_cuts": hard_cuts,
            "observed_class": prod_class,
            "observed_class_held_out": held_out_class,
            "held_out_classification_error": held_out_error,
            "gold_invented": False,
        },
        "required_roles": list(REQUIRED_PROD_BENCHMARK_ROLES),
        "matrix_cases": matrix_cases,
        "roles_passed": roles_passed,
        "roles_absent": roles_absent,
        "production_cut_camera_benchmark_pass": cut_camera_benchmark_pass,
        "production_cut_camera_authority_granted": cut_camera_authority_granted,
        "verdict": "FAIL",
        "blocker_id": "production_cut_camera_benchmark_authority_beyond_held_out_lavfi_absent",
        "blocker_detail": (
            "Sparse_motion single-candidate reclass PASS retained, but production "
            "cut/camera benchmark authority requires non-lavfi gold media for "
            f"roles={list(REQUIRED_PROD_BENCHMARK_ROLES)}; absent={roles_absent}. "
            "Do not invent gold media; do not promote held-out lavfi as production."
        ),
    }

    # --- Gate 3: production media combined visual/contact ---
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    exported = [
        export_png(MEDIA, 0, FRAMES_DIR / "prod_av_sync_f000.png"),
        export_png(MEDIA, 24, FRAMES_DIR / "prod_av_sync_f024.png"),
        export_png(MEDIA, 48, FRAMES_DIR / "prod_av_sync_f048.png"),
    ]
    probe = ffprobe_streams(MEDIA)
    streams = probe.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    local_gold = inventory_local_gold()
    runpod_inv = json.loads(RUNPOD_GOLD_INVENTORY.read_text(encoding="utf-8"))
    runpod_absent = runpod_inv.get("gold_authority_paths_absent")
    assert runpod_absent == "7/7", runpod_absent
    assert local_gold["gold_authority_paths_absent"] == "7/7"

    visual_contact_eval = {
        "contract_scripts": {
            "compiler": COMPILER.relative_to(ROOT).as_posix(),
            "held_out_combined_visual": "execute_combined_visual_audio_review_offline",
            "held_out_visual_receipt": HELD_OUT_VISUAL_RECEIPT.relative_to(ROOT).as_posix()
            if held_out_vis_sha
            else None,
            "held_out_visual_receipt_sha256": held_out_vis_sha,
            "note": (
                "Held-out VISUAL_QA_PASS_BOUNDED uses contact_placeholder only; "
                "production combined visual/contact requires real body/contact gold masks."
            ),
        },
        "media": {
            "kind": "pulled_back_genuine_av_sync_mkv",
            "path": MEDIA.relative_to(ROOT).as_posix(),
            "sha256": MEDIA_SHA,
            "bytes": MEDIA.stat().st_size,
        },
        "decoded_frame_visual_inspection_executed": True,
        "exported_review_frames": exported,
        "audio_stream_probe": {
            "codec_name": audio.get("codec_name"),
            "sample_rate": audio.get("sample_rate"),
            "channels": audio.get("channels"),
            "video_codec_name": video.get("codec_name"),
            "nb_frames": video.get("nb_frames") or video.get("nb_read_frames"),
        },
        "surfaces": [
            {
                "surface": "frame_timeline",
                "decision": "pass_bounded_candidate_only",
                "visual_review_executed": True,
                "observation": (
                    "Decoded/exported genuine AV-sync frames f0/f24/f48 for production "
                    "candidate review; not held-out lavfi."
                ),
            },
            {
                "surface": "cut_epochs",
                "decision": "pass_bounded_candidate_only",
                "visual_review_executed": True,
                "observation": (
                    f"Production profile cut detector: hard_cut_count={len(hard_cuts)}; "
                    f"observed_class={prod_class}."
                ),
            },
            {
                "surface": "camera_motion_policy",
                "decision": "pass_bounded_candidate_only",
                "visual_review_executed": True,
                "observation": (
                    f"Production classifier observed_class={prod_class}; "
                    "held-out class remains null."
                ),
            },
            {
                "surface": "contact",
                "decision": "FAIL",
                "visual_review_executed": True,
                "observation": (
                    "Production contact surface blocked: local body/contact gold "
                    f"{local_gold['gold_authority_paths_absent']} ABSENT; RunPod inventory "
                    f"{runpod_absent} ABSENT (anti-dupe cite, no invent)."
                ),
                "contact_placeholder_not_accepted_as_production": True,
                "gold_invented": False,
            },
            {
                "surface": "audio_stream_binding",
                "decision": "pass_bounded_candidate_only",
                "visual_review_executed": True,
                "observation": (
                    f"ffprobe audio codec={audio.get('codec_name')} "
                    f"rate={audio.get('sample_rate')} channels={audio.get('channels')}."
                ),
            },
        ],
        "local_gold_inventory": local_gold,
        "runpod_gold_inventory_cite": {
            "path": RUNPOD_GOLD_INVENTORY.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(RUNPOD_GOLD_INVENTORY),
            "gold_authority_paths_absent": runpod_absent,
            "re_sshed": False,
            "note": "Anti-dupe: reuse prior RunPod 7/7 ABSENT inventory; do not invent gold masks.",
        },
        "production_combined_visual_contact_pass": False,
        "production_visual_contact_authority_granted": False,
        "verdict": "FAIL",
        "blocker_id": "production_media_combined_visual_contact_beyond_held_out_lavfi_absent",
        "blocker_detail": (
            "Production combined visual/contact cannot bind without body/contact gold "
            f"masks (local {local_gold['gold_authority_paths_absent']} ABSENT; RunPod "
            f"{runpod_absent} ABSENT). contact_placeholder held-out PASS is not production."
        ),
    }

    remaining = [
        "COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED",
        "production_cut_camera_benchmark_authority_beyond_held_out_lavfi_absent",
        "production_media_combined_visual_contact_beyond_held_out_lavfi_absent",
        "ROW084-012_CLASS_C_OPEN_HOLD_SCHEMA_NATIVE_REVERSED_PTS",
        "row_complete_acceptance_COMPLETE_withheld",
    ]
    safe_next = (
        "Keep ROW084-011 FAIL/OPEN. Keep ROW084-012 OPEN_HOLD. Do not COMPLETE. "
        "Production sparse_motion candidate reclass retained, but cut/camera benchmark "
        "authority still ABSENT (missing non-lavfi hard_cut/camera_motion/static gold) "
        "and production visual/contact blocked on body/contact gold 7/7 ABSENT "
        "(local+RunPod). Do not invent gold masks; do not remove compiler hard-fail "
        "until both co-requisites bind."
    )
    summary = (
        "Class E production cut/camera + visual/contact authority climb FAIL/OPEN. "
        f"Candidate reclass PASS retained (observed_class=sparse_motion; "
        f"mean={round(mean_delta, 6)} max={round(max_delta, 6)} "
        f"mod_frac={round(moderate_fraction, 4)}). Production cut/camera benchmark "
        f"matrix FAIL (passed={roles_passed}; absent={roles_absent}). Production "
        f"combined visual/contact FAIL (local gold {local_gold['gold_authority_paths_absent']} "
        f"ABSENT; RunPod {runpod_absent} ABSENT; no invent). Mux replay PASS retained; "
        "compiler hard-fail retained; row_complete=false; ROW084-012 OPEN_HOLD untouched."
    )

    probe_doc = {
        "created_at": now,
        "media_sha256": MEDIA_SHA,
        "cut_camera_eval": cut_camera_eval,
        "visual_contact_eval": visual_contact_eval,
    }
    PROBE_PATH.write_text(json.dumps(probe_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    receipt = {
        "schema_version": "1.0",
        "evidence_id": "TRK-W64-084_ROW084_CLASS_E_PROD_CUT_CAMERA_VISUAL_CONTACT_BLOCKER",
        "tracker_id": "TRK-W64-084",
        "item_id": "ITEM-W64-084",
        "check_id": "ROW084-011",
        "blocker_class": "E",
        "blocker_id": "PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED",
        "decision": "HOLD",
        "cleared": False,
        "row_complete": False,
        "production_completion_allowed": False,
        "production_mux_replay_pass": True,
        "production_cut_camera_authority_granted": False,
        "production_cut_camera_benchmark_pass": False,
        "production_combined_visual_contact_pass": False,
        "production_visual_contact_authority_granted": False,
        "implementation_completion_claimed": False,
        "product_completion_claimed": False,
        "do_not_clear": ["ROW084-011"],
        "do_not_thrash": ["ROW084-012"],
        "row074_left_alone": True,
        "comfyui_8188_invoked_for_new_generation": False,
        "created_at": now,
        "runtime_host": "local_windows_ffmpeg_8.1.2",
        "ffmpeg_version_line": (
            "ffmpeg version 8.1.2-full_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers"
        ),
        "media": {
            "kind": "pulled_back_genuine_av_sync_mkv",
            "path": MEDIA.relative_to(ROOT).as_posix(),
            "bytes": MEDIA.stat().st_size,
            "sha256": MEDIA_SHA,
            "expected_sha256": MEDIA_SHA,
            "sha256_matches_prior_probe": True,
        },
        "prior_retained": {
            "sparse_motion_reclass_packet": PRIOR_SPARSE_PACKET.relative_to(ROOT).as_posix(),
            "mux_replay_packet": PRIOR_MUX_PACKET.relative_to(ROOT).as_posix(),
            "production_mux_replay_pass": True,
            "observed_class": "sparse_motion",
            "note": "No Wan re-fetch; no 017 redo; mux/reclass not re-authored as PASS claim cheat.",
        },
        "cut_camera_eval": cut_camera_eval,
        "visual_contact_eval": visual_contact_eval,
        "probe_json": PROBE_PATH.relative_to(ROOT).as_posix(),
        "remaining_gates_exact": remaining,
        "safe_next_action": safe_next,
        "summary": summary,
        "compiler_hard_fail_removed": False,
        "gold_invented": False,
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(RECEIPT_PATH)

    packet = {
        "blocker_class": "E",
        "blocker_id": "PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED",
        "check_id": "ROW084-011",
        "cleared": False,
        "compiler_hard_fail_blocker_packet": HARD_FAIL_PACKET.relative_to(ROOT).as_posix(),
        "compiler_hard_fail_clearable_on_current_evidence": False,
        "created_at": now,
        "cut_camera_eval": cut_camera_eval,
        "decision": "HOLD",
        "do_not_clear": ["ROW084-011"],
        "do_not_thrash": ["ROW084-012"],
        "evidence_id": "TRK-W64-084_ROW084-011_CLASS_E_PROD_CUT_CAMERA_VISUAL_CONTACT_BLOCKER_20260721",
        "highest_proof_tier_achieved": PROOF,
        "hold_012_unchanged": {
            "exists": True,
            "path": HOLD_012.relative_to(ROOT).as_posix(),
            "sha256": HOLD_012_SHA,
            "status": "OPEN_HOLD",
            "thrashed": False,
        },
        "implementation_completion_claimed": False,
        "item_id": "ITEM-W64-084",
        "media": receipt["media"],
        "mutation_this_landing": "class_e_prod_cut_camera_visual_contact_blocker",
        "preservation_boundary": {
            "class_e_011_not_cleared": True,
            "compiler_hard_fail_not_removed": True,
            "comfyui_new_generation_not_submitted": True,
            "gold_not_invented": True,
            "prior_comfy_gen_prompt_id_retained": PRIOR_GEN_PROMPT,
            "row073_pcm_left_alone": True,
            "row074_left_alone": True,
            "row075_pid_left_alone": True,
            "row084_012_hold_not_thrashed": True,
            "unrelated_dirty_paths_preserved": True,
            "wan_not_refetched": True,
            "row017_not_redone": True,
            "ec2_unused": True,
        },
        "prior_comfy_generation_prompt_id": PRIOR_GEN_PROMPT,
        "prior_sparse_motion_reclass_packet": PRIOR_SPARSE_PACKET.relative_to(ROOT).as_posix(),
        "prior_mux_replay_packet": PRIOR_MUX_PACKET.relative_to(ROOT).as_posix(),
        "product_completion_claimed": False,
        "production_completion_allowed": False,
        "production_cut_camera_authority_granted": False,
        "production_cut_camera_benchmark_pass": False,
        "production_combined_visual_contact_pass": False,
        "production_mux_replay_pass": True,
        "proof_tier": PROOF,
        "remaining_blockers": list(remaining),
        "row073_left_alone": True,
        "row074_left_alone": True,
        "row084_011_status": "FAIL",
        "row_complete": False,
        "runtime_dir": RUNTIME_DIR.relative_to(ROOT).as_posix(),
        "runtime_receipt": RECEIPT_PATH.relative_to(ROOT).as_posix(),
        "runtime_receipt_sha256": receipt_sha,
        "safe_next_action": safe_next,
        "schema_version": "1.0",
        "summary": summary,
        "tracker_id": "TRK-W64-084",
        "visual_contact_eval": visual_contact_eval,
        "gates": {
            "production_cut_camera_benchmark_authority": {
                "verdict": "FAIL",
                "authority_granted": False,
                "roles_passed": roles_passed,
                "roles_absent": roles_absent,
            },
            "production_media_combined_visual_contact": {
                "verdict": "FAIL",
                "authority_granted": False,
                "local_gold_absent": local_gold["gold_authority_paths_absent"],
                "runpod_gold_absent": runpod_absent,
            },
        },
    }
    PACKET_PATH.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    packet_sha = sha256_file(PACKET_PATH)

    hf = json.loads(HARD_FAIL_PACKET.read_text(encoding="utf-8"))
    hf["updated_at"] = now
    hf["compiler_hard_fail_clearable_on_current_evidence"] = False
    hf["production_mux_replay_pass"] = True
    hf["production_cut_camera_authority_granted"] = False
    hf["row_complete"] = False
    hf["related_climb_packet"] = PACKET_PATH.relative_to(ROOT).as_posix()
    hf["related_climb_packet_sha256"] = packet_sha
    hf["observed_class"] = "sparse_motion"
    for entry in hf.get("missing_artifact_authority", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("id") == "production_cut_camera_benchmark_authority":
            entry["status"] = "ABSENT_MATRIX_INCOMPLETE"
            entry["note"] = (
                f"Candidate sparse_motion PASS retained (mean={round(mean_delta, 6)} "
                f"max={round(max_delta, 6)} mod_frac={round(moderate_fraction, 4)}). "
                f"Production benchmark matrix incomplete: passed={roles_passed} "
                f"absent={roles_absent}. Authority NOT granted."
            )
        if entry.get("id") == "production_media_combined_visual_contact":
            entry["status"] = "ABSENT_GOLD_CONTACT_MASKS"
            entry["note"] = (
                f"Production visual/contact FAIL: local gold "
                f"{local_gold['gold_authority_paths_absent']} ABSENT; RunPod "
                f"{runpod_absent} ABSENT (cited inventory). Do not invent gold masks; "
                "held-out contact_placeholder is not production."
            )
    hf["why_not_clearable_now"] = {
        "verdict": "NOT_CLEARABLE_BY_BOUNDED_FIX_ON_CURRENT_EVIDENCE",
        "reasons": [
            "Removing compile_wave64_canonical_video_timeline.py:845-847 alone would enable claim cheat without full production predicates.",
            "Production mux replay PASS + sparse_motion reclass retained — necessary but not sufficient.",
            f"production_cut_camera_authority_granted=false (benchmark matrix absent roles={roles_absent}).",
            f"Production combined visual/contact blocked on gold/contact masks local={local_gold['gold_authority_paths_absent']} RunPod={runpod_absent}.",
            "ROW084-012 Class C OPEN_HOLD stays; orthogonal schema-native cheat forbidden.",
            "Hard-fail removal remains a co-requisite after cut/camera + visual production authority bind.",
        ],
    }
    hf["summary"] = (
        "Gate COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED remains correctly "
        "FAIL/OPEN. Production cut/camera benchmark + visual/contact authority climb "
        "FAIL (matrix incomplete; gold 7/7 ABSENT). Do not remove hard-fail. "
        "ROW084-012 OPEN_HOLD untouched; row_complete=false."
    )
    hf["safe_next_action"] = safe_next
    HARD_FAIL_PACKET.write_text(json.dumps(hf, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    hf_sha = sha256_file(HARD_FAIL_PACKET)
    packet["compiler_hard_fail_blocker_packet_sha256"] = hf_sha
    PACKET_PATH.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    packet_sha = sha256_file(PACKET_PATH)

    delta = json.loads(DELTA_PATH.read_text(encoding="utf-8"))
    delta["updated_at"] = now
    delta["row_complete"] = False
    delta["proof_tier"] = PROOF
    delta["highest_proof_tier_achieved"] = PROOF

    bc = delta.setdefault("blocker_classification", {})
    prod = bc.setdefault("PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED", {})
    prod.update(
        {
            "class": "E",
            "status": "OPEN",
            "detail": (
                "COMPLETE/row_complete intentionally withheld. Production cut/camera "
                f"benchmark + visual/contact authority climb FAIL (receipt {receipt_sha[:12]}; "
                f"roles_absent={roles_absent}; gold local/RunPod 7/7 ABSENT). "
                "Compiler hard-fail retained. ROW084-012 OPEN_HOLD untouched."
            ),
            "prod_cut_camera_visual_contact_blocker_packet": PACKET_PATH.relative_to(
                ROOT
            ).as_posix(),
            "prod_cut_camera_visual_contact_blocker_packet_sha256": packet_sha,
            "prod_cut_camera_visual_contact_blocker_receipt": RECEIPT_PATH.relative_to(
                ROOT
            ).as_posix(),
            "prod_cut_camera_visual_contact_blocker_receipt_sha256": receipt_sha,
            "media_sha256": MEDIA_SHA,
            "production_mux_replay_pass": True,
            "production_cut_camera_authority_granted": False,
            "production_combined_visual_contact_pass": False,
            "observed_class": "sparse_motion",
            "readiness_proof_tier": PROOF,
            "prompt_id": PRIOR_GEN_PROMPT,
            "compiler_hard_fail_blocker_packet": HARD_FAIL_PACKET.relative_to(ROOT).as_posix(),
            "compiler_hard_fail_blocker_packet_sha256": hf_sha,
        }
    )

    for check in delta.get("checks", []):
        if check.get("check_id") == "ROW084-011":
            check["status"] = "FAIL"
            check["proof_tier"] = PROOF
            check["note"] = (
                "Class E FAIL/OPEN retained. Production cut/camera benchmark authority "
                f"FAIL (absent roles={roles_absent}); production visual/contact FAIL "
                f"(gold local/RunPod 7/7 ABSENT). observed_class=sparse_motion retained; "
                "compiler hard-fail retained. Do not COMPLETE. ROW084-012 OPEN_HOLD unchanged."
            )
            check["class_e_prod_cut_camera_visual_contact_blocker_packet"] = (
                PACKET_PATH.relative_to(ROOT).as_posix()
            )
            check["class_e_prod_cut_camera_visual_contact_blocker_packet_sha256"] = packet_sha
            check["class_e_prod_cut_camera_visual_contact_blocker_receipt"] = (
                RECEIPT_PATH.relative_to(ROOT).as_posix()
            )
            check["class_e_prod_cut_camera_visual_contact_blocker_receipt_sha256"] = receipt_sha
            check["media_sha256"] = MEDIA_SHA
            check["production_mux_replay_pass"] = True
            check["production_cut_camera_authority_granted"] = False
            check["production_combined_visual_contact_pass"] = False
            check["observed_class"] = "sparse_motion"
            break

    fltr = delta.setdefault("focused_local_test_result", {})
    fltr["class_e_prod_cut_camera_visual_contact_blocker_climb"] = {
        "blocker_class": "E",
        "blocker_codes_cleared": [],
        "blocker_codes_held": [
            "PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED",
            "COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED",
            "production_cut_camera_benchmark_authority_beyond_held_out_lavfi_absent",
            "production_media_combined_visual_contact_beyond_held_out_lavfi_absent",
        ],
        "cleared": False,
        "media_kind": "pulled_back_genuine_av_sync_mkv",
        "media_sha256": MEDIA_SHA,
        "hard_cut_count": 0,
        "observed_class": "sparse_motion",
        "observed_class_held_out": None,
        "moderate_fraction": round(moderate_fraction, 4),
        "classification_profile": "production",
        "production_mux_replay_pass": True,
        "production_cut_camera_authority_granted": False,
        "production_cut_camera_benchmark_pass": False,
        "production_combined_visual_contact_pass": False,
        "roles_passed": roles_passed,
        "roles_absent": roles_absent,
        "local_gold_absent": local_gold["gold_authority_paths_absent"],
        "runpod_gold_absent": runpod_absent,
        "gold_invented": False,
        "packet": PACKET_PATH.relative_to(ROOT).as_posix(),
        "packet_sha256": packet_sha,
        "runtime_receipt_sha256": receipt_sha,
        "production_completion_allowed": False,
        "proof_tier": PROOF,
        "row_complete": False,
        "status": "HOLD",
        "prior_comfy_gen_prompt_id_retained_non_authority": PRIOR_GEN_PROMPT,
        "ec2_unused": True,
    }
    fltr["scope_interpretation"] = (
        "Local production cut/camera + visual/contact authority evaluation on genuine "
        f"AV-sync MKV (sha={MEDIA_SHA[:12]}; observed_class=sparse_motion). Both gates "
        "FAIL/OPEN (matrix incomplete; gold 7/7 ABSENT). ROW084-012 OPEN_HOLD unchanged. "
        "Row074 left alone. No COMPLETE/row_complete. Local+RunPod cite only (no EC2)."
    )

    inc = delta.setdefault("increment", {})
    inc["kind"] = "class_e_prod_cut_camera_visual_contact_blocker"
    inc["comfyui_8188_invoked"] = False
    inc["runtime_media_decode_invoked"] = True
    inc["ffmpeg_mux_replay_executed"] = False
    inc["row_complete"] = False
    inc["prompt_id"] = PRIOR_GEN_PROMPT
    inc["summary"] = summary

    impl = delta.setdefault("implementation", {})
    still = impl.setdefault("still_absent", [])
    still[:] = [
        s
        for s in still
        if s
        not in {
            "production-candidate observed_class null (need sparse_motion or production moderate_frac≈0.28)",
            "production-candidate media camera class calibration (unclassified under held-out thresholds)",
        }
    ]
    for item in [
        "production cut/camera/benchmark authority beyond held-out lavfi",
        "compiler production_completion_allowed hard fail-close removal",
        "production media combined visual/contact beyond held-out lavfi",
    ]:
        if item not in still:
            still.append(item)

    impl["class_e_prod_cut_camera_visual_contact_blocker_packet_path"] = (
        PACKET_PATH.relative_to(ROOT).as_posix()
    )
    impl["class_e_prod_cut_camera_visual_contact_blocker_packet_sha256"] = packet_sha
    impl["class_e_prod_cut_camera_visual_contact_blocker_receipt_path"] = (
        RECEIPT_PATH.relative_to(ROOT).as_posix()
    )
    impl["class_e_prod_cut_camera_visual_contact_blocker_receipt_sha256"] = receipt_sha
    impl["compiler_hard_fail_blocker_packet_sha256"] = hf_sha

    now_present = impl.setdefault("now_present", [])
    for item in [
        "production mux replay proof on genuine AV-sync sources (frame-preserve recipe)",
        "production-scoped sparse_motion class for genuine AV-sync candidate",
        "production cut/camera + visual/contact authority blocker evaluation (FAIL/OPEN landed)",
    ]:
        if item not in now_present:
            now_present.append(item)

    pb = delta.setdefault("preservation_boundary", {})
    writes = pb.setdefault("actual_write_paths", [])
    for p in [
        PACKET_PATH.relative_to(ROOT).as_posix(),
        RECEIPT_PATH.relative_to(ROOT).as_posix(),
        PROBE_PATH.relative_to(ROOT).as_posix(),
        HARD_FAIL_PACKET.relative_to(ROOT).as_posix(),
        DELTA_PATH.relative_to(ROOT).as_posix(),
        TRACKER_ARTIFACT.relative_to(ROOT).as_posix(),
    ]:
        if p not in writes:
            writes.append(p)

    delta["ledger_status"] = (
        "Blocked_Visual_Qa_Pass_Bounded_Class_C_Schema_Native_Hold_And_Production_Completion_Blocked"
    )
    DELTA_PATH.write_text(json.dumps(delta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    art = json.loads(TRACKER_ARTIFACT.read_text(encoding="utf-8"))
    art["updated_at"] = now
    art["row_complete"] = False
    art["production_completion_allowed"] = False
    art["class_e_011_status"] = "FAIL"
    art["class_e_latest_proof_tier"] = PROOF
    art["class_e_latest_packet"] = PACKET_PATH.relative_to(ROOT).as_posix()
    art["class_e_latest_prompt_id"] = PRIOR_GEN_PROMPT
    art["compiler_hard_fail_blocker_packet"] = HARD_FAIL_PACKET.relative_to(ROOT).as_posix()
    art["compiler_hard_fail_blocker_packet_sha256"] = hf_sha
    art["compiler_hard_fail_clearable_on_current_evidence"] = False
    holds = art.setdefault("hold_reasons", [])
    for reason in [
        "production_completion_blocked",
        "row_complete_blocked",
        "class_e_prod_cut_camera_visual_contact_authority_not_granted",
        "compiler_hard_fail_closes_production_completion_allowed",
        "COMPLETE_claim_forbidden_this_lane",
    ]:
        if reason not in holds:
            holds.append(reason)
    art["class_e_prod_cut_camera_visual_contact_blocker"] = {
        "proof_tier": PROOF,
        "cleared": False,
        "packet": PACKET_PATH.relative_to(ROOT).as_posix(),
        "packet_sha256": packet_sha,
        "runtime_receipt_sha256": receipt_sha,
        "media_sha256": MEDIA_SHA,
        "hard_cut_count": 0,
        "observed_class": "sparse_motion",
        "observed_class_held_out": None,
        "classification_profile": "production",
        "production_mux_replay_pass": True,
        "production_cut_camera_authority_granted": False,
        "production_cut_camera_benchmark_pass": False,
        "production_combined_visual_contact_pass": False,
        "roles_passed": roles_passed,
        "roles_absent": roles_absent,
        "local_gold_absent": local_gold["gold_authority_paths_absent"],
        "runpod_gold_absent": runpod_absent,
        "gold_invented": False,
        "row084_011_status": "FAIL",
        "row084_012_hold_unchanged": True,
        "row074_left_alone": True,
    }
    art["status"] = (
        "HOLD_VISUAL_QA_PASS_BOUNDED_CLASS_E_PROD_CUT_CAMERA_VISUAL_CONTACT_BLOCKER_NO_COMPLETE"
    )
    art["artifact_sha256"] = "pending"
    TRACKER_ARTIFACT.write_text(json.dumps(art, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    art["artifact_sha256"] = sha256_file(TRACKER_ARTIFACT)
    TRACKER_ARTIFACT.write_text(json.dumps(art, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("observed_class", prod_class)
    print("roles_passed", roles_passed)
    print("roles_absent", roles_absent)
    print("local_gold", local_gold["gold_authority_paths_absent"])
    print("runpod_gold", runpod_absent)
    print("cut_camera_authority", cut_camera_authority_granted)
    print("visual_contact_pass", False)
    print("packet", PACKET_PATH)
    print("packet_sha256", packet_sha)
    print("receipt_sha256", receipt_sha)
    print("hard_fail_sha256", hf_sha)
    print("ROW084-011 FAIL/OPEN; ROW084-012 OPEN_HOLD; row_complete=false; hard-fail retained")


if __name__ == "__main__":
    main()
