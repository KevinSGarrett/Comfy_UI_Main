#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 Wan TI2V smoke ≠ Class E proof correction."""
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
STAMP = "20260721T005200-0500"
CORRECTION = f"{EVID}/TRK-W64-019_023_WAN_TI2V_RUNTIME_SMOKE_NOT_CLASS_E_PROOF_{STAMP}.json"
CORRECTION_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    f"TRK-W64-019_023_WAN_TI2V_RUNTIME_SMOKE_NOT_CLASS_E_PROOF_{STAMP}.json"
)
CURRENT = f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
CURRENT_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_CURRENT.json"
)
PRIOR_OVERSTATED = (
    f"{EVID}/TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_20260721T004726-0500.json"
)
RECEIPT = (
    f"{EVID}/fixtures/row019_023/runtime/runpod_wan_ti2v_proof_20260721T054626Z/"
    "generation_receipt.json"
)
PULLBACK = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "runpod_wan_ti2v_proof_20260721T054626Z/"
    "w64_019_023_runpod_wan_ti2v_proof_20260721T054626Z_00001_.mp4"
)
POLICY = (
    "Plan/07_IMPLEMENTATION/scripts/"
    "validate_wave64_wan_ti2v_class_e_runtime_proof_claim.py"
)

PROMPT_ID = "3c525270-e87d-4fe0-9930-4c564e512626"
ARTIFACT_SHA = "bb3a6d02d07dad4cb9e65c357296c6345f08d9fa184231eb2c430ffbd51960e3"
SYNC_MARKER = "synced_by_primary_csv_mutator_row019_023_wan_ti2v_smoke_not_class_e_proof"

STATUS_019 = (
    "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_Runtime_Smoke_Emitted_Not_Class_E_Proof"
)
STATUS_023 = (
    "Blocked_Video_Frame_Repair_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_"
    "Runtime_Smoke_Emitted_Not_Class_E_Proof"
)
DECISION = "runpod_wan_ti2v_runtime_smoke_emitted_visual_fail_not_class_e_proof"


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
        and "Runtime_Smoke_Emitted_Not_Class_E_Proof" in notes
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


