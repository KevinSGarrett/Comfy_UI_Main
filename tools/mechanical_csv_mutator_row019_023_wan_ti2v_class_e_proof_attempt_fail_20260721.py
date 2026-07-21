#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 Wan TI2V Class E proof attempt FAIL (bytes gate)."""
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
STAMP = "20260721T011000-0500"
EVIDENCE = f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_E_PROOF_ATTEMPT_FAIL_{STAMP}.json"
EVIDENCE_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    f"TRK-W64-019_023_WAN_TI2V_CLASS_E_PROOF_ATTEMPT_FAIL_{STAMP}.json"
)
CURRENT = f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
CURRENT_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
)
RECEIPT = (
    f"{EVID}/fixtures/row019_023/runtime/runpod_wan_ti2v_class_e_20260721T055801Z/"
    "generation_receipt.json"
)
PULLBACK_DIR = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "runpod_wan_ti2v_class_e_20260721T055801Z"
)
PULLBACK_MP4 = (
    f"{PULLBACK_DIR}/w64_019_023_runpod_wan_ti2v_class_e_20260721T055801Z_00001_.mp4"
)
POLICY = (
    "Plan/07_IMPLEMENTATION/scripts/"
    "validate_wave64_wan_ti2v_class_e_runtime_proof_claim.py"
)
POLICY_RESULT = (
    f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_E_PROOF_ATTEMPT_FAIL_POLICY_{STAMP}.json"
)

PROMPT_ID = "19c76cc5-a107-4b56-892a-29c9918316fb"
ARTIFACT_SHA = "89c7f671604a19736722aa9bba65d545ccbee7575726b099a69fc68211693c24"
ARTIFACT_BYTES = 194351
SYNC_MARKER = "synced_by_primary_csv_mutator_row019_023_wan_ti2v_class_e_proof_attempt_fail"

STATUS_019 = (
    "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_Class_E_Proof_Attempt_FAIL_Bytes_Gate"
)
STATUS_023 = (
    "Blocked_Video_Frame_Repair_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_"
    "Class_E_Proof_Attempt_FAIL_Bytes_Gate"
)
DECISION = "runpod_wan_ti2v_class_e_proof_attempt_fail_bytes_gate_reject"


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
        and PROMPT_ID in notes
        and "Class_E_Proof_Attempt_FAIL" in notes
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
        "runpod_wan_ti2v_class_e_20260721T055801Z"
    ).replace("/", "\\")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "generation_receipt.json",
        "history.json",
        "prompt_request.json",
    ):
        shutil.copy2(src / name, dst / name)
    frames_src = src / "frames"
    frames_dst = dst / "frames"
    if frames_src.is_dir():
        frames_dst.mkdir(parents=True, exist_ok=True)
        for frame in frames_src.glob("*.jpg"):
            shutil.copy2(frame, frames_dst / frame.name)


def build_packet(tip: str) -> dict:
    return {
        "schema_version": "1.0",
        "evidence_id": f"TRK-W64-019_023_WAN_TI2V_CLASS_E_PROOF_ATTEMPT_FAIL_{STAMP}",
        "created_utc": "2026-07-21T06:10:00Z",
        "created_iso": "2026-07-21T01:10:00-05:00",
        "claim_tier": "class_e_attempt_fail",
        "status": "CLASS_E_PROOF_ATTEMPT_FAIL_REJECT_BYTES_GATE",
        "verdict": "WAN_TI2V_BOUNDED_CLASS_E_PROOF_ATTEMPT_FAIL_REJECT",
        "proof_tier": "RUNPOD_WAN_TI2V_BOUNDED_CLASS_E_PROOF_ATTEMPT_FAIL",
        "highest_proof_tier_achieved": "RUNPOD_WAN_TI2V_BOUNDED_CLASS_E_PROOF_ATTEMPT_FAIL",
        "mutation_this_landing": "bounded_runpod_wan_ti2v_class_e_proof_attempt_fail_bytes_gate",
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
                "filename": (
                    "w64_019_023_runpod_wan_ti2v_class_e_20260721T055801Z_00001_.mp4"
                ),
                "pod_path": (
                    "/workspace/comfy_output/video/"
                    "w64_019_023_runpod_wan_ti2v_class_e_20260721T055801Z_00001_.mp4"
                ),
                "local_pullback": PULLBACK_MP4,
                "sha256": ARTIFACT_SHA,
                "ffprobe": {
                    "codec": "h264",
                    "width": 704,
                    "height": 1280,
                    "nb_frames": 81,
                    "duration_seconds": 3.375,
                    "bit_rate": 460683,
                },
            },
        },
        "bytes_gate": {
            "min_class_e_proof_bytes": 250000,
            "artifact_bytes": ARTIFACT_BYTES,
            "ok": False,
            "fail_reason": "artifact_bytes_194351_below_250000_class_e_proof_floor",
        },
        "technical_qa": {
            "performed": True,
            "technical_pass": True,
            "result": "pass_bounded_video_technical_qa",
            "note": (
                "ffprobe decode OK (704x1280/81f/h264/3.375s). Technical decode is NOT "
                "product COMPLETE and does NOT clear the Class E ≥250KB proof floor."
            ),
        },
        "visual_qa": {
            "performed": True,
            "pass": True,
            "result": "pass_local_vlm_minimum_not_product_complete",
            "reviewer": "ollama_qwen2.5vl_7b_plus_cursor_frame_spotcheck",
            "blunt_defects": [],
            "high_end_llm_in_loop": False,
            "ollama_vlm_in_loop": True,
            "global_review_stamp": None,
            "global_review_note": (
                "Row017 GLOBAL_REVIEW schema is localized-image producer specific; "
                "not applied to this TI2V motion clip. Frame VLM substitute used."
            ),
            "note": (
                "Local VLM PASS on sampled frames; product visual accept still needs "
                "human/Claude when available. Bytes gate FAIL blocks Proof_Landed."
            ),
        },
        "vlm_review": {
            "performed": True,
            "pass": True,
            "verdict": "PASS",
            "model": "qwen2.5vl:7b",
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
                    "The clip shows a fully clothed adult woman with stable identity, "
                    "subtle breathing and fabric motion, realistic skin texture, "
                    "coherent limbs/hands, and no visible defects."
                ),
            },
        },
        "high_end_note": (
            "Local Ollama qwen2.5vl:7b is the required minimum visual gate for this climb. "
            "Product visual accept still needs human/Claude when available; do not treat "
            "local VLM PASS as final product COMPLETE."
        ),
        "class_ladder": {
            "class_f": "ASSET_PRESENT retained",
            "class_e": (
                "attempted raised-quality TI2V (704x1280/81f/36steps/cfg6); "
                "FAIL/REJECT on bytes gate (<250KB) — not Proof_Landed"
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
            f"prompt_id={PROMPT_ID} raised-quality Wan TI2V Class E attempt on RunPod "
            f"(704x1280/81f/36steps/cfg6.0) produced {ARTIFACT_BYTES}-byte mp4. "
            "Ollama qwen2.5vl:7b VLM PASS, but Class E proof floor requires ≥250KB — "
            "Status is FAIL/REJECT not Proof_Landed. row_complete=false; no COMPLETE; "
            f"Row074 untouched; EC2 untouched. tip={tip}."
        ),
        "next_fix_advice": (
            "Re-encode/remux with higher H.264 bitrate (or CRF that yields ≥250KB) while "
            "keeping 704x1280+/81f/30–40 steps/CFG~5.5–6.5 identity-safe clothed prompt; "
            "optional stronger blink/weight-shift cue; re-run qwen2.5vl:7b before any "
            "Proof_Landed Status; still require human/Claude for product accept."
        ),
        "next_action": (
            "Raise encode bitrate / entropy so artifact ≥250KB with VLM still PASS; "
            "only then claim Runtime_Proof_Landed. Keep product visual QA open. No COMPLETE."
        ),
    }


