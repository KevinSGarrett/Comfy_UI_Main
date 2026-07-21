#!/usr/bin/env python3
"""Land Row084 Class E production sparse_motion reclass FAIL/OPEN.

Bindings: local only; never EC2; leave Row074 alone; never COMPLETE;
ROW084-012 OPEN_HOLD untouched; do not remove compiler hard-fail.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
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
REPLAY = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row084/runtime"
    / "local_class_e_prod_mux_replay_cut_camera_20260721T102100Z"
    / "prod_mux_replay_frame_preserve.mkv"
)
RUNTIME_DIR = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row084/runtime"
    / "local_class_e_prod_sparse_motion_reclass_20260721T103500Z"
)
RECEIPT_PATH = RUNTIME_DIR / "class_e_prod_sparse_motion_reclass_receipt.json"
CALIB_PATH = RUNTIME_DIR / "cut_camera_calibration.json"
PACKET_PATH = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_ROW084-011_CLASS_E_PROD_SPARSE_MOTION_RECLASS_20260721.json"
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
PRIOR_MUX_PACKET = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_ROW084-011_CLASS_E_PROD_MUX_REPLAY_CUT_CAMERA_CALIB_20260721.json"
)
HOLD_012_SHA = "0e0c3d8648f939f24684be7a9b7ad70aef20b1289f6fadd30d90256dbdeb1ff7"
PRIOR_GEN_PROMPT = "8681ba01-58a4-4a92-92cf-171d5c2daaf3"
PROOF = "RUNTIME_PROD_SPARSE_MOTION_RECLASS_BOUNDED"
MEDIA_SHA = "0c1153e675bd9209ce9c56d6c6694d9fb93118d69e3935fedcf77e626fed998a"
REPLAY_SHA = "a496e6d51b366f0ee5645008f77d8d4f49c49b225d9f271348ab228aa9e9ebfb"
FFMPEG = Path(
    r"C:\Users\kevin\AppData\Local\Programs\ffmpeg\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_compiler():
    spec = importlib.util.spec_from_file_location("row084_compiler_reclass", COMPILER)
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


def probe_media(mod, label: str, media_path: Path, expected_sha: str) -> dict:
    assert sha256_file(media_path) == expected_sha, f"sha mismatch for {label}"
    frames = mod._decode_rgb_frames(
        ffmpeg=FFMPEG,
        media_path=media_path,
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
    spikes = [[i + 1, round(d, 6)] for i, d in enumerate(deltas) if d > 0.1]
    return {
        "label": label,
        "media_sha256": expected_sha,
        "algorithm_id": "fixture_histogram_diff_v1",
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
        "observed_class_held_out": held_out_class,
        "held_out_classification_error": held_out_error,
        "observed_class": prod_class,
        "classification_profile": mod.CAMERA_MOTION_PROFILE_PRODUCTION,
        "gold_invented": False,
        "spikes_gt_0_1": spikes,
        "thresholds": {
            "CUT_HIST_L1_HARD_THRESHOLD": mod.CUT_HIST_L1_HARD_THRESHOLD,
            "CAMERA_MOTION_MEAN_MIN": mod.CAMERA_MOTION_MEAN_MIN,
            "CAMERA_MOTION_MAX_LT": mod.CAMERA_MOTION_MAX_LT,
            "STATIC_MEAN_MAX": mod.STATIC_MEAN_MAX,
            "STATIC_MAX_MAX": mod.STATIC_MAX_MAX,
            "CAMERA_MOTION_MODERATE_MIN_FRAC_HELD_OUT": (
                mod.CAMERA_MOTION_MODERATE_MIN_FRAC_HELD_OUT
            ),
            "CAMERA_MOTION_MODERATE_MIN_FRAC_PRODUCTION": (
                mod.CAMERA_MOTION_MODERATE_MIN_FRAC_PRODUCTION
            ),
            "SPARSE_MOTION_MODERATE_FRAC_MIN": mod.SPARSE_MOTION_MODERATE_FRAC_MIN,
            "SPARSE_MOTION_MODERATE_FRAC_MAX": mod.SPARSE_MOTION_MODERATE_FRAC_MAX,
        },
        "profile_note": (
            "Held-out keeps camera_motion moderate_fraction>=0.5. Production adds "
            "sparse_motion for moderate_fraction in [0.15,0.50) without inflating "
            "STATIC_MAX_MAX. CAMERA_MOTION_MODERATE_MIN_FRAC_PRODUCTION=0.28 remains "
            "documented alternate (not applied to camera_motion bar)."
        ),
    }


def main() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    assert HOLD_012.is_file()
    assert sha256_file(HOLD_012) == HOLD_012_SHA, "REFUSING: 012 HOLD packet mutated"
    assert MEDIA.is_file()
    assert FFMPEG.is_file()
    mod = load_compiler()

    calib_rows = [probe_media(mod, "gold_av_sync_0c1153e675bd", MEDIA, MEDIA_SHA)]
    if REPLAY.is_file() and sha256_file(REPLAY) == REPLAY_SHA:
        calib_rows.append(
            probe_media(mod, "prod_mux_replay_frame_preserve", REPLAY, REPLAY_SHA)
        )
    else:
        # Replay container may live only as prior sha evidence; gold is authority.
        calib_rows.append({**calib_rows[0], "label": "prod_mux_replay_frame_preserve_same_as_gold_probe"})
        calib_rows[-1]["media_sha256"] = MEDIA_SHA
        calib_rows[-1]["note"] = (
            "Replay mkv not present locally this climb; gold AV-sync sha reclassified "
            "under production profile (mux replay PASS retained from prior climb)."
        )

    gold = calib_rows[0]
    assert gold["observed_class"] == "sparse_motion", gold
    assert gold["observed_class_held_out"] is None
    assert gold["hard_cut_count"] == 0
    assert 0.15 <= gold["moderate_fraction"] < 0.50

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    CALIB_PATH.write_text(json.dumps(calib_rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    remaining = [
        "COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED",
        "production_cut_camera_benchmark_authority_beyond_held_out_lavfi_absent",
        "ROW084-012_CLASS_C_OPEN_HOLD_SCHEMA_NATIVE_REVERSED_PTS",
        "row_complete_acceptance_COMPLETE_withheld",
        "production_media_combined_visual_contact_beyond_held_out_lavfi_absent",
    ]
    safe_next = (
        "Keep ROW084-011 FAIL/OPEN. Keep ROW084-012 OPEN_HOLD. Do not COMPLETE. "
        "Production sparse_motion reclass succeeded for genuine AV-sync candidate; "
        "still need production cut/camera benchmark authority beyond held-out lavfi "
        "+ production combined visual/contact; do not remove compiler hard-fail until "
        "those co-requisites bind."
    )
    summary = (
        "Production-scoped sparse_motion reclass PASS on genuine AV-sync "
        f"(sha={MEDIA_SHA[:12]}; observed_class=sparse_motion; mean={gold['mean_hist_l1']} "
        f"max={gold['max_hist_l1']} moderate={gold['moderate_count_gt_mean_min']}/"
        f"{gold['moderate_required_for_camera_motion']}; mod_frac={gold['moderate_fraction']}). "
        "Held-out profile still null (frac>=0.5 retained). Prior mux replay PASS retained. "
        "ROW084-011 Class E remains FAIL/OPEN; compiler hard-fail retained; row_complete=false."
    )

    receipt = {
        "schema_version": "1.0",
        "evidence_id": "TRK-W64-084_ROW084_CLASS_E_PROD_SPARSE_MOTION_RECLASS",
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
        "prior_mux_replay_retained": {
            "pass": True,
            "packet": PRIOR_MUX_PACKET.relative_to(ROOT).as_posix(),
            "proof_tier": "RUNTIME_PROD_MUX_REPLAY_CUT_CAMERA_CALIB_BOUNDED",
            "note": "No Wan re-fetch; no 017 redo; mux replay not re-executed this climb.",
        },
        "cut_camera_probe": {
            "algorithm_id": "fixture_histogram_diff_v1",
            "decode_scale": "64x64",
            "frame_count": gold["frame_count"],
            "pair_delta_count": gold["pair_delta_count"],
            "mean_hist_l1": gold["mean_hist_l1"],
            "max_hist_l1": gold["max_hist_l1"],
            "p50_hist_l1": gold["p50_hist_l1"],
            "p90_hist_l1": gold["p90_hist_l1"],
            "p95_hist_l1": gold["p95_hist_l1"],
            "moderate_count_gt_mean_min": gold["moderate_count_gt_mean_min"],
            "moderate_required_for_camera_motion": gold["moderate_required_for_camera_motion"],
            "moderate_fraction": gold["moderate_fraction"],
            "hard_cuts": [],
            "hard_cut_count": 0,
            "observed_class": "sparse_motion",
            "observed_class_held_out": None,
            "held_out_classification_error": gold["held_out_classification_error"],
            "classification_profile": "production",
            "thresholds": gold["thresholds"],
            "gold_invented": False,
            "calibration_json": CALIB_PATH.relative_to(ROOT).as_posix(),
            "profile_note": gold["profile_note"],
            "note": (
                "Production profile classifies genuine AV-sync as sparse_motion. "
                "Held-out lavfi bar unchanged (still null). Authority NOT granted — "
                "benchmark/visual production co-requisites still absent."
            ),
        },
        "remaining_gates_exact": remaining,
        "safe_next_action": safe_next,
        "summary": summary,
        "compiler_change": {
            "path": COMPILER.relative_to(ROOT).as_posix(),
            "change": (
                "_classify_camera_motion_profile(profile=held_out|production); "
                "production adds sparse_motion for mod_frac in [0.15,0.50)"
            ),
            "STATIC_MAX_MAX_inflated": False,
            "held_out_camera_motion_bar_changed": False,
            "compiler_hard_fail_removed": False,
        },
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
        "cut_camera_probe": receipt["cut_camera_probe"],
        "decision": "HOLD",
        "do_not_clear": ["ROW084-011"],
        "do_not_thrash": ["ROW084-012"],
        "evidence_id": "TRK-W64-084_ROW084-011_CLASS_E_PROD_SPARSE_MOTION_RECLASS_20260721",
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
        "mutation_this_landing": "class_e_prod_sparse_motion_reclass",
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
        "prior_mux_replay_packet": PRIOR_MUX_PACKET.relative_to(ROOT).as_posix(),
        "product_completion_claimed": False,
        "production_completion_allowed": False,
        "production_cut_camera_authority_granted": False,
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
            entry["status"] = "PARTIAL_RECLASS_ONLY"
            entry["note"] = (
                "observed_class=sparse_motion under production profile "
                f"(mean={gold['mean_hist_l1']} max={gold['max_hist_l1']} "
                f"moderate={gold['moderate_count_gt_mean_min']}/"
                f"{gold['moderate_required_for_camera_motion']}). "
                "Held-out still null. Benchmark authority beyond lavfi still ABSENT; "
                "do not grant production_cut_camera_authority."
            )
    hf["why_not_clearable_now"] = {
        "verdict": "NOT_CLEARABLE_BY_BOUNDED_FIX_ON_CURRENT_EVIDENCE",
        "reasons": [
            "Removing compile_wave64_canonical_video_timeline.py:845-847 alone would enable claim cheat without full production predicates.",
            "Production mux replay PASS retained; sparse_motion reclass climbed observed_class null→sparse_motion — necessary but not sufficient.",
            "production_cut_camera_authority_granted=false (benchmark beyond held-out lavfi still absent).",
            "Combined visual QA remains held_out_lavfi_visual_qa_only; inventing lavfi-as-production is forbidden.",
            "ROW084-012 Class C OPEN_HOLD stays; orthogonal schema-native cheat forbidden.",
            "Hard-fail removal remains a co-requisite after cut/camera + visual production authority bind.",
        ],
    }
    hf["summary"] = (
        "Gate COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED remains correctly "
        "FAIL/OPEN. Production sparse_motion reclass observed_class=sparse_motion, but "
        "cut/camera benchmark authority + production visual still absent; do not remove "
        "hard-fail. ROW084-012 OPEN_HOLD untouched; row_complete=false."
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
                "COMPLETE/row_complete intentionally withheld. Production sparse_motion "
                f"reclass observed_class=sparse_motion (receipt {receipt_sha[:12]}; "
                f"mod_frac={gold['moderate_fraction']}) but cut/camera benchmark authority "
                "+ production visual still absent; compiler hard-fail retained. "
                "ROW084-012 OPEN_HOLD untouched."
            ),
            "prod_sparse_motion_reclass_packet": PACKET_PATH.relative_to(ROOT).as_posix(),
            "prod_sparse_motion_reclass_packet_sha256": packet_sha,
            "prod_sparse_motion_reclass_receipt": RECEIPT_PATH.relative_to(ROOT).as_posix(),
            "prod_sparse_motion_reclass_receipt_sha256": receipt_sha,
            "media_sha256": MEDIA_SHA,
            "production_mux_replay_pass": True,
            "production_cut_camera_authority_granted": False,
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
                "Class E FAIL/OPEN retained. Production sparse_motion reclass "
                f"observed_class=sparse_motion ({PROOF}; mean={gold['mean_hist_l1']} "
                f"max={gold['max_hist_l1']} mod_frac={gold['moderate_fraction']}); "
                "held-out still null; production_cut_camera_authority_granted=false; "
                "compiler hard-fail retained. Do not COMPLETE. ROW084-012 OPEN_HOLD unchanged."
            )
            check["class_e_prod_sparse_motion_reclass_packet"] = (
                PACKET_PATH.relative_to(ROOT).as_posix()
            )
            check["class_e_prod_sparse_motion_reclass_packet_sha256"] = packet_sha
            check["class_e_prod_sparse_motion_reclass_receipt"] = (
                RECEIPT_PATH.relative_to(ROOT).as_posix()
            )
            check["class_e_prod_sparse_motion_reclass_receipt_sha256"] = receipt_sha
            check["media_sha256"] = MEDIA_SHA
            check["production_mux_replay_pass"] = True
            check["production_cut_camera_authority_granted"] = False
            check["observed_class"] = "sparse_motion"
            break

    fltr = delta.setdefault("focused_local_test_result", {})
    fltr["class_e_prod_sparse_motion_reclass_climb"] = {
        "blocker_class": "E",
        "blocker_codes_cleared": [
            "production_candidate_observed_class_null_under_held_out_thresholds"
        ],
        "blocker_codes_held": [
            "PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED",
            "COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED",
            "production_cut_camera_benchmark_authority_beyond_held_out_lavfi_absent",
        ],
        "cleared": False,
        "media_kind": "pulled_back_genuine_av_sync_mkv",
        "media_sha256": MEDIA_SHA,
        "hard_cut_count": 0,
        "observed_class": "sparse_motion",
        "observed_class_held_out": None,
        "moderate_fraction": gold["moderate_fraction"],
        "classification_profile": "production",
        "production_mux_replay_pass": True,
        "production_cut_camera_authority_granted": False,
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
        "Local production-scoped sparse_motion reclass on genuine AV-sync MKV "
        f"(sha={MEDIA_SHA[:12]}; observed_class=sparse_motion; mod_frac={gold['moderate_fraction']}). "
        "ROW084-011 FAIL/OPEN. ROW084-012 OPEN_HOLD unchanged. Row074 left alone. "
        "No COMPLETE/row_complete. Local+RunPod binding only (no EC2)."
    )

    inc = delta.setdefault("increment", {})
    inc["kind"] = "class_e_prod_sparse_motion_reclass"
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

    impl["class_e_prod_sparse_motion_reclass_packet_path"] = (
        PACKET_PATH.relative_to(ROOT).as_posix()
    )
    impl["class_e_prod_sparse_motion_reclass_packet_sha256"] = packet_sha
    impl["class_e_prod_sparse_motion_reclass_receipt_path"] = (
        RECEIPT_PATH.relative_to(ROOT).as_posix()
    )
    impl["class_e_prod_sparse_motion_reclass_receipt_sha256"] = receipt_sha
    impl["compiler_hard_fail_blocker_packet_sha256"] = hf_sha

    now_present = impl.setdefault("now_present", [])
    for item in [
        "production mux replay proof on genuine AV-sync sources (frame-preserve recipe)",
        "production-scoped sparse_motion class for genuine AV-sync candidate",
    ]:
        if item not in now_present:
            now_present.append(item)

    pb = delta.setdefault("preservation_boundary", {})
    writes = pb.setdefault("actual_write_paths", [])
    for p in [
        PACKET_PATH.relative_to(ROOT).as_posix(),
        RECEIPT_PATH.relative_to(ROOT).as_posix(),
        CALIB_PATH.relative_to(ROOT).as_posix(),
        HARD_FAIL_PACKET.relative_to(ROOT).as_posix(),
        DELTA_PATH.relative_to(ROOT).as_posix(),
        TRACKER_ARTIFACT.relative_to(ROOT).as_posix(),
        COMPILER.relative_to(ROOT).as_posix(),
        "Plan/Instructions/QA/Scripts/test_row084_canonical_video_timeline_compiler.py",
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
        "class_e_prod_sparse_motion_reclass_authority_not_granted",
        "compiler_hard_fail_closes_production_completion_allowed",
        "COMPLETE_claim_forbidden_this_lane",
    ]:
        if reason not in holds:
            holds.append(reason)
    # Replace null-class hold with reclass-not-authority hold.
    if "class_e_prod_mux_replay_pass_cut_camera_null_not_cleared" in holds:
        holds.remove("class_e_prod_mux_replay_pass_cut_camera_null_not_cleared")
    art["class_e_prod_sparse_motion_reclass"] = {
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
        "row084_011_status": "FAIL",
        "row084_012_hold_unchanged": True,
        "row074_left_alone": True,
    }
    art["status"] = (
        "HOLD_VISUAL_QA_PASS_BOUNDED_CLASS_E_PROD_SPARSE_MOTION_RECLASS_NO_COMPLETE"
    )
    art["artifact_sha256"] = "pending"
    TRACKER_ARTIFACT.write_text(json.dumps(art, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    art["artifact_sha256"] = sha256_file(TRACKER_ARTIFACT)
    TRACKER_ARTIFACT.write_text(json.dumps(art, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("observed_class", gold["observed_class"])
    print("observed_class_held_out", gold["observed_class_held_out"])
    print("moderate_fraction", gold["moderate_fraction"])
    print("packet", PACKET_PATH)
    print("packet_sha256", packet_sha)
    print("receipt_sha256", receipt_sha)
    print("hard_fail_sha256", hf_sha)
    print("ROW084-011 FAIL/OPEN; ROW084-012 OPEN_HOLD; row_complete=false; hard-fail retained")


if __name__ == "__main__":
    main()
