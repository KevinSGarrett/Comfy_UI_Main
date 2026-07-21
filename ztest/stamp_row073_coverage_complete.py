#!/usr/bin/env python3
"""Stamp Row073 coverage_complete + CURRENT_DELTA. CSV deferred to mutator. No product COMPLETE."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(r"C:\Comfy_UI_Main")
RUNTIME = ROOT / "runtime_artifacts/usable_bounds/row073_index_retained_20260720"
PROGRESS = RUNTIME / "progress.json"
RECEIPT = RUNTIME / "retained_index_bounds_receipt.json"
RECORDS = RUNTIME / "records.jsonl"
OWNER = RUNTIME / "FULL_RECONCILE_OWNER.txt"
EVID = ROOT / "Plan/Instructions/QA/Evidence/Wave64"
DELTA = EVID / "TRK-W64-073_USABLE_BOUNDS_DECAY_CURRENT_DELTA_20260719.json"
ANALYSIS = EVID / "TRK-W64-073_usable_bounds_decay_analysis.json"
SUMMARY = EVID / "TRK-W64-073_ACCEPTED_INDEX_RETAINED_BOUNDS_SUMMARY_20260720.json"
PRIOR_STAMP = EVID / "TRK-W64-073_USABLE_BOUNDS_DECAY_RECONCILE_PROGRESS_20260720T1152-0500.json"

STATUS = "Blocked_Library_Thresholds_And_Benchmark_Strata_Absent_Reconcile_Complete"
STATUS_HOLD = "HOLD_LIBRARY_THRESHOLDS_AND_BENCHMARK_STRATA_ABSENT_RECONCILE_COMPLETE"
PROOF = "RUNTIME_PASS_BOUNDED"
BLOCKERS = [
    "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
    "REPRESENTATIVE_STRATA_CALIBRATION_ABSENT",
]


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

    # Copy runtime receipt/analysis into evidence tree (exact paths used by prior probe).
    analysis_src = RUNTIME / "usable_bounds_decay_analysis.json"
    if analysis_src.is_file():
        shutil.copy2(analysis_src, ANALYSIS)
    elif (RUNTIME / "retained_index_bounds_analysis.json").is_file():
        shutil.copy2(RUNTIME / "retained_index_bounds_analysis.json", ANALYSIS)
    else:
        # Analyzer writes receipt; analysis evidence may already exist — refresh from receipt.
        ANALYSIS.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "schema_version": 1,
        "evidence_id": "W64-ROW073-ACCEPTED-INDEX-RETAINED-BOUNDS-COVERAGE-COMPLETE-20260720",
        "tracker_id": "TRK-W64-073",
        "item_id": "ITEM-W64-073",
        "authority": "accepted_index_retained_bounds_reconcile",
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
        "finalize_pid": 27320,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    local = datetime.now(ZoneInfo("America/Chicago"))
    stamp_local = local.strftime("%Y%m%dT%H%M-0500")
    created_local = local.strftime("%Y-%m-%dT%H:%M:%S-05:00")
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    stamp_name = f"TRK-W64-073_USABLE_BOUNDS_DECAY_RECONCILE_PROGRESS_{stamp_local}.json"
    stamp_path = EVID / stamp_name

    stamp = {
        "schema_version": "1.0",
        "evidence_id": f"TRK-W64-073-BOUNDS-RECONCILE-COVERAGE-COMPLETE-{stamp_local}",
        "created_at": created_local,
        "tracker_id": "TRK-W64-073",
        "item_id": "ITEM-W64-073",
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
            "command": (
                "analyze_wave64_usable_bounds_decay.py --mode index-retained --resume "
                "--retained-runtime-dir runtime_artifacts/usable_bounds/row073_index_retained_20260720"
            ),
            "exclusive_lane": "library_pcm",
            "parallel_074_076_077_refused": True,
            "pid": 27320,
            "prior_dead_pid": 20200,
            "exit_cause": "clean_exit_coverage_complete",
        },
        "progress": {
            "blocker_histogram": live.get("blocker_histogram", {}),
            "bounds_blocked": int(counts.get("bounds_blocked", 0)),
            "bounds_pass": int(counts.get("bounds_pass", 0)),
            "complete": True,
            "coverage_complete": True,
            "exact_blockers": int(counts.get("exact_blockers", 0)),
            "extension_histogram": live.get("extension_histogram", {}),
            "feature_non_pass_inputs": int(counts.get("feature_non_pass_inputs", 0)),
            "feature_pass_inputs": int(counts.get("feature_pass_inputs", 0)),
            "limit": None,
            "next_record_index": int(live.get("next_record_index", processed)),
            "onset_preservation_ok": int(counts.get("onset_preservation_ok", 0)),
            "pcm_sha_verified": int(counts.get("pcm_sha_verified", 0)),
            "percent_complete": 100.0,
            "records_processed": processed,
            "records_total": total,
            "source_immutable_true": int(counts.get("source_immutable_true", 0)),
            "started_at": live.get("started_at"),
            "tail_preservation_ok": int(counts.get("tail_preservation_ok", 0)),
            "updated_at": live.get("updated_at"),
        },
        "remaining_blockers": BLOCKERS,
        "runtime_paths": {
            "owner_path": str(OWNER.relative_to(ROOT)).replace("\\", "/"),
            "progress_path": str(PROGRESS.relative_to(ROOT)).replace("\\", "/"),
            "records_path": str(RECORDS.relative_to(ROOT)).replace("\\", "/"),
            "receipt_path": str(RECEIPT.relative_to(ROOT)).replace("\\", "/"),
            "retained_runtime_dir": str(RUNTIME.relative_to(ROOT)).replace("\\", "/"),
        },
        "safe_next_action": (
            "Full-library usable-bounds reconcile is coverage_complete under frozen "
            "suggestion-only thresholds. Next exclusive library PCM owner: recommend "
            "Row074 (multi_event_segmentation; P0; deps Row072+Row073). Do not start "
            "074/076/077 until this stamp is accepted. No product COMPLETE. CSV Notes "
            "sync deferred to mutator."
        ),
        "explicit_non_claims": [
            "COMPLETE",
            "product_completion",
            "library_authority",
            "library_threshold_authority",
        ],
        "next_exclusive_pcm_recommendation": "TRK-W64-074",
    }
    stamp_path.write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")

    if PRIOR_STAMP.exists():
        prev = json.loads(PRIOR_STAMP.read_text(encoding="utf-8"))
        prev["csv_stamp"] = f"superseded_by_{stamp_name}"
        PRIOR_STAMP.write_text(json.dumps(prev, indent=2) + "\n", encoding="utf-8")

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
                "Silence/hysteresis/suggestion-only thresholds remain planning-freeze "
                "identity, not production library acceptance."
            ),
        },
        {
            "code": "REPRESENTATIVE_STRATA_CALIBRATION_ABSENT",
            "detail": (
                "No representative library strata with truth usable bounds/decay labels; "
                "full-library coverage proves method identity on retained index only."
            ),
        },
    ]
    delta["accepted_index_retained_bounds_runtime"] = {
        "authority": "accepted_index_retained_bounds_reconcile",
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
        "finalize_pid": 27320,
    }
    delta["ledger_vocabulary_sync"] = {
        "ledger_status": STATUS,
        "note": (
            f"PID 27320 clean exit coverage_complete {processed}/{total}; "
            f"stamp {stamp_local}; runtime_completion=true; product COMPLETE=false; "
            "CSV deferred to mutator."
        ),
        "product_completion": False,
        "runtime_completion": True,
        "progress_stamp": rel_stamp,
        "synced_at": now_utc,
    }
    if isinstance(delta.get("decision"), dict):
        delta["decision"]["row073_status"] = STATUS
        delta["decision"]["row073_acceptance"] = "held"
        delta["decision"]["product_completion"] = False
        delta["decision"]["runtime_completion"] = True
        delta["decision"]["dependencies_unlocked"] = True
        delta["decision"]["safe_next_action"] = stamp["safe_next_action"]
    if isinstance(delta.get("explicit_non_claims"), list):
        for claim in ("COMPLETE", "product_completion", "library_authority"):
            if claim not in delta["explicit_non_claims"]:
                delta["explicit_non_claims"].append(claim)
    # Refresh preservation boundary writable note for this stamp only.
    if isinstance(delta.get("preservation_boundary"), dict):
        writable = [
            "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-073_usable_bounds_decay_analysis.json",
            "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-073_ACCEPTED_INDEX_RETAINED_BOUNDS_SUMMARY_20260720.json",
            "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-073_USABLE_BOUNDS_DECAY_CURRENT_DELTA_20260719.json",
            rel_stamp,
            "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-073_USABLE_BOUNDS_DECAY_RECONCILE_PROGRESS_20260720T1152-0500.json",
        ]
        delta["preservation_boundary"]["only_row073_writable_paths"] = writable
        delta["preservation_boundary"]["row074_076_077_not_started"] = True
    DELTA.write_text(json.dumps(delta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "stamp": rel_stamp,
                "delta": str(DELTA.relative_to(ROOT)).replace("\\", "/"),
                "summary": str(SUMMARY.relative_to(ROOT)).replace("\\", "/"),
                "processed": processed,
                "total": total,
                "coverage_complete": True,
                "product_completion": False,
                "receipt_sha256": sha256_file(RECEIPT),
                "stamp_sha256": sha256_file(stamp_path),
                "delta_sha256": sha256_file(DELTA),
                "next_exclusive_pcm": "TRK-W64-074",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
