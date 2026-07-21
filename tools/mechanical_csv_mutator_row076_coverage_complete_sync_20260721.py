#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row076 coverage_complete HOLD Notes sync (no product COMPLETE).

Asserts progress.json complete=true / 39771/39771 / limit=null and PID 31808 gone.
Does not invent Row077 library embed start; records exact runner-absent blocker only.
"""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(r"C:\Comfy_UI_Main")
TRACKER = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_TRACKER_ROWS.csv"
ITEMS = ROOT / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_ITEM_ROWS.csv"
DELTA = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-076_REVERB_DRYNESS_CURRENT_DELTA_20260719.json"
)
LIVE = ROOT / "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/progress.json"
RECEIPT = (
    ROOT
    / "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/retained_index_reverb_receipt.json"
)
EVID_DIR = ROOT / "Plan/Instructions/QA/Evidence/Wave64"

POST073_RANK = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-POST073_EXCLUSIVE_PCM_HANDOFF_RANKING_074_076_077_20260720.json"
)
ANALYSIS = "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-076_audio_reverb_dryness_estimation.json"
SUMMARY = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-076_ACCEPTED_INDEX_RETAINED_REVERB_SUMMARY_20260720.json"
)
DELTA_REL = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-076_REVERB_DRYNESS_CURRENT_DELTA_20260719.json"
)
PRIOR_PROGRESS = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-076_REVERB_DRYNESS_RECONCILE_PROGRESS_20260721T1045-0500.json"
)
ROW074_HOLD = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-074_MULTI_EVENT_SEGMENTATION_RECONCILE_PROGRESS_20260721T0252-0500.json"
)

HOLD_STATUS = "HOLD_LIBRARY_THRESHOLDS_AND_ROOM_CALIBRATION_ABSENT_RECONCILE_COMPLETE"
LEDGER_STATUS = "Blocked_Library_Thresholds_And_Room_Calibration_Absent_Reconcile_Complete"
STATUS_DECISION = "row076_library_thresholds_and_room_calibration_absent_reconcile_complete"
PROOF = "RUNTIME_PASS_BOUNDED"
BLOCKERS = [
    "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
    "REPRESENTATIVE_ROOM_SOURCE_CALIBRATION_ABSENT",
    "DOUBLE_REVERB_GUARD_LIBRARY_ENFORCEMENT_ABSENT",
]
RESUME_CMD = (
    "analyze_wave64_audio_reverb_dryness.py --mode index-retained --resume "
    "--retained-runtime-dir runtime_artifacts/reverb_dryness/row076_index_retained_20260720"
)
EXPECTED_PID = 31808
CSV_STAMP = "synced_by_primary_csv_mutator_row076_coverage_complete_sync"

# Row077: established post073 lane — library mode is blocker-packet only (no resume runner).
ROW077_BLOCKER_CODES = [
    "EMBEDDING_INDEX_LIBRARY_RUNTIME_ABSENT",
    "FULL_LIBRARY_EMBEDDING_RECONCILIATION_ABSENT",
]
ROW077_STATUS = "Blocked_Library_Embedding_Runner_Absent_Heldout_Runtime_Bound"
ROW077_STATUS_DECISION = "row077_library_embedding_runner_absent_heldout_runtime_bound"
ROW077_YIELD_PRIOR = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-077_LIBRARY_EMBED_YIELD_ROW073_CONTENTION_20260720T0934-0500.json"
)


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


def rewrite(path: Path, id_col: str, target_id: str, mut) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    assert fields
    found = False
    for row in rows:
        if row[id_col] == target_id:
            mut(row)
            found = True
    assert found, target_id
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def assert_pid_dead(pid: int) -> None:
    out = subprocess.check_output(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        text=True,
        errors="replace",
    )
    if str(pid) in out and "No tasks" not in out:
        raise SystemExit(f"ROW076_PID_STILL_ALIVE:{pid}")


def main() -> None:
    tip = git_short()
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    analysis = json.loads((ROOT / ANALYSIS).read_text(encoding="utf-8"))
    counts = live["counts"]
    processed = int(counts["records_processed"])
    total = int(counts["records_total"])

    assert live.get("complete") is True
    assert live.get("limit") is None, live.get("limit")
    assert processed == total == 39771
    assert int(live["next_record_index"]) == 39771
    assert receipt.get("coverage_complete") is True
    assert receipt.get("runtime_completion_claimed") is True
    assert analysis.get("status") == HOLD_STATUS
    assert analysis.get("runtime_completion_claimed") is True
    assert_pid_dead(EXPECTED_PID)

    local = datetime.now(ZoneInfo("America/Chicago"))
    stamp_local = local.strftime("%Y%m%dT%H%M-0500")
    created_local = local.strftime("%Y-%m-%dT%H:%M:%S-05:00")
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    stamp_name = f"TRK-W64-076_REVERB_DRYNESS_RECONCILE_PROGRESS_{stamp_local}.json"
    rel_stamp = f"Plan/Instructions/QA/Evidence/Wave64/{stamp_name}"
    stamp = {
        "created_at": created_local,
        "csv_stamp": CSV_STAMP,
        "csv_sync_tip": tip,
        "evidence_id": f"TRK-W64-076-REVERB-RECONCILE-COVERAGE-COMPLETE-{stamp_local}",
        "explicit_non_claims": [
            "COMPLETE",
            "product_completion",
            "library_authority",
            "library_threshold_authority",
        ],
        "highest_proof_tier_achieved": PROOF,
        "item_id": "ITEM-W64-076",
        "library_authority": False,
        "process": {
            "action": "finalize_full_library_index_retained_coverage_complete",
            "alive": False,
            "command": RESUME_CMD,
            "exclusive_lane": "library_pcm",
            "exit_cause": "clean_exit_coverage_complete",
            "pid": EXPECTED_PID,
            "prior_row074_gate": {
                "coverage_complete": True,
                "guardian_mode": "done_hold_stamped",
                "records": "39771/39771",
                "evidence": ROW074_HOLD,
            },
            "prior_progress_stamp": PRIOR_PROGRESS,
        },
        "product_completion_claimed": False,
        "progress": {
            "blocker_histogram": live.get("blocker_histogram", {}),
            "classification_ambiguous": int(counts.get("classification_ambiguous", 0)),
            "classification_dry": int(counts.get("classification_dry", 0)),
            "classification_wet": int(counts.get("classification_wet", 0)),
            "complete": True,
            "coverage_complete": True,
            "double_reverb_guard_enforced": int(counts.get("double_reverb_guard_enforced", 0)),
            "exact_blockers": int(counts.get("exact_blockers", 0)),
            "extension_histogram": live.get("extension_histogram", {}),
            "feature_pass_inputs": int(counts.get("feature_pass_inputs", 0)),
            "limit": None,
            "next_record_index": int(live["next_record_index"]),
            "pcm_sha_verified": int(counts.get("pcm_sha_verified", 0)),
            "percent_complete": 100.0,
            "records_processed": processed,
            "records_total": total,
            "reverb_pass": int(counts.get("reverb_pass", 0)),
            "source_immutable_true": int(counts.get("source_immutable_true", 0)),
            "started_at": live.get("started_at"),
            "updated_at": live.get("updated_at"),
        },
        "proof_tier": PROOF,
        "remaining_blockers": BLOCKERS,
        "row_complete": False,
        "runtime_completion_claimed": True,
        "runtime_paths": {
            "owner_path": (
                "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/"
                "FULL_RECONCILE_OWNER.txt"
            ),
            "progress_path": (
                "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/progress.json"
            ),
            "receipt_path": (
                "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/"
                "retained_index_reverb_receipt.json"
            ),
            "records_path": (
                "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/records.jsonl"
            ),
            "retained_runtime_dir": (
                "runtime_artifacts/reverb_dryness/row076_index_retained_20260720"
            ),
        },
        "safe_next_action": (
            "Full-library reverb/dryness reconcile is coverage_complete under frozen "
            "suggestion-only thresholds. Calibrate representative room/source strata and "
            "unfreeze threshold authority before Row076 acceptance or Row079 unlock. "
            "Row077 library embed runner remains absent — do not invent a start command. "
            "No product COMPLETE. Leave Row074 HOLD alone."
        ),
        "schema_version": "1.0",
        "source_commit": tip,
        "status": HOLD_STATUS,
        "tracker_id": "TRK-W64-076",
    }
    (EVID_DIR / stamp_name).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")

    row077_stamp_name = (
        f"TRK-W64-077_LIBRARY_EMBED_RUNNER_ABSENT_AFTER_076_{stamp_local}.json"
    )
    row077_rel = f"Plan/Instructions/QA/Evidence/Wave64/{row077_stamp_name}"
    row077_stamp = {
        "created_at": created_local,
        "csv_stamp": CSV_STAMP,
        "csv_sync_tip": tip,
        "evidence_id": f"TRK-W64-077-LIBRARY-EMBED-RUNNER-ABSENT-{stamp_local}",
        "explicit_non_claims": [
            "COMPLETE",
            "product_completion",
            "library_authority",
            "full_library_embedding_index_started",
            "invented_library_embed_command",
        ],
        "highest_proof_tier_achieved": PROOF,
        "item_id": "ITEM-W64-077",
        "library_authority": False,
        "full_library_embedding_index_started": False,
        "preconditions": {
            "row076_coverage_complete": True,
            "row076_alive": False,
            "row076_records": "39771/39771",
            "row076_status": HOLD_STATUS,
            "row076_evidence": rel_stamp,
            "row077_heldout_runtime_bound": True,
            "established_library_command": (
                "python Plan/07_IMPLEMENTATION/scripts/"
                "compile_wave64_semantic_audio_embeddings.py --mode library"
            ),
            "library_mode_behavior": "build_library_blocker_packet_only_no_resume_runner",
        },
        "action_taken": {
            "started_row077_full_library_embed": False,
            "reason": (
                "Post-073 exclusive ranking clears Row076, but compile_wave64_semantic_"
                "audio_embeddings.py --mode library still emits build_library_blocker_packet "
                "only; no --resume / index-retained full-library embed runner exists."
            ),
            "product_complete_claimed": False,
        },
        "blocker_codes": ROW077_BLOCKER_CODES,
        "prior_yield": ROW077_YIELD_PRIOR,
        "proof_tier": PROOF,
        "row_complete": False,
        "runtime_completion_claimed": False,
        "safe_next_action": (
            "Do not invent a Row077 library PCM command. Land a real --resume / "
            "index-retained library embed runner (disjoint tree "
            "runtime_artifacts/embeddings/row077_library_20260720) before starting. "
            "Held-out RUNTIME_PASS_BOUNDED remains bound. No COMPLETE."
        ),
        "schema_version": "1.0",
        "source_commit": tip,
        "status": "HOLD_LIBRARY_EMBEDDING_RUNNER_ABSENT_HELDOUT_RUNTIME_BOUND",
        "tracker_id": "TRK-W64-077",
    }
    (EVID_DIR / row077_stamp_name).write_text(
        json.dumps(row077_stamp, indent=2) + "\n", encoding="utf-8"
    )

    evidence_path = (
        f"{ANALYSIS}; {SUMMARY}; {rel_stamp}; {PRIOR_PROGRESS}; {POST073_RANK}; "
        f"{DELTA_REL}; {ROW074_HOLD}"
    )
    notes = (
        f"HOLD coverage_complete: full-library index-retained reverb/dryness reconcile "
        f"PID {EXPECTED_PID} clean_exit ({tip} coverage sync); {processed}/{total}; "
        f"limit=null; proof_tier={PROOF}; coverage_complete=true; "
        f"runtime_completion_claimed=true; row_complete=false; library_authority=false; "
        f"status={HOLD_STATUS}; no product COMPLETE. Remaining blockers: "
        + "|".join(BLOCKERS)
        + f". Row077 not started (library embed runner absent). Evidence: {rel_stamp}; "
        f"{PRIOR_PROGRESS}; {POST073_RANK}."
    )
    row077_notes = (
        f"HOLD: Row076 coverage_complete released exclusive PCM ({processed}/{total}); "
        f"held-out RUNTIME_PASS_BOUNDED retained; established "
        f"compile_wave64_semantic_audio_embeddings.py --mode library remains "
        f"build_library_blocker_packet-only (no --resume / full-library embed runner); "
        f"077 not started; no invented command; no COMPLETE. Blockers: "
        + "|".join(ROW077_BLOCKER_CODES)
        + f". Evidence: {row077_rel}; {rel_stamp}; {POST073_RANK}; {ROW077_YIELD_PRIOR}."
    )

    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    delta["updated_at"] = now_utc
    delta["ledger_status"] = LEDGER_STATUS
    delta["status"] = HOLD_STATUS
    delta["proof_tier"] = PROOF
    delta["highest_proof_tier_achieved"] = PROOF
    delta["row_complete"] = False
    delta["library_authority"] = False
    delta["runtime_completion_claimed"] = True
    delta["blocker_codes"] = BLOCKERS
    delta["csv_sync"] = CSV_STAMP
    delta["csv_sync_tip"] = tip
    delta["classification"] = (
        "ROW076_INDEX_RETAINED_COVERAGE_COMPLETE_THRESHOLDS_AND_ROOM_CALIBRATION_HELD"
    )
    delta["accepted_index_retained_reverb_runtime"] = {
        "authority": "accepted_index_retained_reverb_reconcile",
        "counts": counts,
        "coverage_complete": True,
        "limit": None,
        "proof_tier": PROOF,
        "runtime_receipt_path": (
            "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/"
            "retained_index_reverb_receipt.json"
        ),
        "status": "RUNTIME_PASS_BOUNDED_LIBRARY_THRESHOLDS_FROZEN",
        "summary_path": SUMMARY,
    }
    delta["ledger_vocabulary_sync"] = {
        "ledger_status": LEDGER_STATUS,
        "note": (
            f"Coverage complete {processed}/{total}; PID {EXPECTED_PID} exited clean; "
            f"prove tip {tip}; no COMPLETE; 077 blocker landed (runner absent)."
        ),
        "product_completion": False,
        "runtime_completion": True,
        "synced_at": now_utc,
        "prove_commit": tip,
        "progress_stamp": rel_stamp,
        "row077_blocker_stamp": row077_rel,
    }
    if isinstance(delta.get("decision"), dict):
        delta["decision"]["row076_status"] = LEDGER_STATUS
        delta["decision"]["product_completion"] = False
        delta["decision"]["runtime_completion"] = True
        delta["decision"]["safe_next_action"] = stamp["safe_next_action"]
    DELTA.write_text(json.dumps(delta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def mut_tracker_076(row: dict) -> None:
        row["Status"] = LEDGER_STATUS
        row["Status_Decision"] = STATUS_DECISION
        row["Notes"] = notes
        row["Evidence_Path"] = evidence_path

    def mut_item_076(row: dict) -> None:
        row["Status"] = LEDGER_STATUS
        row["Notes"] = notes

    def mut_tracker_077(row: dict) -> None:
        row["Status"] = ROW077_STATUS
        row["Status_Decision"] = ROW077_STATUS_DECISION
        row["Notes"] = row077_notes
        existing = row.get("Evidence_Path") or ""
        row["Evidence_Path"] = f"{row077_rel}; {rel_stamp}; {existing}".rstrip("; ")

    def mut_item_077(row: dict) -> None:
        row["Status"] = ROW077_STATUS
        row["Notes"] = row077_notes

    rewrite(TRACKER, "Tracker_ID", "TRK-W64-076", mut_tracker_076)
    rewrite(ITEMS, "Item_ID", "ITEM-W64-076", mut_item_076)
    rewrite(TRACKER, "Tracker_ID", "TRK-W64-077", mut_tracker_077)
    rewrite(ITEMS, "Item_ID", "ITEM-W64-077", mut_item_077)

    print("tip", tip)
    print("076_synced", processed, total, "coverage_complete=true", f"pid={EXPECTED_PID}_dead")
    print("stamp", rel_stamp)
    print("077_blocker", row077_rel)
    print("077_started", False)


if __name__ == "__main__":
    main()
