#!/usr/bin/env python3
"""Land Row084 Class E production mux-replay + cut/camera calibration FAIL/OPEN.

Bindings: local tools (sources on disk); never EC2; leave Row074 alone; never COMPLETE;
ROW084-012 OPEN_HOLD untouched; do not remove compiler hard-fail.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
RUNTIME_DIR = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row084/runtime"
    / "local_class_e_prod_mux_replay_cut_camera_20260721T102100Z"
)
RECEIPT_PATH = RUNTIME_DIR / "class_e_prod_mux_replay_cut_camera_calib_receipt.json"
CALIB_PATH = RUNTIME_DIR / "cut_camera_calibration.json"
PACKET_PATH = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_ROW084-011_CLASS_E_PROD_MUX_REPLAY_CUT_CAMERA_CALIB_20260721.json"
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
HOLD_012_SHA = "0e0c3d8648f939f24684be7a9b7ad70aef20b1289f6fadd30d90256dbdeb1ff7"
PRIOR_GEN_PROMPT = "8681ba01-58a4-4a92-92cf-171d5c2daaf3"
PROOF = "RUNTIME_PROD_MUX_REPLAY_CUT_CAMERA_CALIB_BOUNDED"
MEDIA_SHA = "0c1153e675bd9209ce9c56d6c6694d9fb93118d69e3935fedcf77e626fed998a"
SOURCE_VIDEO_SHA = "671c3b064effbc1081ffc11f22d910402bbd229eebb0d2bd49c8a2b280db27d5"
SOURCE_AUDIO_SHA = "e5965ebb9eb620513ad4d6d693b2c122d1038d3398e2139c518df0fc7131b1a3"
REPLAY_SHA = "a496e6d51b366f0ee5645008f77d8d4f49c49b225d9f271348ab228aa9e9ebfb"
VIDEO_DECODE_SHA16 = "b372ba478a4ebec3"
SHORTEST_FAIL_SHA = "70edae9d1f88cb473b421142a130c804b5c99cc86f002bc5ad7ec15af0e7e003"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
assert HOLD_012.is_file()
assert sha256_file(HOLD_012) == HOLD_012_SHA, "REFUSING: 012 HOLD packet mutated"
assert CALIB_PATH.is_file()
calib = json.loads(CALIB_PATH.read_text(encoding="utf-8"))
gold_calib = next(c for c in calib if c["label"].startswith("gold_av_sync"))
assert gold_calib["observed_class"] is None
assert gold_calib["media_sha256"] == MEDIA_SHA
assert gold_calib["hard_cut_count"] == 0

RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

receipt = {
    "schema_version": "1.0",
    "evidence_id": "TRK-W64-084_ROW084_CLASS_E_PROD_MUX_REPLAY_CUT_CAMERA_CALIB",
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
    "pod_binding_note": "Candidate also present on RunPod 1q4ji0gg1fkhvt; this climb executed locally against pulled-back sources (no EC2).",
    "ffmpeg_version_line": (
        "ffmpeg version 8.1.2-full_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers"
    ),
    "media": {
        "kind": "pulled_back_genuine_av_sync_mkv",
        "path": (
            "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
            "w64_genuine_av_sync_frame_aligned_20260714T202000-0500/"
            "strict_sync_mux_ffv1_pcm16_mono_frame_aligned.mkv"
        ),
        "bytes": 2073838,
        "sha256": MEDIA_SHA,
        "expected_sha256": MEDIA_SHA,
        "sha256_matches_prior_probe": True,
    },
    "sources": {
        "video_path": (
            "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
            "w64_genuine_audio_chain_20260714T163400-0500/source_video_ffv1.mkv"
        ),
        "video_sha256": SOURCE_VIDEO_SHA,
        "audio_path": (
            "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
            "w64_genuine_audio_chain_20260714T163400-0500/strict_sync_mix_mono_16k.wav"
        ),
        "audio_sha256": SOURCE_AUDIO_SHA,
    },
    "mux_replay": {
        "identity_probe_is_not_replay": True,
        "recipe": (
            "ffmpeg -y -i source_video_ffv1.mkv -i strict_sync_mix_mono_16k.wav "
            "-map 0:v:0 -map 1:a:0 -c:v copy -c:a pcm_s16le -ar 16000 -ac 1 "
            "-frames:v 49 -af apad -shortest <out.mkv>"
        ),
        "negative_control_shortest_only": {
            "recipe": "same without -frames:v 49 -af apad (plain -shortest)",
            "video_frames": 48,
            "duration_seconds": 2.04,
            "mux_sha256": SHORTEST_FAIL_SHA,
            "passed": False,
            "note": "Reproduces Row030 defective 48/49 drop; proves identity≠replay and why frame-preserve recipe is required.",
        },
        "frame_preserve_replay": {
            "video_frames": 49,
            "audio_samples": 32640,
            "audio_sample_rate_hz": 16000,
            "duration_seconds": 2.041,
            "expected_video_frames": 49,
            "expected_audio_samples": 32640,
            "expected_duration_seconds": 2.041,
            "frame_count_matched": True,
            "sample_count_matched": True,
            "duration_within_tolerance": True,
            "mux_sha256": REPLAY_SHA,
            "mux_byte_length": 2073792,
            "container_sha_equals_gold": False,
            "video_decode_rgb24_sha256_prefix16_matches_source_and_gold": VIDEO_DECODE_SHA16,
            "passed": True,
            "note": (
                "Production mux replay PASS on clock+decode-hash criteria. "
                "Container sha differs from gold (metadata); stream content matches."
            ),
        },
        "production_mux_replay_pass": True,
        "proof_tier_note": "Non-lavfi source remux verified; not held-out lavfi authority.",
    },
    "cut_camera_probe": {
        "algorithm_id": "fixture_histogram_diff_v1",
        "decode_scale": "64x64",
        "frame_count": gold_calib["frame_count"],
        "pair_delta_count": gold_calib["pair_delta_count"],
        "mean_hist_l1": gold_calib["mean_hist_l1"],
        "max_hist_l1": gold_calib["max_hist_l1"],
        "p50_hist_l1": gold_calib["p50_hist_l1"],
        "p90_hist_l1": gold_calib["p90_hist_l1"],
        "p95_hist_l1": gold_calib["p95_hist_l1"],
        "moderate_count_gt_mean_min": gold_calib["moderate_count_gt_mean_min"],
        "moderate_required_for_camera_motion": gold_calib["moderate_required_for_camera_motion"],
        "moderate_fraction": gold_calib["moderate_fraction"],
        "hard_cuts": [],
        "hard_cut_count": 0,
        "observed_class": None,
        "classification_error": gold_calib["classification_error"],
        "thresholds": gold_calib["thresholds"],
        "gold_invented": False,
        "calibration_gap": gold_calib["calibration_gap"],
        "calibration_json": CALIB_PATH.relative_to(ROOT).as_posix(),
        "note": (
            "Existing Wave64 fixture_histogram_diff_v1 thresholds cannot classify "
            "genuine AV-sync candidate; observed_class remains null. Authority NOT granted."
        ),
    },
    "remaining_gates_exact": [
        "COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED",
        "production_cut_camera_benchmark_authority_beyond_held_out_lavfi_absent",
        "production_candidate_observed_class_null_under_held_out_thresholds",
        "ROW084-012_CLASS_C_OPEN_HOLD_SCHEMA_NATIVE_REVERSED_PTS",
        "row_complete_acceptance_COMPLETE_withheld",
        "production_media_combined_visual_contact_beyond_held_out_lavfi_absent",
    ],
    "safe_next_action": (
        "Keep ROW084-011 FAIL/OPEN. Keep ROW084-012 OPEN_HOLD. Do not COMPLETE. "
        "Mux replay climbed to PASS; cut/camera still blocked on null observed_class. "
        "Next: implement sparse_motion class or production CAMERA_MOTION_MODERATE_MIN_FRAC "
        "profile (held-out keep 0.5), then re-classify genuine candidate; do not remove "
        "compiler hard-fail until cut/camera + visual production authority also bind."
    ),
    "summary": (
        "Local production mux replay PASS on genuine AV-sync sources "
        f"(sha gold={MEDIA_SHA[:12]}; replay container={REPLAY_SHA[:12]}; "
        "49f/32640smp/2.041s; decode-hash match). Cut/camera observed_class=null "
        "(mean=0.0297 max=0.3770 moderate=14/24). ROW084-011 Class E remains FAIL/OPEN; "
        "compiler hard-fail retained; row_complete=false."
    ),
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
    "evidence_id": "TRK-W64-084_ROW084-011_CLASS_E_PROD_MUX_REPLAY_CUT_CAMERA_CALIB_20260721",
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
    "mux_replay": receipt["mux_replay"],
    "mutation_this_landing": "evidence_only_class_e_prod_mux_replay_cut_camera_calib",
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
    "product_completion_claimed": False,
    "production_completion_allowed": False,
    "production_cut_camera_authority_granted": False,
    "production_mux_replay_pass": True,
    "proof_tier": PROOF,
    "remaining_blockers": list(receipt["remaining_gates_exact"]),
    "row073_left_alone": True,
    "row074_left_alone": True,
    "row084_011_status": "FAIL",
    "row_complete": False,
    "runtime_dir": RUNTIME_DIR.relative_to(ROOT).as_posix(),
    "runtime_receipt": RECEIPT_PATH.relative_to(ROOT).as_posix(),
    "runtime_receipt_sha256": receipt_sha,
    "safe_next_action": receipt["safe_next_action"],
    "schema_version": "1.0",
    "sources": receipt["sources"],
    "summary": receipt["summary"],
    "tracker_id": "TRK-W64-084",
}
PACKET_PATH.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
packet_sha = sha256_file(PACKET_PATH)

# Refresh hard-fail blocker packet: mux replay now present; still not clearable.
hf = json.loads(HARD_FAIL_PACKET.read_text(encoding="utf-8"))
hf["updated_at"] = now
hf["compiler_hard_fail_clearable_on_current_evidence"] = False
hf["production_mux_replay_pass"] = True
hf["production_cut_camera_authority_granted"] = False
hf["row_complete"] = False
hf["related_climb_packet"] = PACKET_PATH.relative_to(ROOT).as_posix()
hf["related_climb_packet_sha256"] = packet_sha
for entry in hf.get("missing_artifact_authority", []):
    if not isinstance(entry, dict):
        continue
    if entry.get("id") == "production_mux_replay_proof":
        entry["status"] = "SATISFIED_THIS_CLIMB"
        entry["note"] = (
            "Local frame-preserve remux from genuine sources passed "
            "49f/32640smp/2.041s + decode-hash match; container sha≠gold. "
            "Identity probe alone remains non-authority."
        )
    if entry.get("id") == "production_cut_camera_benchmark_authority":
        entry["status"] = "ABSENT"
        entry["note"] = (
            "observed_class=null under held-out thresholds "
            "(mean=0.0297 max=0.3770 moderate=14/24). Recommend sparse_motion class "
            "or production CAMERA_MOTION_MODERATE_MIN_FRAC≈0.28; do not relabel lavfi."
        )
hf["why_not_clearable_now"] = {
    "verdict": "NOT_CLEARABLE_BY_BOUNDED_FIX_ON_CURRENT_EVIDENCE",
    "reasons": [
        "Removing compile_wave64_canonical_video_timeline.py:845-847 alone would enable claim cheat without full production predicates.",
        "Production mux replay now PASS on genuine AV-sync sources (frame-preserve recipe; 49f/32640smp/2.041s; decode-hash match) — necessary but not sufficient.",
        "Cut/camera observed_class remains null (mean=0.0297 max=0.3770 moderate=14/24); production_cut_camera_authority_granted=false.",
        "Combined visual QA remains held_out_lavfi_visual_qa_only; inventing lavfi-as-production is forbidden.",
        "ROW084-012 Class C OPEN_HOLD stays; orthogonal schema-native cheat forbidden.",
        "Hard-fail removal remains a co-requisite after cut/camera + visual production authority bind — not a solo unlock after mux replay alone.",
    ],
}
hf["summary"] = (
    "Gate COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED remains correctly "
    "FAIL/OPEN. Production mux replay now PASS on genuine AV-sync sources, but "
    "cut/camera observed_class=null and production visual authority still absent; "
    "do not remove hard-fail. ROW084-012 OPEN_HOLD untouched; row_complete=false."
)
hf["safe_next_action"] = receipt["safe_next_action"]
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
            "COMPLETE/row_complete intentionally withheld. Production mux replay PASS "
            f"on genuine AV-sync sources (receipt {receipt_sha[:12]}; "
            "49f/32640smp/2.041s decode-hash match) but cut/camera observed_class=null "
            "and compiler hard-fail retained. ROW084-012 OPEN_HOLD untouched."
        ),
        "prod_mux_replay_cut_camera_calib_packet": PACKET_PATH.relative_to(ROOT).as_posix(),
        "prod_mux_replay_cut_camera_calib_packet_sha256": packet_sha,
        "prod_mux_replay_cut_camera_calib_receipt": RECEIPT_PATH.relative_to(ROOT).as_posix(),
        "prod_mux_replay_cut_camera_calib_receipt_sha256": receipt_sha,
        "media_sha256": MEDIA_SHA,
        "production_mux_replay_pass": True,
        "production_cut_camera_authority_granted": False,
        "observed_class": None,
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
            "Class E FAIL/OPEN retained. Production mux replay PASS on genuine AV-sync "
            f"sources ({PROOF}); cut/camera observed_class=null "
            "(mean=0.0297 max=0.3770 moderate=14/24); compiler hard-fail retained. "
            "Do not COMPLETE. ROW084-012 OPEN_HOLD unchanged."
        )
        check["class_e_prod_mux_replay_cut_camera_calib_packet"] = (
            PACKET_PATH.relative_to(ROOT).as_posix()
        )
        check["class_e_prod_mux_replay_cut_camera_calib_packet_sha256"] = packet_sha
        check["class_e_prod_mux_replay_cut_camera_calib_receipt"] = (
            RECEIPT_PATH.relative_to(ROOT).as_posix()
        )
        check["class_e_prod_mux_replay_cut_camera_calib_receipt_sha256"] = receipt_sha
        check["media_sha256"] = MEDIA_SHA
        check["production_mux_replay_pass"] = True
        check["production_cut_camera_authority_granted"] = False
        check["observed_class"] = None
        break

fltr = delta.setdefault("focused_local_test_result", {})
fltr["class_e_prod_mux_replay_cut_camera_calib_climb"] = {
    "blocker_class": "E",
    "blocker_codes_cleared": ["production_mux_replay_proof_absent"],
    "blocker_codes_held": [
        "PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED",
        "COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED",
        "production_cut_camera_benchmark_authority_beyond_held_out_lavfi_absent",
        "production_candidate_observed_class_null_under_held_out_thresholds",
    ],
    "cleared": False,
    "media_kind": "pulled_back_genuine_av_sync_mkv",
    "media_sha256": MEDIA_SHA,
    "hard_cut_count": 0,
    "observed_class": None,
    "classification_error": gold_calib["classification_error"],
    "moderate_fraction": gold_calib["moderate_fraction"],
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
    "Local production mux replay + cut/camera calibration on genuine AV-sync MKV "
    f"(sha={MEDIA_SHA[:12]}; mux_replay=PASS; observed_class=null; mod_frac=0.292). "
    "ROW084-011 FAIL/OPEN. ROW084-012 OPEN_HOLD unchanged. Row074 left alone. "
    "No COMPLETE/row_complete. Local+RunPod binding only (no EC2)."
)

inc = delta.setdefault("increment", {})
inc["kind"] = "class_e_prod_mux_replay_cut_camera_calib"
inc["comfyui_8188_invoked"] = False
inc["runtime_media_decode_invoked"] = True
inc["ffmpeg_mux_replay_executed"] = True
inc["row_complete"] = False
inc["prompt_id"] = PRIOR_GEN_PROMPT
inc["summary"] = packet["summary"]

impl = delta.setdefault("implementation", {})
still = impl.setdefault("still_absent", [])
# Remove satisfied mux-replay absence; keep cut/camera + hard-fail
still[:] = [
    s
    for s in still
    if s
    not in {
        "production mux replay proof",
        "production-candidate media camera class calibration (unclassified under held-out thresholds)",
    }
]
for item in [
    "production cut/camera/benchmark authority beyond held-out lavfi",
    "production-candidate observed_class null (need sparse_motion or production moderate_frac≈0.28)",
    "compiler production_completion_allowed hard fail-close removal",
    "production media combined visual/contact beyond held-out lavfi",
]:
    if item not in still:
        still.append(item)

impl["class_e_prod_mux_replay_cut_camera_calib_packet_path"] = (
    PACKET_PATH.relative_to(ROOT).as_posix()
)
impl["class_e_prod_mux_replay_cut_camera_calib_packet_sha256"] = packet_sha
impl["class_e_prod_mux_replay_cut_camera_calib_receipt_path"] = (
    RECEIPT_PATH.relative_to(ROOT).as_posix()
)
impl["class_e_prod_mux_replay_cut_camera_calib_receipt_sha256"] = receipt_sha
impl["compiler_hard_fail_blocker_packet_sha256"] = hf_sha

now_present = impl.setdefault("now_present", [])
for item in [
    "production mux replay proof on genuine AV-sync sources (frame-preserve recipe)",
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
    "class_e_prod_mux_replay_pass_cut_camera_null_not_cleared",
    "compiler_hard_fail_closes_production_completion_allowed",
    "COMPLETE_claim_forbidden_this_lane",
]:
    if reason not in holds:
        holds.append(reason)
art["class_e_prod_mux_replay_cut_camera_calib"] = {
    "proof_tier": PROOF,
    "cleared": False,
    "packet": PACKET_PATH.relative_to(ROOT).as_posix(),
    "packet_sha256": packet_sha,
    "runtime_receipt_sha256": receipt_sha,
    "media_sha256": MEDIA_SHA,
    "hard_cut_count": 0,
    "observed_class": None,
    "production_mux_replay_pass": True,
    "production_cut_camera_authority_granted": False,
    "row084_011_status": "FAIL",
    "row084_012_hold_unchanged": True,
    "row074_left_alone": True,
}
art["status"] = (
    "HOLD_VISUAL_QA_PASS_BOUNDED_CLASS_E_PROD_MUX_REPLAY_PASS_CUT_CAMERA_NULL_NO_COMPLETE"
)
art["artifact_sha256"] = "pending"
TRACKER_ARTIFACT.write_text(json.dumps(art, indent=2, sort_keys=True) + "\n", encoding="utf-8")
art["artifact_sha256"] = sha256_file(TRACKER_ARTIFACT)
TRACKER_ARTIFACT.write_text(json.dumps(art, indent=2, sort_keys=True) + "\n", encoding="utf-8")

print("packet", PACKET_PATH)
print("packet_sha256", packet_sha)
print("receipt_sha256", receipt_sha)
print("hard_fail_sha256", hf_sha)
print("production_mux_replay_pass=true; observed_class=null; ROW084-011 FAIL/OPEN")
print("ROW084-012 OPEN_HOLD; row_complete=false; hard-fail retained")
