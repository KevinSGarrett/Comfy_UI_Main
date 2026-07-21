#!/usr/bin/env python3
"""Land Row084 Class E real Comfy generation + VLM. Do not clear 011; leave 074 alone."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
RUNTIME_DIR = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row084/runtime"
    / "runpod_class_e_comfy_gen_20260721T050810Z"
)
PRIOR_READINESS = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_PRODUCTION_READINESS_PACKET_20260721.json"
)
PACKET_PATH = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_COMFY_GENERATION_PACKET_20260721.json"
)
VLM_PATH = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64"
    / "TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_COMFY_GENERATION_VLM_REVIEW_20260721.json"
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
HANDOFF = ROOT / "Plan/00_PROJECT_CONTROL/MAIN_SESSION_INTEGRATION_HANDOFF_CURRENT.md"
HANDOFF_STAMPED = (
    ROOT
    / "Plan/00_PROJECT_CONTROL"
    / "MAIN_SESSION_INTEGRATION_HANDOFF_20260721T0010-0500.md"
)
PROOF = "RUNTIME_COMFY_GENERATION_RECEIPT_WITH_VLM_REVIEW"
PROMPT_ID = "8681ba01-58a4-4a92-92cf-171d5c2daaf3"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
assert HOLD_012.is_file()
assert sha256_file(HOLD_012) == HOLD_012_SHA, "REFUSING: 012 HOLD packet mutated"

receipt_src = RUNTIME_DIR / "class_e_comfy_generation_receipt.json"
receipt = json.loads(receipt_src.read_text(encoding="utf-8"))
assert receipt.get("cleared") is False
assert receipt.get("row_complete") is False
assert receipt.get("production_completion_allowed") is False
assert receipt["generation"]["prompt_id"] == PROMPT_ID
assert receipt["generation"]["completed"] is True

visual_dir = RUNTIME_DIR / "visual_frames"
local_frames = []
for fp in sorted(visual_dir.glob("frame_*.png")):
    local_frames.append(
        {
            "path": fp.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(fp),
            "bytes": fp.stat().st_size,
            "name": fp.name,
        }
    )
assert len(local_frames) >= 1
assert local_frames[0]["sha256"] == "9cfdfe40bb5015746388df6f44919be2db060056be1b51252026ef568280996e"

# normalize receipt paths to local authority
for fr in receipt["generation"]["visual_frames"]:
    name = fr.get("name")
    if name:
        local = visual_dir / name
        if local.is_file():
            fr["local_path"] = local.relative_to(ROOT).as_posix()
            fr["sha256"] = sha256_file(local)
            fr["bytes"] = local.stat().st_size
for rev in receipt.get("vlm", {}).get("reviews", []):
    name = rev.get("name")
    if name:
        local = visual_dir / name
        if local.is_file():
            rev["local_path"] = local.relative_to(ROOT).as_posix()
            rev["sha256"] = sha256_file(local)
    if isinstance(rev.get("parsed"), dict):
        rev["parsed"]["production_completion_allowed"] = False
        rev["parsed"]["row_complete"] = False
receipt["local_runtime_dir"] = RUNTIME_DIR.relative_to(ROOT).as_posix()
receipt["workflow_api_local"] = (RUNTIME_DIR / "workflow.api.json").relative_to(ROOT).as_posix()
receipt["workflow_sha256"] = sha256_file(RUNTIME_DIR / "workflow.api.json")
receipt["history_entry_local"] = (RUNTIME_DIR / "history_entry.json").relative_to(ROOT).as_posix()
receipt["history_entry_sha256"] = sha256_file(RUNTIME_DIR / "history_entry.json")
receipt["submit_response_local"] = (RUNTIME_DIR / "submit_response.json").relative_to(ROOT).as_posix()
receipt["mutation_this_landing"] = "evidence_only_class_e_runpod_comfy_generation_and_vlm"
receipt["csv_sync"] = "deferred_leave_to_serialized_mutator"
receipt["created_at"] = now
receipt_src.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
receipt_sha = sha256_file(receipt_src)

# VLM packet at evidence root
vlm_src = json.loads((RUNTIME_DIR / "vlm_review.json").read_text(encoding="utf-8"))
vlm = {
    "schema_version": "1.0",
    "evidence_id": "TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_COMFY_GENERATION_VLM_REVIEW_20260721",
    "created_at": now,
    "tracker_id": "TRK-W64-084",
    "item_id": "ITEM-W64-084",
    "check_id": "ROW084-011",
    "blocker_class": "E",
    "decision": "HOLD",
    "cleared": False,
    "row_complete": False,
    "production_completion_allowed": False,
    "do_not_clear": ["ROW084-011"],
    "do_not_thrash": ["ROW084-012"],
    "row074_left_alone": True,
    "row084_011_status": "FAIL",
    "status": "VLM_REVIEW_BOUNDED_HOLD",
    "model_used": vlm_src.get("model_used") or receipt["vlm"]["model"],
    "prompt_id": PROMPT_ID,
    "checkpoint": receipt["generation"]["checkpoint"],
    "generation_receipt": receipt_src.relative_to(ROOT).as_posix(),
    "generation_receipt_sha256": receipt_sha,
    "local_frames": local_frames,
    "reviews": receipt["vlm"]["reviews"],
    "vlm_ok_frame_count": sum(1 for r in receipt["vlm"]["reviews"] if r.get("ok")),
    "cursor_vision_corroboration": {
        "method": "cursor_image_read_local_authority_frame",
        "frames_reviewed": 1,
        "subject_consensus": (
            "adult woman in black one-piece swimsuit with side cutouts, "
            "neutral gray studio background"
        ),
        "decode_artifacts_observed": False,
        "matches_vlm_subject": True,
        "production_completion_allowed": False,
        "row_complete": False,
        "note": "Corroborates live Comfy generation + Ollama qwen2.5vl:7b; does not clear Class E.",
    },
    "hold_012_unchanged": {
        "path": HOLD_012.relative_to(ROOT).as_posix(),
        "sha256": HOLD_012_SHA,
        "status": "OPEN_HOLD",
        "thrashed": False,
    },
    "mutation_this_landing": "evidence_only_class_e_runpod_comfy_generation_vlm",
    "csv_sync": "deferred_leave_to_serialized_mutator",
    "safe_next_action": receipt["safe_next_action"],
    "summary": (
        f"Ollama qwen2.5vl:7b reviewed live Comfy generation prompt_id={PROMPT_ID} "
        f"(1/1 frames). ROW084-011 Class E remains OPEN (not cleared); "
        "ROW084-012 HOLD untouched; no COMPLETE."
    ),
}
VLM_PATH.write_text(json.dumps(vlm, indent=2) + "\n", encoding="utf-8")
vlm_sha = sha256_file(VLM_PATH)

comfy = receipt.get("comfy_probe") or {}
gen = receipt["generation"]
packet = {
    "schema_version": "1.0",
    "evidence_id": "TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_COMFY_GENERATION_PACKET_20260721",
    "created_at": now,
    "tracker_id": "TRK-W64-084",
    "item_id": "ITEM-W64-084",
    "check_id": "ROW084-011",
    "blocker_id": "PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED",
    "blocker_class": "E",
    "decision": "HOLD",
    "cleared": False,
    "row_complete": False,
    "production_completion_allowed": False,
    "implementation_completion_claimed": False,
    "product_completion_claimed": False,
    "csv_sync": "deferred_leave_to_serialized_mutator",
    "mutation_this_landing": "evidence_only_class_e_runpod_comfy_generation_and_vlm",
    "proof_tier": PROOF,
    "highest_proof_tier_achieved": PROOF,
    "do_not_clear": ["ROW084-011"],
    "do_not_thrash": ["ROW084-012"],
    "row073_left_alone": True,
    "row074_left_alone": True,
    "pod": receipt["pod"],
    "prior_readiness_packet": PRIOR_READINESS.relative_to(ROOT).as_posix(),
    "runtime_dir": RUNTIME_DIR.relative_to(ROOT).as_posix(),
    "generation_receipt": receipt_src.relative_to(ROOT).as_posix(),
    "generation_receipt_sha256": receipt_sha,
    "prompt_id": PROMPT_ID,
    "checkpoint": gen["checkpoint"],
    "elapsed_seconds": gen["elapsed_seconds"],
    "status_str": gen["status_str"],
    "completed": True,
    "workflow_sha256": receipt["workflow_sha256"],
    "history_entry_sha256": receipt["history_entry_sha256"],
    "visual_frames": local_frames,
    "vlm_review_packet": VLM_PATH.relative_to(ROOT).as_posix(),
    "vlm_review_packet_sha256": vlm_sha,
    "vlm_model": vlm["model_used"],
    "vlm_status": vlm["status"],
    "vlm_ok_frame_count": vlm["vlm_ok_frame_count"],
    "comfy_probe": comfy,
    "remaining_blockers": receipt["remaining_blockers"],
    "hold_012_unchanged": {
        "path": HOLD_012.relative_to(ROOT).as_posix(),
        "exists": True,
        "sha256": HOLD_012_SHA,
        "status": "OPEN_HOLD",
        "thrashed": False,
    },
    "row084_011_status": "FAIL",
    "summary": receipt["summary"],
    "safe_next_action": receipt["safe_next_action"],
    "preservation_boundary": {
        "row073_pcm_left_alone": True,
        "row074_left_alone": True,
        "row075_pid_left_alone": True,
        "tracker_items_csv_writes": False,
        "tip_sha_chain_written": False,
        "comfyui_new_generation_submitted": True,
        "comfyui_generation_is_not_production_mux_authority": True,
        "unrelated_dirty_paths_preserved": True,
        "row084_012_hold_not_thrashed": True,
        "class_e_011_not_cleared": True,
    },
}
PACKET_PATH.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
packet_sha = sha256_file(PACKET_PATH)

# --- CURRENT_DELTA ---
delta = json.loads(DELTA_PATH.read_text(encoding="utf-8"))
for check in delta["checks"]:
    if check.get("check_id") == "ROW084-011":
        assert check.get("status") == "FAIL", "REFUSING to land if 011 already cleared"
        check["status"] = "FAIL"
        check["note"] = (
            "Class E HOLD: production COMPLETE intentionally withheld. Live RunPod Comfy "
            f"generation receipt prompt_id={PROMPT_ID} + Ollama qwen2.5vl:7b VLM "
            f"({PROOF}) recorded; single-image gen is not mux/cut/camera authority — do not clear."
        )
        check["class_e_comfy_generation_packet"] = PACKET_PATH.relative_to(ROOT).as_posix()
        check["class_e_comfy_generation_packet_sha256"] = packet_sha
        check["generation_receipt"] = packet["generation_receipt"]
        check["generation_receipt_sha256"] = receipt_sha
        check["prompt_id"] = PROMPT_ID
        check["vlm_review_packet"] = VLM_PATH.relative_to(ROOT).as_posix()
        check["vlm_review_packet_sha256"] = vlm_sha
        check["proof_tier"] = PROOF
    if check.get("check_id") == "ROW084-012":
        assert check.get("status") == "FAIL"
        assert check.get("hold_packet_sha256") == HOLD_012_SHA

bc = delta["blocker_classification"]["PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED"]
assert bc["status"] == "OPEN"
bc["detail"] = (
    "COMPLETE/row_complete intentionally withheld. Live RunPod Comfy generation receipt "
    f"prompt_id={PROMPT_ID} + Ollama VLM review deepen Class E readiness without granting "
    "production_completion_allowed (single-image gen ≠ production mux/cut/camera authority)."
)
bc["status"] = "OPEN"
bc["comfy_generation_packet"] = PACKET_PATH.relative_to(ROOT).as_posix()
bc["comfy_generation_packet_sha256"] = packet_sha
bc["generation_receipt"] = packet["generation_receipt"]
bc["generation_receipt_sha256"] = receipt_sha
bc["prompt_id"] = PROMPT_ID
bc["readiness_proof_tier"] = PROOF
bc["vlm_review_packet"] = VLM_PATH.relative_to(ROOT).as_posix()
bc["vlm_review_packet_sha256"] = vlm_sha

assert (
    delta["blocker_classification"]["CLOCK_SPAN_REVERSED_PTS_JSON_SCHEMA_NATIVE_ABSENT"]["status"]
    == "OPEN_HOLD"
)
assert (
    delta["blocker_classification"]["CLOCK_SPAN_REVERSED_PTS_JSON_SCHEMA_NATIVE_ABSENT"][
        "hold_packet_sha256"
    ]
    == HOLD_012_SHA
)

delta["updated_at"] = now
delta["classification"] = (
    "ROW084_CLASS_E_RUNPOD_COMFY_GENERATION_RECEIPT_AND_VLM_REVIEW_BOUNDED_NO_COMPLETE"
)
delta["status"] = (
    "HOLD_ROW084_VISUAL_QA_PASS_BOUNDED_CLASS_E_COMFY_GEN_VLM_PROBED_NO_COMPLETE"
)
delta["qa_decision"] = "HOLD"
delta["row_complete"] = False
delta["implementation_completion_claimed"] = False
delta["runtime_completion_claimed"] = False
delta["proof_tier"] = PROOF
delta["highest_proof_tier_achieved"] = PROOF
delta["source_commit"] = "PENDING_LANDING"

fltr = delta.setdefault("focused_local_test_result", {})
fltr["class_e_runpod_comfy_generation_climb"] = {
    "blocker_class": "E",
    "blocker_codes_held": ["PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED"],
    "blocker_codes_cleared": [],
    "cleared": False,
    "comfyui_8188_serving": bool(comfy.get("comfyui_serving")),
    "comfyui_new_generation_submitted": True,
    "prompt_id": PROMPT_ID,
    "checkpoint": gen["checkpoint"],
    "paths_env_sourced": True,
    "proof_tier": PROOF,
    "packet": PACKET_PATH.relative_to(ROOT).as_posix(),
    "packet_sha256": packet_sha,
    "generation_receipt_sha256": receipt_sha,
    "vlm_review_packet": VLM_PATH.relative_to(ROOT).as_posix(),
    "vlm_review_packet_sha256": vlm_sha,
    "vlm_model": vlm["model_used"],
    "vlm_ok_frame_count": packet["vlm_ok_frame_count"],
    "visual_frame_count": len(local_frames),
    "row_complete": False,
    "production_completion_allowed": False,
    "status": "HOLD",
}
fltr["scope_interpretation"] = (
    f"RunPod Comfy live generation prompt_id={PROMPT_ID} "
    f"(realvisxlV50; completed success) + Ollama qwen2.5vl:7b VLM 1/1. "
    "ROW084-011 remains FAIL/OPEN. ROW084-012 Class C OPEN_HOLD unchanged. "
    "Row074 left alone. No COMPLETE/row_complete. RunPod ONLY (no EC2)."
)

hd = delta.setdefault("hold_decision", {})
hd["decision"] = "HOLD_ROW084_CLASS_E_COMFY_GEN_VLM_PROBED_NO_COMPLETE"
hd["reason"] = (
    "Class E RunPod real Comfy generation receipt + VLM deepen only. "
    "ROW084-011 FAIL remains; ROW084-012 Class C OPEN_HOLD not thrashed; "
    "COMPLETE/row_complete withheld; Row074 untouched; EC2 unused."
)
hd["safe_next_action"] = packet["safe_next_action"]

inc = delta.setdefault("increment", {})
inc["kind"] = "class_e_runpod_comfy_generation_receipt_and_vlm"
inc["row_complete"] = False
inc["comfyui_8188_invoked"] = True
inc["prompt_id"] = PROMPT_ID
inc["summary"] = (
    f"Live RunPod Comfy generation prompt_id={PROMPT_ID} with VLM review; "
    "ROW084-011 not cleared; ROW084-012 HOLD not thrashed; no EC2."
)

pb = delta.setdefault("preservation_boundary", {})
pb["row073_pcm_left_alone"] = True
pb["row074_left_alone"] = True
pb["class_e_011_not_cleared"] = True
pb["actual_write_paths"] = sorted(
    set(
        (pb.get("actual_write_paths") or [])
        + [
            PACKET_PATH.relative_to(ROOT).as_posix(),
            VLM_PATH.relative_to(ROOT).as_posix(),
            receipt_src.relative_to(ROOT).as_posix(),
            DELTA_PATH.relative_to(ROOT).as_posix(),
            (RUNTIME_DIR / "visual_frames/frame_01.png").relative_to(ROOT).as_posix(),
            (RUNTIME_DIR / "workflow.api.json").relative_to(ROOT).as_posix(),
            (RUNTIME_DIR / "history_entry.json").relative_to(ROOT).as_posix(),
            (RUNTIME_DIR / "submit_response.json").relative_to(ROOT).as_posix(),
            (RUNTIME_DIR / "comfy_probe.json").relative_to(ROOT).as_posix(),
            (RUNTIME_DIR / "vlm_review.json").relative_to(ROOT).as_posix(),
        ]
    )
)

# tracker artifact tip note
if TRACKER_ARTIFACT.is_file():
    art = json.loads(TRACKER_ARTIFACT.read_text(encoding="utf-8"))
    art["updated_at"] = now
    art["row_complete"] = False
    art["class_e_latest_proof_tier"] = PROOF
    art["class_e_latest_prompt_id"] = PROMPT_ID
    art["class_e_latest_packet"] = PACKET_PATH.relative_to(ROOT).as_posix()
    art["class_e_011_status"] = "FAIL"
    TRACKER_ARTIFACT.write_text(json.dumps(art, indent=2) + "\n", encoding="utf-8")

DELTA_PATH.write_text(json.dumps(delta, indent=2) + "\n", encoding="utf-8")

handoff = f"""# Main Session Integration Handoff — 2026-07-21T00:10-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- Binding: **RunPod ONLY** (`1q4ji0gg1fkhvt`) — NEVER EC2
- Row084 Class E advance: live Comfy generation + VLM on pod
  - `prompt_id={PROMPT_ID}`
  - checkpoint=`realvisxlV50_v50Bakedvae.safetensors`
  - proof_tier=`{PROOF}`
  - packet=`{PACKET_PATH.relative_to(ROOT).as_posix()}`
  - VLM=`{VLM_PATH.relative_to(ROOT).as_posix()}`
- **ROW084-011 Class E remains FAIL/OPEN** (not cleared)
- ROW084-012 Class C OPEN_HOLD unchanged (`{HOLD_012_SHA[:8]}`)
- `row_complete=false`; no COMPLETE; Row074 untouched

## Exact next action

1. Keep ROW084-011 FAIL/OPEN; do not claim COMPLETE from single-image gen receipt.
2. Future Class E clearance still needs production mux/cut/camera/visual authority + compiler hard-fail removal.
3. Leave Row074 alone. RunPod only for Wave64/Comfy/GPU.
"""
HANDOFF.write_text(handoff, encoding="utf-8")
HANDOFF_STAMPED.write_text(handoff, encoding="utf-8")

print("packet", PACKET_PATH.relative_to(ROOT).as_posix(), packet_sha)
print("vlm", VLM_PATH.relative_to(ROOT).as_posix(), vlm_sha)
print("receipt", receipt_sha)
print("prompt_id", PROMPT_ID)
print("proof_tier", PROOF)
print("ROW084-011 FAIL/OPEN retained; cleared=false; row_complete=false")
print("Row074 left alone; HOLD_012 sha unchanged")
