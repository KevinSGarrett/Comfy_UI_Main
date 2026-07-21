#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: reconstruct tip Notes sync (20260721)."""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
NOW = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

SOUND_TRACKER = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_TRACKER_ROWS.csv"
SOUND_ITEMS = ROOT / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_ITEM_ROWS.csv"
SPEECH_TRACKER = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv"
SPEECH_ITEMS = ROOT / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv"
E2E_TRACKER = ROOT / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv"
E2E_TRACKER_WAVES = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"
E2E_ITEMS = ROOT / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv"
E2E_ITEMS_WAVES = ROOT / "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"

EVID = ROOT / "Plan/Instructions/QA/Evidence/Wave64"
RUNTIME_EVID = ROOT / "Plan/Instructions/QA/Evidence/Runtime_Readiness"
AUDIO_EVID = ROOT / "Plan/Instructions/QA/Evidence/Audio_Asset_Intake"

POST073_RANK = f"{EVID}/TRK-W64-POST073_EXCLUSIVE_PCM_HANDOFF_RANKING_074_076_077_20260720.json"
ROW073_STAMP = f"{EVID}/TRK-W64-073_USABLE_BOUNDS_DECAY_RECONCILE_PROGRESS_20260720T2246-0500.json"
ROW073_DELTA = f"{EVID}/TRK-W64-073_USABLE_BOUNDS_DECAY_CURRENT_DELTA_20260719.json"
ROW073_ANALYSIS = f"{EVID}/TRK-W64-073_usable_bounds_decay_analysis.json"
ROW073_SUMMARY = f"{EVID}/TRK-W64-073_ACCEPTED_INDEX_RETAINED_BOUNDS_SUMMARY_20260720.json"
RUNPOD_SMOKE = f"{RUNTIME_EVID}/RUNPOD_1q4ji0gg1fkhvt_MECHANICAL_SMOKE_PASS_20260720T2244-0500.json"
FLUX_CANARY = f"{RUNTIME_EVID}/RUNPOD_1q4ji0gg1fkhvt_FLUX_CANARY_GENERATION_PASS_20260721T034826Z.json"
OLLAMA_VLM_SMOKE = (
    f"{RUNTIME_EVID}/RUNPOD_1q4ji0gg1fkhvt_OLLAMA_VLM_FLUX_CANARY_SMOKE_PASS_20260721T041729Z.json"
)
VLM_ENDPOINT = "WAVE64_VLM_URL=http://127.0.0.1:11434"
VLM_MODELS = "llava:13b / qwen2.5:7b-instruct"
ROW010_CALIB = f"{EVID}/TRK-W64-010_RUNPOD_C1_LOCK_LORA_CALIB_20260721T035348Z.json"
ROW010_VLM_IDENTITY = (
    f"{EVID}/TRK-W64-010_RUNPOD_C1_LOCK_LORA_VLM_IDENTITY_20260721T041746Z.json"
)
ROW010_BLOCKER = f"{EVID}/TRK-W64-010_CLASS_A_F_USER_AUTHORITY_FACE_REF_BLOCKER_PACKAGE_20260720.json"
ROW017_EMISSION = f"{EVID}/TRK-W64-017_RUNPOD_FUTURE_PRODUCER_EMISSION_PACKET_20260720T225140-0500.json"
ROW017_READINESS = f"{EVID}/TRK-W64-017_FUTURE_PRODUCER_EMISSION_PROOF_READINESS_20260720.json"
POD_019_023 = f"{EVID}/TRK-W64-019_023_POD_CLASS_A_F_BLOCKER_DISPOSITION_PACKET_20260720T225545-0500.json"
ROW109_DELTA = f"{EVID}/TRK-W64-109_AUDIO_BENCHMARK_CORPUS_CURRENT_DELTA_20260720.json"
ROW109_PACKET = (
    f"{EVID}/TRK-W64-109_CLASS_F_STEP2_GENUINE_MEDIA_ACQUISITION_RIGHTS_CHECKLIST_PACKET_20260720.json"
)
ROW124_DELTA = f"{EVID}/TRK-W64-124_MULTI_REF_LISTENING_CURRENT_DELTA_20260720F.json"
ROW124_ROW = f"{AUDIO_EVID}/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW124.json"
ROW084_PACKET = f"{EVID}/TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_PRODUCTION_READINESS_PACKET_20260721.json"
ROW084_VLM_REVIEW = f"{EVID}/TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_VLM_REVIEW_20260721.json"
ROW084_DELTA = f"{EVID}/TRK-W64-084_CANONICAL_VIDEO_TIMELINE_CURRENT_DELTA_20260719.json"
ROW084_ARTIFACT = f"{EVID}/TRK-W64-084_canonical_video_timeline.json"
ROW084_HOLD_012 = (
    f"{EVID}/TRK-W64-084_ROW084-012_CLASS_C_SCHEMA_NATIVE_REVERSED_PTS_HOLD_PACKET_20260720.json"
)