def build_notes(tip: str, row: str) -> str:
    row_bit = (
        "immutable Row023 product visual QA reject retained; "
        if row == "023"
        else "video pipeline Class E attempt FAIL (bytes gate); "
    )
    return (
        f"Wan TI2V RunPod Class E proof attempt FAIL/REJECT bytes gate "
        f"({tip}/{STAMP}): "
        f"prompt_id={PROMPT_ID}; "
        "workflow=wan_2_2_ti2v_5b_primary_lane; "
        "params=704x1280/81f/36steps/cfg6.0/seed2271401; "
        "artifact=/workspace/comfy_output/video/"
        "w64_019_023_runpod_wan_ti2v_class_e_20260721T055801Z_00001_.mp4; "
        f"sha256={ARTIFACT_SHA}; bytes={ARTIFACT_BYTES} (<250000); "
        "Ollama qwen2.5vl:7b VLM PASS but bytes gate FAIL → not Proof_Landed; "
        "product visual still needs human/Claude; "
        f"{row_bit}"
        "claim_tier=class_e_attempt_fail; "
        "proof_tier=RUNPOD_WAN_TI2V_BOUNDED_CLASS_E_PROOF_ATTEMPT_FAIL; "
        "row_complete=false; no COMPLETE; Row074 left alone; EC2 untouched; "
        f"local Comfy untouched. Evidence: {EVIDENCE}; {RECEIPT}; {PULLBACK_MP4}; {POLICY}"
    )


def main() -> None:
    tip = git_short()
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
        f"TRK-W64-019_023_WAN_TI2V_CLASS_E_PROOF_ATTEMPT_FAIL_POLICY_{STAMP}.json",
        json.loads((ROOT / POLICY_RESULT.replace("/", "\\")).read_text(encoding="utf-8")),
    )

    if already_synced(read_notes("TRK-W64-019"), tip) and already_synced(
        read_notes("TRK-W64-023"), tip
    ):
        print("tip", tip)
        print("no-op: TRK/ITEM-W64-019/023 Class E FAIL Notes already synced")
        print("Row074 untouched")
        return

    notes019 = build_notes(tip, "019")
    notes023 = build_notes(tip, "023")
    evid = f"{EVIDENCE}; {RECEIPT}; {PULLBACK_MP4}; {POLICY}; {POLICY_RESULT}"
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
        "vlm_verdict": "PASS",
        "bytes_gate_ok": False,
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
        f"{EVID}/TRK-W64-019_023_WAN_TI2V_CLASS_E_PROOF_ATTEMPT_FAIL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    dump_json(
        "Plan/Tracker/Evidence/Wave64/"
        f"TRK-W64-019_023_WAN_TI2V_CLASS_E_PROOF_ATTEMPT_FAIL_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    print("tip", tip)
    print("synced TRK/ITEM-W64-019/023 Wan TI2V Class E proof attempt FAIL")
    print("prompt_id", PROMPT_ID)
    print("bytes", ARTIFACT_BYTES)
    print("vlm PASS; bytes_gate FAIL; Status FAIL/REJECT; no Proof_Landed; no COMPLETE")
    print("Row074 untouched")


if __name__ == "__main__":
    main()
