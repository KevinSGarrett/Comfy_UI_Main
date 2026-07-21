#!/usr/bin/env python3
"""Stamp Row074 coverage_complete + CURRENT_DELTA. CSV deferred to mutator. No product COMPLETE."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(r"C:\Comfy_UI_Main")
RUNTIME = ROOT / "runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720"
PROGRESS = RUNTIME / "progress.json"
RECEIPT = RUNTIME / "retained_index_segment_receipt.json"
RECORDS = RUNTIME / "records.jsonl"
OWNER = RUNTIME / "FULL_RECONCILE_OWNER.txt"
EVID = ROOT / "Plan/Instructions/QA/Evidence/Wave64"
DELTA = EVID / "TRK-W64-074_MULTI_EVENT_SEGMENTATION_CURRENT_DELTA_20260719.json"
ANALYSIS = EVID / "TRK-W64-074_multi_event_segmentation.json"
SUMMARY = EVID / "TRK-W64-074_ACCEPTED_INDEX_RETAINED_SEGMENT_SUMMARY_20260720.json"

STATUS = "Blocked_Library_Thresholds_And_Event_Count_Calibration_Absent_Reconcile_Complete"
STATUS_HOLD = "HOLD_LIBRARY_THRESHOLDS_AND_EVENT_COUNT_CALIBRATION_ABSENT_RECONCILE_COMPLETE"
PROOF = "RUNTIME_PASS_BOUNDED"
BLOCKERS = [
    "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
    "EVENT_COUNT_CALIBRATION_STRATA_ABSENT",
]
RESUME_CMD = (
    "segment_wave64_multi_event_audio.py --mode index-retained --resume "
    "--retained-runtime-dir runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    live = json.loads(PROGRESS.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    counts = live["counts"]
    processed = int(counts["records_processed"])
    total = int(counts["records_total"])
    assert live.get("complete") is True, live.get("complete")
    assert processed == total == 39771, (processed, total)
    assert receipt.get("coverage_complete") is True, receipt.get("coverage_complete")
    assert receipt.get("product_completion_claimed") is False
    assert receipt.get("library_authority") is False
    assert receipt.get("row_complete") is False

    finalize_pid = None
    owner_text = OWNER.read_text(encoding="utf-8") if OWNER.is_file() else ""
    for line in owner_text.splitlines():
        if line.startswith("pid="):
            try:
                finalize_pid = int(line.split("=", 1)[1].strip())
            except ValueError:
                pass
    guardian_state = RUNTIME / "guardian_poll_state.json"
    if finalize_pid is None and guardian_state.is_file():
        try:
            gstate = json.loads(guardian_state.read_text(encoding="utf-8-sig"))
            if gstate.get("known_pid") is not None:
                finalize_pid = int(gstate["known_pid"])
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass


    summary = {
        "schema_version": 1,
        "evidence_id": "W64-ROW074-ACCEPTED-INDEX-RETAINED-SEGMENT-COVERAGE-COMPLETE-20260720",
        "tracker_id": "TRK-W64-074",
        "item_id": "ITEM-W64-074",
        "authority": "accepted_index_retained_segment_reconcile",
        "coverage_complete": True,
        "limit": None,
        "counts": counts,
        "blocker_histogram": live.get("blocker_histogram", {}),
        "extension_histogram": live.get("extension_histogram", {}),
        "proof_tier": PROOF,
        "highest_proof_tier_achieved": PROOF,
        "library_authority": False,
        "row_complete": False,
        "product_completion_claimed": False,
        "runtime_completion_claimed": True,
        "status": "RUNTIME_PASS_BOUNDED_LIBRARY_THRESHOLDS_FROZEN",
        "runtime_receipt_path": str(RECEIPT.relative_to(ROOT)).replace("\\", "/"),
        "progress_path": str(PROGRESS.relative_to(ROOT)).replace("\\", "/"),
        "records_path": str(RECORDS.relative_to(ROOT)).replace("\\", "/"),
        "receipt_sha256": sha256_file(RECEIPT),
        "records_sha256": sha256_file(RECORDS),
        "progress_sha256": sha256_file(PROGRESS),
        "explicit_non_claims": [
            "COMPLETE",
            "product_completion",
            "library_threshold_authority",
            "library_authority",
        ],
        "finalize_pid": finalize_pid,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    local = datetime.now(ZoneInfo("America/Chicago"))
    stamp_local = local.strftime("%Y%m%dT%H%M-0500")
    created_local = local.strftime("%Y-%m-%dT%H:%M:%S-05:00")
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    stamp_name = f"TRK-W64-074_MULTI_EVENT_SEGMENTATION_RECONCILE_PROGRESS_{stamp_local}.json"
    stamp_path = EVID / stamp_name
    safe_next = (
        "Full-library multi-event segmentation reconcile is coverage_complete under frozen "
        "suggestion-only thresholds. Do not start Row076/Row077 from this stamp. No product "
        "COMPLETE. CSV Notes sync deferred to mutator. Event-count calibration strata remain HOLD."
    )

    stamp = {
        "schema_version": "1.0",
        "evidence_id": f"TRK-W64-074-SEGMENT-RECONCILE-COVERAGE-COMPLETE-{stamp_local}",
        "created_at": created_local,
        "tracker_id": "TRK-W64-074",
        "item_id": "ITEM-W64-074",
        "status": STATUS_HOLD,
        "proof_tier": PROOF,
        "highest_proof_tier_achieved": PROOF,
        "row_complete": False,
        "library_authority": False,
        "runtime_completion_claimed": True,
        "product_completion_claimed": False,
        "csv_stamp": "deferred_to_primary_csv_mutator",
        "process": {
            "action": "finalize_full_library_index_retained_coverage_complete",
            "alive": False,
            "command": RESUME_CMD,
            "exclusive_lane": "library_pcm",
            "parallel_076_077_refused": True,
            "pid": finalize_pid,
            "exit_cause": "clean_exit_coverage_complete",
        },
        "progress": {
            "blocker_histogram": live.get("blocker_histogram", {}),
            "bit_exact_reconstruction_ok": int(counts.get("bit_exact_reconstruction_ok", 0)),
            "complete": True,
            "coverage_complete": True,
            "exact_blockers": int(counts.get("exact_blockers", 0)),
            "extension_histogram": live.get("extension_histogram", {}),
            "feature_non_pass_inputs": int(counts.get("feature_non_pass_inputs", 0)),
            "feature_pass_inputs": int(counts.get("feature_pass_inputs", 0)),
            "limit": None,
            "multi_event_assets": int(counts.get("multi_event_assets", 0)),
            "next_record_index": int(live.get("next_record_index", processed)),
            "pcm_sha_verified": int(counts.get("pcm_sha_verified", 0)),
            "percent_complete": 100.0,
            "records_processed": processed,
            "records_total": total,
            "segment_blocked": int(counts.get("segment_blocked", 0)),
            "segment_pass": int(counts.get("segment_pass", 0)),
            "single_event_assets": int(counts.get("single_event_assets", 0)),
            "source_immutable_true": int(counts.get("source_immutable_true", 0)),
            "started_at": live.get("started_at"),
            "updated_at": live.get("updated_at"),
            "zero_event_assets": int(counts.get("zero_event_assets", 0)),
        },
        "remaining_blockers": BLOCKERS,
        "runtime_paths": {
            "owner_path": str(OWNER.relative_to(ROOT)).replace("\\", "/"),
            "progress_path": str(PROGRESS.relative_to(ROOT)).replace("\\", "/"),
            "records_path": str(RECORDS.relative_to(ROOT)).replace("\\", "/"),
            "receipt_path": str(RECEIPT.relative_to(ROOT)).replace("\\", "/"),
            "retained_runtime_dir": str(RUNTIME.relative_to(ROOT)).replace("\\", "/"),
        },
        "safe_next_action": safe_next,
        "explicit_non_claims": [
            "COMPLETE",
            "product_completion",
            "library_authority",
            "library_threshold_authority",
        ],
        "next_exclusive_pcm_recommendation": "none_do_not_start_076_077_from_this_stamp",
    }
    stamp_path.write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")

    rel_stamp = f"Plan/Instructions/QA/Evidence/Wave64/{stamp_name}"
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    delta["updated_at"] = now_utc
    delta["ledger_status"] = STATUS
    delta["status"] = STATUS_HOLD
    delta["proof_tier"] = PROOF
    delta["highest_proof_tier_achieved"] = PROOF
    delta["row_complete"] = False
    delta["library_authority"] = False
    delta["runtime_completion_claimed"] = True
    delta["product_completion_claimed"] = False
    delta["implementation_completion_claimed"] = False
    delta["blocker_codes"] = BLOCKERS
    delta["acceptance_gaps"] = [
        {
            "code": "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
            "detail": (
                "Segmentation thresholds remain planning-freeze suggestion-only identity, "
                "not production library acceptance."
            ),
        },
        {
            "code": "EVENT_COUNT_CALIBRATION_STRATA_ABSENT",
            "detail": (
                "No representative library strata with truth event-count labels; "
                "full-library coverage proves method identity on retained index only."
            ),
        },
    ]
    delta["accepted_index_retained_segment_runtime"] = {
        "authority": "accepted_index_retained_segment_reconcile",
        "counts": counts,
        "coverage_complete": True,
        "limit": None,
        "proof_tier": PROOF,
        "runtime_receipt_path": str(RECEIPT.relative_to(ROOT)).replace("\\", "/"),
        "status": "RUNTIME_PASS_BOUNDED_LIBRARY_THRESHOLDS_FROZEN",
        "summary_path": str(SUMMARY.relative_to(ROOT)).replace("\\", "/"),
        "summary_sha256": sha256_file(SUMMARY),
        "receipt_sha256": sha256_file(RECEIPT),
        "records_sha256": sha256_file(RECORDS),
        "finalize_pid": finalize_pid,
    }
    delta["ledger_vocabulary_sync"] = {
        "ledger_status": STATUS,
        "note": (
            f"PID {finalize_pid} clean exit coverage_complete {processed}/{total}; "
            f"stamp {stamp_local}; runtime_completion=true; product COMPLETE=false; "
            "CSV deferred to mutator; 076/077 not started."
        ),
        "product_completion": False,
        "runtime_completion": True,
        "progress_stamp": rel_stamp,
        "synced_at": now_utc,
    }
    if isinstance(delta.get("decision"), dict):
        delta["decision"]["row074_status"] = STATUS
        delta["decision"]["row074_acceptance"] = "held"
        delta["decision"]["product_completion"] = False
        delta["decision"]["runtime_completion"] = True
        delta["decision"]["dependencies_unlocked"] = True
        delta["decision"]["safe_next_action"] = safe_next
    if isinstance(delta.get("explicit_non_claims"), list):
        for claim in ("COMPLETE", "product_completion", "library_authority"):
            if claim not in delta["explicit_non_claims"]:
                delta["explicit_non_claims"].append(claim)
    if isinstance(delta.get("preservation_boundary"), dict):
        writable = [
            str(ANALYSIS.relative_to(ROOT)).replace("\\", "/"),
            str(SUMMARY.relative_to(ROOT)).replace("\\", "/"),
            str(DELTA.relative_to(ROOT)).replace("\\", "/"),
            rel_stamp,
            "ztest/stamp_row074_coverage_complete.py",
        ]
        delta["preservation_boundary"]["only_row074_writable_paths"] = writable
        delta["preservation_boundary"]["row076_077_not_started"] = True
        delta["preservation_boundary"]["sound_item_tracker_csv_modified"] = False
        delta["preservation_boundary"]["sound_item_tracker_csv_deferred_reason"] = (
            "deferred_to_primary_csv_mutator"
        )
    DELTA.write_text(json.dumps(delta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Refresh analysis packet coverage pointer without claiming product COMPLETE.
    if ANALYSIS.is_file():
        analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
        analysis["accepted_index_retained_segment_runtime"] = {
            "authority": "accepted_index_retained_segment_reconcile",
            "blocker_histogram": live.get("blocker_histogram", {}),
            "counts": counts,
            "coverage_complete": True,
            "limit": None,
            "present": True,
            "progress_path": str(PROGRESS.relative_to(ROOT)).replace("\\", "/"),
            "receipt_path": str(RECEIPT.relative_to(ROOT)).replace("\\", "/"),
            "records_path": str(RECORDS.relative_to(ROOT)).replace("\\", "/"),
            "status": "RUNTIME_PASS_BOUNDED_LIBRARY_THRESHOLDS_FROZEN",
            "summary_path": str(SUMMARY.relative_to(ROOT)).replace("\\", "/"),
            "summary_sha256": sha256_file(SUMMARY),
        }
        if isinstance(analysis.get("decision"), dict):
            analysis["decision"]["product_completion"] = False
            analysis["decision"]["runtime_completion"] = True
            analysis["decision"]["row074_acceptance"] = "held"
            analysis["decision"]["safe_next_action"] = safe_next
            analysis["decision"]["status"] = "hold"
        analysis["blocker_codes"] = BLOCKERS
        analysis["status"] = STATUS_HOLD
        ANALYSIS.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "stamp": rel_stamp,
                "delta": str(DELTA.relative_to(ROOT)).replace("\\", "/"),
                "summary": str(SUMMARY.relative_to(ROOT)).replace("\\", "/"),
                "analysis": str(ANALYSIS.relative_to(ROOT)).replace("\\", "/"),
                "processed": processed,
                "total": total,
                "coverage_complete": True,
                "product_completion": False,
                "receipt_sha256": sha256_file(RECEIPT),
                "stamp_sha256": sha256_file(stamp_path),
                "delta_sha256": sha256_file(DELTA),
                "next_exclusive_pcm": "none_do_not_start_076_077",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