ROW073_PROGRESS = ROOT / "runtime_artifacts/usable_bounds/row073_index_retained_20260720/progress.json"


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8"))


def dump_json(rel: str, obj: dict) -> None:
    path = ROOT / rel.replace("/", "\\")
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sync_delta(
    rel: str,
    *,
    status: str,
    proof_tier: str,
    blockers: list[str],
    prove_commits: list[str],
    extra: dict | None = None,
) -> None:
    d = load_json(rel)
    d["updated_at"] = NOW
    d["ledger_status"] = status
    d["proof_tier"] = proof_tier
    d["highest_proof_tier_achieved"] = proof_tier
    d["row_complete"] = False
    d["library_authority"] = False
    d["blocker_codes"] = blockers
    d["ledger_vocabulary_sync"] = {
        "ledger_status": status,
        "note": f"Mechanical CSV mutator sync from {','.join(prove_commits)}; no COMPLETE.",
        "product_completion": False,
        "runtime_completion": d.get("runtime_completion_claimed", False),
        "synced_at": NOW,
        "prove_commits": prove_commits,
    }
    if extra:
        d.update(extra)
    dump_json(rel, d)


def rewrite_csv(path: Path, id_col: str, updates: dict[str, dict[str, str]]) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    assert fields
    for row in rows:
        key = row[id_col]
        if key in updates:
            row.update(updates[key])
    for key in updates:
        assert any(r[id_col] == key for r in rows), f"missing {key} in {path}"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    tip = git_short()
    prove = [
        "cd517ee7",
        "581c21f8",
        "cf72e756",
        "7b2d9490",
        "b85b13a2",
        "77dac184",
        "c44d1dd9",
        "83da2a63",
        "e1401895",
        "73f185c5",
        tip,
    ]

    row073_live = json.loads(ROW073_PROGRESS.read_text(encoding="utf-8"))
    p073 = int(row073_live["counts"]["records_processed"])
    t073 = int(row073_live["counts"]["records_total"])
    assert row073_live.get("complete") is True and p073 == t073 == 39771

    row073_status = "Blocked_Library_Thresholds_And_Benchmark_Strata_Absent_Reconcile_Complete"
    row073_decision = "row073_reconcile_complete_thresholds_and_strata_held_runtime_pass_bounded"
    row073_proof = "RUNTIME_PASS_BOUNDED"
    row073_blockers = [
        "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
        "REPRESENTATIVE_STRATA_CALIBRATION_ABSENT",
    ]
    row073_notes = (
        f"Coverage_complete index-retained bounds reconcile {p073}/{t073} (~100%); "
        f"PID 27320 clean exit left alone (483be3ee/T2246); proof_tier={row073_proof}; "
        f"runtime_completion=true; row_complete=false; library_authority=false; no COMPLETE. "
        f"Post-073 gate: Row074 first exclusive PCM ({POST073_RANK}). RunPod smoke+Flux canary "
        f"({RUNPOD_SMOKE}; {FLUX_CANARY}). Blockers: "
        + "|".join(row073_blockers)
        + f". Evidence: {ROW073_STAMP}; {POST073_RANK}"
    )
    row073_evidence = (
        f"{ROW073_ANALYSIS}; {ROW073_SUMMARY}; {ROW073_STAMP}; {ROW073_DELTA}; {POST073_RANK}"
    )

    sync_delta(
        ROW073_DELTA,
        status=row073_status,
        proof_tier=row073_proof,
        blockers=row073_blockers,
        prove_commits=prove,
        extra={"runtime_completion_claimed": True, "product_completion_claimed": False},
    )

    row075_notes = (
        "Coverage_complete retained; Class F/D shortlist stop (d71ec94d/dce0fd1a): 13 candidates "
        "(5 labeled/6 pending/2 blocked); thresholds still frozen; BOTH blockers remain "
        "(REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY|"
        "REPRESENTATIVE_STRATA_CALIBRATION_ABSENT); row_complete=false; no COMPLETE. "
        f"Evidence: {EVID}/TRK-W64-075_audio_defect_classification.json"
    )

    row109_notes = (
        "Class F step2 acquisition/rights checklist deepened (9f9ec22a): open=14/satisfied=1; "
        "media/row109 empty; proof_tier=OFFLINE_ACQUISITION_RIGHTS_CHECKLIST_BOUNDED; "
        "row_complete=false; library_authority=false. Blockers: "
        "GENUINE_ANNOTATED_MEDIA_CORPUS_ABSENT|COMBINED_FRAME_CONTACT_AUDIO_REVIEW_ABSENT|"
        "PRODUCTION_BENCHMARK_AUTHORITY_ABSENT|HELD_OUT_RUNTIME_PROOF_ABSENT. Evidence: "
        f"{ROW109_PACKET}"
    )

    vlm_endpoint_note = (
        f"Durable RunPod Ollama VLM/LLM reviewer UP (e1401895/{tip}): {VLM_ENDPOINT} "
        f"({VLM_MODELS}); Flux canary VLM smoke PASS_WITH_NOTES. Evidence: {OLLAMA_VLM_SMOKE}"
    )

    row010_notes = (
        "Class A/F USER_AUTHORITY face-ref blocker (b9085976/db81ab66): per-character reference "
        "crops absent and not inventable; proof_tier=OFFLINE_INVENTORY_BLOCKER_BOUNDED; "
        "RunPod personal-calibration panel-v2 VLM GATE CLEARED "
        "(f7081a0d/041746Z): qwen2.5vl:7b side_by_side_panel_v2 face_consistency_mean 0.5625 "
        "(n=4)/body_silhouette_mean 0.9/solo_lock_trait_alignment 0.95; runtime_pass_bounded=true; "
        "still NONCANONICAL; C1 lock+LoRA calib (035348Z/cf72e756) retained; "
        "multi-character USER_AUTHORITY retained blocked; does NOT clear generic "
        "multi-character USER_AUTHORITY chain; row_complete=false; NEVER Complete. Blockers: "
        "USER_AUTHORITY_PER_CHARACTER_REFERENCE_CROPS_ABSENT|"
        "USER_AUTHORITY_FACE_BODY_REFERENCES_NOT_INVENTABLE|"
        "PORTABLE_MULTI_CHARACTER_REFERENCE_CHAIN_ABSENT|PERSONAL_CALIBRATION_CHARACTER1_EXCLUDED. "
        f"Evidence: {ROW010_BLOCKER}; {ROW010_CALIB}; {ROW010_VLM_IDENTITY}; {OLLAMA_VLM_SMOKE}"
    )

    row017_notes = (
        "Class C cleared (70e12e70); Class E emission-proof readiness (cc68fd5a); RunPod "
        "1q4ji0gg1fkhvt mechanical smoke PASS (1c4e2432) + Flux canary generation PASS "
        f"(cf72e756); RunPod future-producer emission bounded climb VISUAL_QA_PASS_BOUNDED "
        f"(7b2d9490): face-mask v1 execute+global review; local :8188 unreachable; "
        "row_complete=false; NEVER Complete. Blockers: "
        "FUTURE_PRODUCER_EMISSION_PROOF_PACKAGE_ABSENT|RUNTIME_8188_UNREACHABLE_BLOCKS_PRODUCER_EMISSION. "
        f"Evidence: {ROW017_READINESS}; {ROW017_EMISSION}; {RUNPOD_SMOKE}; {FLUX_CANARY}"
    )

    row019_notes = (
        "Class A/F POD live inventory disposition (581c21f8/225545-0500): Wan TI2V 0/3 absent; "
        "gold authority 7/7 ABSENT on pod; local :8188 unreachable; RunPod remote :8188 PASS "
        f"(1c4e2432) + Flux canary PASS (cf72e756) — route GPU climb on pod; Flux seed retries "
        "stopped (2272301/2272401/2272507); row_complete=false; no COMPLETE. "
        f"Evidence: {POD_019_023}; {FLUX_CANARY}"
    )
    row023_notes = (
        "Class A/F POD live inventory disposition (581c21f8/225545-0500): Wan TI2V 0/3 absent; "
        "gold-mask authority absent on pod; local :8188 unreachable; RunPod remote :8188 PASS "
        f"(1c4e2432) + Flux canary PASS (cf72e756); Class B REJECT retained; row_complete=false; "
        f"no COMPLETE. Evidence: {POD_019_023}; {FLUX_CANARY}"
    )

    row124_notes = (
        "OFFLINE_PROOF_BOUNDED (b85b13a2/20260720F): multi-ref drift/leakage matrix complete; "
        "Path A bounded stretch live-measured OUT OF BOUNDS; fail-closed timing waiver NOT "
        "granted (RAW_DIALOGUE_TIMING_OUT_OF_TOLERANCE); human-listening fail-closed retained; "
        "listening_authority_granted=false; row_complete=false; no COMPLETE. "
        f"Evidence: {ROW124_DELTA}; {ROW124_ROW}"
    )

    row084_status = (
        "Blocked_Visual_Qa_Pass_Bounded_Class_C_Schema_Native_Hold_And_Production_Completion_Blocked"
    )
    row084_decision = "row084_class_e_runpod_readiness_vlm_probed_no_complete"
    row084_proof = "RUNTIME_PROBE_VISUAL_BOUNDED_WITH_VLM_REVIEW"
    row084_notes = (
        "Class E continue (c44d1dd9/83da2a63/e1401895): RunPod Comfy :8188 re-probe "
        f"{row084_proof}; Ollama qwen2.5vl:7b 3/3 frames reviewed via {VLM_ENDPOINT} "
        f"({VLM_MODELS}; durable e1401895/{tip}). "
        "ROW084-011 Class E FAIL/OPEN retained (production COMPLETE withheld); "
        "ROW084-012 Class C OPEN_HOLD unchanged (0e0c3d86); ROW084-015/017/013 PASS retained; "
        f"row_complete=false; NEVER Complete; Row074 left alone. Evidence: {ROW084_PACKET}; "
        f"{ROW084_VLM_REVIEW}; {OLLAMA_VLM_SMOKE}; {ROW084_DELTA}; {ROW084_HOLD_012}"
    )
    row084_evidence = (
        f"{ROW084_ARTIFACT}; {ROW084_DELTA}; {ROW084_PACKET}; "
        f"{ROW084_VLM_REVIEW}; {OLLAMA_VLM_SMOKE}; {ROW084_HOLD_012}"
    )

    sound_tracker_updates = {
        "TRK-W64-073": {
            "Status": row073_status,
            "Status_Decision": row073_decision,
            "Notes": row073_notes,
            "Evidence_Path": row073_evidence,
        },
        "TRK-W64-075": {"Notes": row075_notes},
        "TRK-W64-109": {
            "Status": "Blocked_Synthetic_Fixture_Corpus_Present_Genuine_Media_And_Visual_QA_Absent",
            "Status_Decision": "row109_acquisition_rights_checklist_hold_genuine_media_absent",
            "Notes": row109_notes,
            "Evidence_Path": ROW109_PACKET,
        },
        "TRK-W64-084": {
            "Status": row084_status,
            "Status_Decision": row084_decision,
            "Notes": row084_notes,
            "Evidence_Path": row084_evidence,
        },
    }
    sound_item_updates = {
        "ITEM-W64-073": {"Status": row073_status, "Notes": row073_notes},
        "ITEM-W64-075": {"Notes": row075_notes},
        "ITEM-W64-109": {
            "Status": "Blocked_Synthetic_Fixture_Corpus_Present_Genuine_Media_And_Visual_QA_Absent",
            "Notes": row109_notes,
        },
        "ITEM-W64-084": {
            "Status": row084_status,
            "Notes": row084_notes,
        },
    }

    speech_tracker_updates = {
        "TRK-W64-124": {
            "Notes": row124_notes,
            "Evidence_Path": f"{ROW124_ROW}; {ROW124_DELTA}",
        },
    }
    speech_item_updates = {
        "ITEM-W64-124": {"Notes": row124_notes},
    }

    e2e_tracker_updates = {
        "TRK-W64-010": {
            "Status": "Blocked_Identity_Reference_Proof_Missing_Separation_And_Merge_Rejection_Pass",
            "Notes": row010_notes + " " + vlm_endpoint_note,
            "Evidence_Path": (
                f"{ROW010_BLOCKER}; {ROW010_CALIB}; {ROW010_VLM_IDENTITY}; {OLLAMA_VLM_SMOKE}"
            ),
        },
        "TRK-W64-017": {
            "Notes": row017_notes + " " + vlm_endpoint_note,
            "Evidence_Path": (
                f"{ROW017_READINESS}; {ROW017_EMISSION}; {RUNPOD_SMOKE}; "
                f"{FLUX_CANARY}; {OLLAMA_VLM_SMOKE}"
            ),
        },
        "TRK-W64-019": {"Notes": row019_notes},
        "TRK-W64-023": {"Notes": row023_notes},
    }
    e2e_item_updates = {
        "ITEM-W64-010": {
            "Status": "Blocked_Identity_Reference_Proof_Missing_Separation_And_Merge_Rejection_Pass",
            "Notes": row010_notes + " " + vlm_endpoint_note,
        },
        "ITEM-W64-017": {"Notes": row017_notes + " " + vlm_endpoint_note},
        "ITEM-W64-019": {"Notes": row019_notes},
        "ITEM-W64-023": {"Notes": row023_notes},
    }

    rewrite_csv(SOUND_TRACKER, "Tracker_ID", sound_tracker_updates)
    rewrite_csv(SOUND_ITEMS, "Item_ID", sound_item_updates)
    rewrite_csv(SPEECH_TRACKER, "Tracker_ID", speech_tracker_updates)
    rewrite_csv(SPEECH_ITEMS, "Item_ID", speech_item_updates)
    rewrite_csv(E2E_TRACKER, "Tracker_ID", e2e_tracker_updates)
    rewrite_csv(E2E_TRACKER_WAVES, "Tracker_ID", e2e_tracker_updates)
    rewrite_csv(E2E_ITEMS, "Item_ID", e2e_item_updates)
    rewrite_csv(E2E_ITEMS_WAVES, "Item_ID", e2e_item_updates)

    sync_delta(
        ROW109_DELTA,
        status="Blocked_Synthetic_Fixture_Corpus_Present_Genuine_Media_And_Visual_QA_Absent",
        proof_tier="OFFLINE_ACQUISITION_RIGHTS_CHECKLIST_BOUNDED",
        blockers=[
            "GENUINE_ANNOTATED_MEDIA_CORPUS_ABSENT",
            "COMBINED_FRAME_CONTACT_AUDIO_REVIEW_ABSENT",
            "PRODUCTION_BENCHMARK_AUTHORITY_ABSENT",
            "HELD_OUT_RUNTIME_PROOF_ABSENT",
        ],
        prove_commits=prove,
    )

    stamp = load_json(ROW073_STAMP)
    stamp["csv_stamp"] = "synced_by_primary_csv_mutator_20260721"
    stamp["csv_sync_tip"] = tip
    dump_json(ROW073_STAMP, stamp)

    row124_delta = load_json(ROW124_DELTA)
    row124_delta["csv_sync"] = "synced_by_primary_csv_mutator"
    row124_delta["csv_sync_tip"] = tip
    dump_json(ROW124_DELTA, row124_delta)

    sync_delta(
        ROW084_DELTA,
        status=row084_status,
        proof_tier=row084_proof,
        blockers=[
            "PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED",
            "CLOCK_SPAN_REVERSED_PTS_JSON_SCHEMA_NATIVE_ABSENT",
            "COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED",
        ],
        prove_commits=prove,
        extra={"runtime_completion_claimed": False, "product_completion_claimed": False},
    )
    row084_packet = load_json(ROW084_PACKET)
    row084_packet["csv_sync"] = "synced_by_primary_csv_mutator"
    row084_packet["csv_sync_tip"] = tip
    dump_json(ROW084_PACKET, row084_packet)

    print("tip", tip)
    print("synced Row073", p073, t073)
    print("Row074 left alone (no CSV writes)")
    print("synced Ollama VLM endpoint e1401895 + 010/084 tip Notes")
    print("synced 010/017/019/023/075/084/109/124")


if __name__ == "__main__":
    main()