def build_packet(tip: str) -> dict:
    return {
        "schema_version": "1.0",
        "evidence_id": f"TRK-W64-019_023_WAN_TI2V_RUNTIME_SMOKE_NOT_CLASS_E_PROOF_{STAMP}",
        "created_utc": "2026-07-21T05:52:00Z",
        "created_iso": "2026-07-21T00:52:00-05:00",
        "claim_tier": "smoke_emission",
        "status": "RUNTIME_SMOKE_EMITTED_VISUAL_FAIL_NOT_CLASS_E_PROOF",
        "verdict": "WAN_TI2V_BOUNDED_RUNTIME_SMOKE_EMISSION_ON_RUNPOD_VISUAL_FAIL",
        "proof_tier": "RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_SMOKE_EMISSION",
        "highest_proof_tier_achieved": "RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_SMOKE_EMISSION",
        "mutation_this_landing": "correct_overstated_class_e_runtime_proof_to_smoke_emission",
        "prior_overstated_evidence": PRIOR_OVERSTATED,
        "prior_overstated_commit": "f93ba611",
        "csv_sync": SYNC_MARKER,
        "item_ids": ["ITEM-W64-019", "ITEM-W64-023"],
        "tracker_ids": ["TRK-W64-019", "TRK-W64-023"],
        "binding": {
            "sole_runtime": "RunPod",
            "pod_id": "1q4ji0gg1fkhvt",
            "ssh": "root@195.26.233.100:52077",
            "forbidden": ["EC2", "local_Comfy", "Row074", "COMPLETE"],
        },
        "generation": {
            "prompt_id": PROMPT_ID,
            "completed": True,
            "status_str": "success",
            "width": 480,
            "height": 640,
            "length": 49,
            "fps": 24,
            "steps": 20,
            "cfg": 5,
            "seed": 2271301,
            "artifact": {
                "bytes": 94378,
                "filename": "w64_019_023_runpod_wan_ti2v_proof_20260721T054626Z_00001_.mp4",
                "pod_path": (
                    "/workspace/comfy_output/video/"
                    "w64_019_023_runpod_wan_ti2v_proof_20260721T054626Z_00001_.mp4"
                ),
                "local_pullback": PULLBACK,
                "sha256": ARTIFACT_SHA,
                "ffprobe": {
                    "duration_seconds": 2.041667,
                    "bit_rate": 355200,
                    "nb_frames": 49,
                    "codec": "h264",
                },
            },
        },
        "technical_qa": {
            "performed": True,
            "technical_pass": True,
            "result": "pass_bounded_video_technical_qa",
            "note": (
                "Decode/black/freeze technical gate passes; this is NOT product/identity pass. "
                "luminance_mean_span≈1.5; near-static smoke motion."
            ),
        },
        "visual_qa": {
            "performed": True,
            "pass": False,
            "result": "fail_product_visual_qa",
            "reviewer": "interactive_cursor_shift_direct_frame_read",
            "blunt_defects": [
                "mangled/fused hands and freak finger proportions",
                "impossible bodysuit-to-leggings V crotch garment fusion",
                "plastic oversmoothed skin and flat lighting",
                "blurry sneakers / weak extremity detail",
                "near-static 2s smoke clip; not credible TI2V identity motion proof",
            ],
            "high_end_llm_in_loop": False,
            "ollama_vlm_in_loop": False,
            "global_review_stamp": None,
        },
        "vlm_review": {
            "performed": False,
            "pass": False,
            "reason": "not_run_for_this_smoke_emission; product visual QA remains open",
        },
        "class_ladder": {
            "class_f": "ASSET_PRESENT retained",
            "class_e": "NOT cleared — prior Runtime_Proof_Landed language retracted to smoke_emission",
            "class_a": "product_visual_qa_fail_open",
            "not_claimed": [
                "row_complete",
                "COMPLETE",
                "class_e_runtime_proof_success",
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
            f"prompt_id={PROMPT_ID} (94378-byte 480x640/49f mp4) is RunPod Wan TI2V runtime "
            "smoke emission only. Direct frame inspection FAIL (hands/garment/plastic/"
            "near-static). No Ollama/GLOBAL_REVIEW/Claude visual loop on this climb. "
            f"Retract Class E Runtime_Proof_Landed language (f93ba611/{tip}). "
            "row_complete=false; no COMPLETE; Row074 untouched; EC2 untouched."
        ),
        "recommended_wan_proof_params": {
            "width_height": "720x1280 or 704x1280 minimum for identity proof",
            "length_frames": "81+",
            "steps": "30-40",
            "cfg": "5.0-6.5",
            "require_before_proof_status": [
                "ffprobe non-black decode",
                "artifact_bytes >= 250000",
                "direct visual QA or GLOBAL_REVIEW/VLM pass",
                "Status may say Runtime_Proof_Landed only after visual pass",
            ],
        },
        "next_action": (
            "Re-run Wan TI2V with stronger params; require visual/VLM before any "
            "Class E proof-success Status. Keep product visual QA open. No COMPLETE."
        ),
    }


def build_notes(tip: str, row: str) -> str:
    row_bit = (
        "immutable Row023 product visual QA reject retained; "
        if row == "023"
        else "video pipeline runtime smoke only; "
    )
    return (
        f"Wan TI2V RunPod runtime smoke emitted NOT Class E proof "
        f"(f93ba611/{tip}/{STAMP}): "
        f"prompt_id={PROMPT_ID}; "
        "workflow=wan_2_2_ti2v_5b_primary_lane; "
        "artifact=/workspace/comfy_output/video/"
        "w64_019_023_runpod_wan_ti2v_proof_20260721T054626Z_00001_.mp4; "
        f"sha256={ARTIFACT_SHA}; bytes=94378; "
        "direct visual FAIL (hands/garment fusion/plastic/near-static); "
        "no Ollama/GLOBAL_REVIEW/Claude on this climb; "
        "technical decode pass ≠ product/identity pass; "
        f"{row_bit}"
        "claim_tier=smoke_emission; "
        "proof_tier=RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_SMOKE_EMISSION; "
        "row_complete=false; no COMPLETE; Row074 left alone; EC2 untouched; "
        f"local Comfy untouched. Evidence: {CORRECTION}; {RECEIPT}; {PULLBACK}; {POLICY}"
    )


def main() -> None:
    tip = git_short()
    packet = build_packet(tip)
    dump_json(CORRECTION, packet)
    dump_json(CORRECTION_TRACKER, packet)
    dump_json(CURRENT, packet)
    dump_json(CURRENT_TRACKER, packet)
    shutil.copy2(ROOT / CORRECTION.replace("/", "\\"), ROOT / CORRECTION_TRACKER.replace("/", "\\"))

    if already_synced(read_notes("TRK-W64-019"), tip) and already_synced(
        read_notes("TRK-W64-023"), tip
    ):
        print("tip", tip)
        print("no-op: TRK/ITEM-W64-019/023 smoke-not-proof Notes already synced")
        print("Row074 untouched")
        return

    notes019 = build_notes(tip, "019")
    notes023 = build_notes(tip, "023")
    evid = f"{CORRECTION}; {RECEIPT}; {PULLBACK}; {POLICY}"
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
        "rows": ["TRK-W64-019", "TRK-W64-023", "ITEM-W64-019", "ITEM-W64-023"],
        "status_019": STATUS_019,
        "status_023": STATUS_023,
        "status_decision": DECISION,
        "claim_tier": "smoke_emission",
        "row074_touched": False,
        "complete_claimed": False,
        "row_complete": False,
        "evidence": CORRECTION,
    }
    dump_json(
        f"{EVID}/TRK-W64-019_023_WAN_TI2V_RUNTIME_SMOKE_NOT_CLASS_E_PROOF_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    dump_json(
        "Plan/Tracker/Evidence/Wave64/"
        f"TRK-W64-019_023_WAN_TI2V_RUNTIME_SMOKE_NOT_CLASS_E_PROOF_NOTES_SYNC_RECEIPT_{STAMP}.json",
        sync_receipt,
    )
    print("tip", tip)
    print("synced TRK/ITEM-W64-019/023 smoke-not-Class-E proof correction")
    print("prompt_id", PROMPT_ID)
    print("Row074 untouched; no COMPLETE")


if __name__ == "__main__":
    main()
