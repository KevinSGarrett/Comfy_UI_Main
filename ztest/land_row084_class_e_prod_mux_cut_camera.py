#!/usr/bin/env python3
"""Land Row084 Class E production-media cut/camera/mux probe. Do not clear 011; leave 074 alone."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
RUNTIME_DIR = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row084/runtime"
    / "runpod_class_e_prod_mux_cut_camera_20260721T101712Z"
)
RECEIPT_PATH = RUNTIME_DIR / "class_e_prod_media_cut_camera_mux_receipt.json"
PACKET_PATH = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_PROD_MEDIA_CUT_CAMERA_MUX_PROBE_20260721.json"
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
HOLD_012_SHA = "0e0c3d8648f939f24684be7a9b7ad70aef20b1289f6fadd30d90256dbdeb1ff7"
PRIOR_GEN_PROMPT = "8681ba01-58a4-4a92-92cf-171d5c2daaf3"
PROOF = "RUNTIME_PROD_MEDIA_CUT_CAMERA_MUX_PROBE_BOUNDED"
MEDIA_SHA = "0c1153e675bd9209ce9c56d6c6694d9fb93118d69e3935fedcf77e626fed998a"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
assert HOLD_012.is_file()
assert sha256_file(HOLD_012) == HOLD_012_SHA, "REFUSING: 012 HOLD packet mutated"

receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
assert receipt.get("cleared") is False
assert receipt.get("row_complete") is False
assert receipt.get("production_completion_allowed") is False
assert receipt.get("production_mux_replay_pass") is False
assert receipt.get("production_cut_camera_authority_granted") is False
assert receipt.get("comfyui_8188_invoked_for_new_generation") is False
assert receipt["media"]["sha256"] == MEDIA_SHA
assert receipt["cut_camera_probe"]["gold_invented"] is False
assert receipt["pod"]["id"] == "1q4ji0gg1fkhvt"
receipt_sha = sha256_file(RECEIPT_PATH)

packet = {
    "blocker_class": "E",
    "blocker_id": "PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED",
    "check_id": "ROW084-011",
    "cleared": False,
    "comfy_probe": receipt["comfy_probe"],
    "created_at": now,
    "decision": "HOLD",
    "do_not_clear": ["ROW084-011"],
    "do_not_thrash": ["ROW084-012"],
    "evidence_id": "TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_PROD_MEDIA_CUT_CAMERA_MUX_PROBE_20260721",
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
    "mutation_this_landing": "evidence_only_class_e_runpod_prod_media_cut_camera_mux_probe",
    "pod": {
        "id": "1q4ji0gg1fkhvt",
        "name": "hyperreal-flux",
        "public_ip": "195.26.233.100",
        "ssh_port": 52077,
    },
    "preservation_boundary": {
        "class_e_011_not_cleared": True,
        "comfyui_new_generation_not_submitted": True,
        "gold_not_invented": True,
        "prior_comfy_gen_prompt_id_retained": PRIOR_GEN_PROMPT,
        "row073_pcm_left_alone": True,
        "row074_left_alone": True,
        "row075_pid_left_alone": True,
        "row084_012_hold_not_thrashed": True,
        "unrelated_dirty_paths_preserved": True,
    },
    "prior_comfy_generation_prompt_id": PRIOR_GEN_PROMPT,
    "product_completion_claimed": False,
    "production_completion_allowed": False,
    "production_cut_camera_authority_granted": False,
    "production_mux_replay_pass": False,
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
    "summary": (
        "RunPod genuine AV-sync MKV cut/camera/mux identity probe on "
        f"sha256={MEDIA_SHA[:12]}…; frames=49 hard_cuts=0 observed_class=null "
        f"({receipt['cut_camera_probe']['classification_error']}). "
        "ROW084-011 Class E remains OPEN (not cleared); ROW084-012 HOLD untouched; "
        "no COMPLETE/row_complete; prior Comfy gen receipt retained as non-authority; "
        "Row074 left alone; no new :8188 generation."
    ),
    "tracker_id": "TRK-W64-084",
    "cut_camera_probe": receipt["cut_camera_probe"],
    "mux_identity": receipt["mux_identity"],
    "media": receipt["media"],
}
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
            "COMPLETE/row_complete intentionally withheld. RunPod production-candidate "
            f"AV-sync MKV cut/camera/mux identity probe (receipt {receipt_sha[:12]}) "
            "deepens Class E without granting production_completion_allowed "
            "(unclassified camera profile; 0 hard cuts; mux identity ≠ mux replay; "
            "compiler hard-fails production_completion_allowed). Prior Comfy gen "
            f"prompt_id={PRIOR_GEN_PROMPT} retained as non-authority."
        ),
        "prod_media_cut_camera_mux_packet": PACKET_PATH.relative_to(ROOT).as_posix(),
        "prod_media_cut_camera_mux_packet_sha256": packet_sha,
        "prod_media_cut_camera_mux_receipt": RECEIPT_PATH.relative_to(ROOT).as_posix(),
        "prod_media_cut_camera_mux_receipt_sha256": receipt_sha,
        "media_sha256": MEDIA_SHA,
        "readiness_proof_tier": PROOF,
        "prompt_id": PRIOR_GEN_PROMPT,
    }
)

for check in delta.get("checks", []):
    if check.get("check_id") == "ROW084-011":
        check["status"] = "FAIL"
        check["proof_tier"] = PROOF
        check["note"] = (
            "Class E HOLD: production COMPLETE intentionally withheld. RunPod genuine "
            f"AV-sync MKV cut/camera/mux probe ({PROOF}); observed_class=null "
            "hard_cuts=0; mux identity only; compiler hard-fail retained. Prior Comfy "
            f"gen prompt_id={PRIOR_GEN_PROMPT} is not mux/cut/camera authority — do not clear."
        )
        check["class_e_prod_media_cut_camera_mux_packet"] = PACKET_PATH.relative_to(ROOT).as_posix()
        check["class_e_prod_media_cut_camera_mux_packet_sha256"] = packet_sha
        check["class_e_prod_media_cut_camera_mux_receipt"] = RECEIPT_PATH.relative_to(ROOT).as_posix()
        check["class_e_prod_media_cut_camera_mux_receipt_sha256"] = receipt_sha
        check["media_sha256"] = MEDIA_SHA
        break

fltr = delta.setdefault("focused_local_test_result", {})
fltr["class_e_runpod_prod_media_cut_camera_mux_climb"] = {
    "blocker_class": "E",
    "blocker_codes_cleared": [],
    "blocker_codes_held": [
        "PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED",
        "COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED",
    ],
    "cleared": False,
    "comfyui_8188_serving": True,
    "comfyui_new_generation_submitted": False,
    "media_kind": "pulled_back_genuine_av_sync_mkv",
    "media_sha256": MEDIA_SHA,
    "hard_cut_count": 0,
    "observed_class": None,
    "classification_error": receipt["cut_camera_probe"]["classification_error"],
    "mux_identity_va_pair": True,
    "production_mux_replay_pass": False,
    "production_cut_camera_authority_granted": False,
    "packet": PACKET_PATH.relative_to(ROOT).as_posix(),
    "packet_sha256": packet_sha,
    "runtime_receipt_sha256": receipt_sha,
    "production_completion_allowed": False,
    "proof_tier": PROOF,
    "row_complete": False,
    "status": "HOLD",
    "prior_comfy_gen_prompt_id_retained_non_authority": PRIOR_GEN_PROMPT,
}
fltr["scope_interpretation"] = (
    "RunPod production-candidate AV-sync MKV cut/camera/mux identity probe "
    f"(sha={MEDIA_SHA[:12]}; frames=49; hard_cuts=0; class=null). "
    f"Prior Comfy gen prompt_id={PRIOR_GEN_PROMPT} retained non-authority. "
    "ROW084-011 remains FAIL/OPEN. ROW084-012 Class C OPEN_HOLD unchanged. "
    "Row074 left alone. No COMPLETE/row_complete. RunPod ONLY (no EC2)."
)

inc = delta.setdefault("increment", {})
inc["kind"] = "class_e_runpod_prod_media_cut_camera_mux_probe"
inc["comfyui_8188_invoked"] = False
inc["runtime_media_decode_invoked"] = True
inc["row_complete"] = False
inc["prompt_id"] = PRIOR_GEN_PROMPT
inc["summary"] = packet["summary"]

impl = delta.setdefault("implementation", {})
still = impl.setdefault("still_absent", [])
for item in [
    "production mux replay proof",
    "production cut/camera/benchmark authority beyond held-out lavfi",
    "compiler production_completion_allowed hard fail-close removal",
    "production-candidate media camera class calibration (unclassified under held-out thresholds)",
]:
    if item not in still:
        still.append(item)

impl["class_e_runpod_prod_media_cut_camera_mux_packet_path"] = PACKET_PATH.relative_to(ROOT).as_posix()
impl["class_e_runpod_prod_media_cut_camera_mux_packet_sha256"] = packet_sha
impl["class_e_runpod_prod_media_cut_camera_mux_receipt_path"] = RECEIPT_PATH.relative_to(ROOT).as_posix()
impl["class_e_runpod_prod_media_cut_camera_mux_receipt_sha256"] = receipt_sha

pb = delta.setdefault("preservation_boundary", {})
writes = pb.setdefault("actual_write_paths", [])
for p in [
    PACKET_PATH.relative_to(ROOT).as_posix(),
    RECEIPT_PATH.relative_to(ROOT).as_posix(),
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
holds = art.setdefault("hold_reasons", [])
for reason in [
    "production_completion_blocked",
    "row_complete_blocked",
    "class_e_prod_media_cut_camera_mux_probed_not_cleared",
    "compiler_hard_fail_closes_production_completion_allowed",
    "COMPLETE_claim_forbidden_this_lane",
]:
    if reason not in holds:
        holds.append(reason)
art["class_e_runpod_prod_media_cut_camera_mux"] = {
    "proof_tier": PROOF,
    "cleared": False,
    "packet": PACKET_PATH.relative_to(ROOT).as_posix(),
    "packet_sha256": packet_sha,
    "runtime_receipt_sha256": receipt_sha,
    "media_sha256": MEDIA_SHA,
    "hard_cut_count": 0,
    "observed_class": None,
    "production_mux_replay_pass": False,
    "production_cut_camera_authority_granted": False,
    "row084_011_status": "FAIL",
    "row084_012_hold_unchanged": True,
    "row074_left_alone": True,
}
art["status"] = (
    "HOLD_VISUAL_QA_PASS_BOUNDED_CLASS_E_PROD_MEDIA_CUT_CAMERA_MUX_PROBED_NO_COMPLETE"
)
art["artifact_sha256"] = "pending"
TRACKER_ARTIFACT.write_text(json.dumps(art, indent=2, sort_keys=True) + "\n", encoding="utf-8")
art["artifact_sha256"] = sha256_file(TRACKER_ARTIFACT)
TRACKER_ARTIFACT.write_text(json.dumps(art, indent=2, sort_keys=True) + "\n", encoding="utf-8")

print("packet", PACKET_PATH)
print("packet_sha256", packet_sha)
print("receipt_sha256", receipt_sha)
print("ROW084-011 FAIL/OPEN; ROW084-012 OPEN_HOLD; row_complete=false")
print("Row074 left alone; no COMPLETE from gen receipt")
