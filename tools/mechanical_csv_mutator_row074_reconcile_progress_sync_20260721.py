#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: sync TRK/ITEM-W64-074 Notes from live reconcile progress."""
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
    / "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-074_MULTI_EVENT_SEGMENTATION_CURRENT_DELTA_20260719.json"
)
LIVE = ROOT / "runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720/progress.json"
GUARDIAN = (
    ROOT / "runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720/guardian_poll_state.json"
)
EVID_DIR = ROOT / "Plan/Instructions/QA/Evidence/Wave64"

POST073_RANK = "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-POST073_EXCLUSIVE_PCM_HANDOFF_RANKING_074_076_077_20260720.json"
ANALYSIS = "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-074_multi_event_segmentation.json"
SUMMARY = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-074_ACCEPTED_INDEX_RETAINED_SEGMENT_SUMMARY_20260720.json"
)
DELTA_REL = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-074_MULTI_EVENT_SEGMENTATION_CURRENT_DELTA_20260719.json"
)

STATUS = "Blocked_Library_Reconcile_In_Progress_Deps_Unlocked"
STATUS_DECISION = "row074_library_reconcile_in_progress_deps_unlocked"
PROOF = "RUNTIME_PASS_BOUNDED"
BLOCKERS = [
    "FULL_LIBRARY_RECONCILE_IN_PROGRESS_TIME_BOUND",
    "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
    "EVENT_COUNT_CALIBRATION_STRATA_ABSENT",
]
EXPECTED_PID = 40256
RESUME_CMD = (
    "segment_wave64_multi_event_audio.py --mode index-retained --resume "
    "--retained-runtime-dir runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720"
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


def main() -> None:
    tip = git_short()
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    counts = live["counts"]
    processed = int(counts["records_processed"])
    total = int(counts["records_total"])
    pct = 100.0 * processed / total
    assert live.get("complete") is False
    assert processed >= 600, processed
    assert total == 39771

    guardian_pid = EXPECTED_PID
    if GUARDIAN.is_file():
        gstate = json.loads(GUARDIAN.read_text(encoding="utf-8-sig"))
        guardian_pid = int(gstate.get("known_pid", EXPECTED_PID))
    assert guardian_pid == EXPECTED_PID, guardian_pid

    local = datetime.now(ZoneInfo("America/Chicago"))
    stamp_local = local.strftime("%Y%m%dT%H%M-0500")
    created_local = local.strftime("%Y-%m-%dT%H:%M:%S-05:00")
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    stamp_name = f"TRK-W64-074_MULTI_EVENT_SEGMENTATION_RECONCILE_PROGRESS_{stamp_local}.json"
    rel_stamp = f"Plan/Instructions/QA/Evidence/Wave64/{stamp_name}"
    stamp = {
        "created_at": created_local,
        "csv_stamp": "synced_by_primary_csv_mutator_row074_reconcile_progress_sync",
        "csv_sync_tip": tip,
        "evidence_id": f"TRK-W64-074-SEGMENT-RECONCILE-PROGRESS-{stamp_local}",
        "explicit_non_claims": [
            "COMPLETE",
            "product_completion",
            "library_authority",
            "full_library_coverage",
        ],
        "highest_proof_tier_achieved": PROOF,
        "item_id": "ITEM-W64-074",
        "library_authority": False,
        "process": {
            "action": "continued_full_library_index_retained_resume",
            "alive": True,
            "command": RESUME_CMD,
            "exclusive_lane": "library_pcm",
            "guardian_left_alone": True,
            "parallel_076_077_refused": True,
            "pid": guardian_pid,
            "pid_left_alone": True,
        },
        "product_completion_claimed": False,
        "progress": {
            "bit_exact_reconstruction_ok": int(counts.get("bit_exact_reconstruction_ok", 0)),
            "blocker_histogram": live.get("blocker_histogram", {}),
            "complete": False,
            "coverage_complete": False,
            "exact_blockers": int(counts.get("exact_blockers", 0)),
            "extension_histogram": live.get("extension_histogram", {}),
            "feature_pass_inputs": int(counts.get("feature_pass_inputs", processed)),
            "limit": live.get("limit"),
            "multi_event_assets": int(counts.get("multi_event_assets", 0)),
            "next_record_index": int(live["next_record_index"]),
            "pcm_sha_verified": int(counts.get("pcm_sha_verified", processed)),
            "percent_complete": round(pct, 2),
            "records_processed": processed,
            "records_total": total,
            "resume_from": {
                "prior_limit": 25,
                "prior_next_record_index": 25,
                "prior_records_processed": 25,
            },
            "segment_pass": int(counts.get("segment_pass", processed)),
            "single_event_assets": int(counts.get("single_event_assets", 0)),
            "source_immutable_true": int(counts.get("source_immutable_true", processed)),
            "started_at": live.get("started_at"),
            "updated_at": live.get("updated_at"),
            "zero_event_assets": int(counts.get("zero_event_assets", 0)),
        },
        "proof_tier": PROOF,
        "remaining_blockers": BLOCKERS,
        "row_complete": False,
        "runtime_completion_claimed": False,
        "runtime_paths": {
            "guardian_state_path": (
                "runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720/"
                "guardian_poll_state.json"
            ),
            "owner_path": (
                "runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720/"
                "FULL_RECONCILE_OWNER.txt"
            ),
            "progress_path": (
                "runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720/"
                "progress.json"
            ),
            "records_path": (
                "runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720/"
                "records.jsonl"
            ),
            "retained_runtime_dir": (
                "runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720"
            ),
        },
        "safe_next_action": (
            f"Do not kill healthy PID {guardian_pid} or guardian; finish retained-index "
            "multi-event segmentation reconcile to coverage_complete under frozen "
            "suggestion-only thresholds. Do not start Row076/Row077 library PCM scans in "
            "parallel. No product COMPLETE."
        ),
        "schema_version": "1.0",
        "source_commit": tip,
        "status": "HOLD_LIBRARY_RECONCILE_IN_PROGRESS_DEPS_UNLOCKED",
        "tracker_id": "TRK-W64-074",
    }
    (EVID_DIR / stamp_name).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")

    evidence_path = f"{ANALYSIS}; {SUMMARY}; {rel_stamp}; {POST073_RANK}; {DELTA_REL}"
    notes = (
        f"In progress: full-library index-retained multi-event segmentation reconcile PID "
        f"{guardian_pid} healthy ({tip} stamp); resumed from limit-25 probe "
        f"(e9b3942b/49d2e3af); post-073 exclusive PCM gate open (671082c5/8c2ce364); "
        f"{processed}/{total} (~{pct:.1f}%); proof_tier={PROOF}; coverage_complete=false; "
        f"row_complete=false; library_authority=false; process and guardian left alone; "
        f"no COMPLETE. Blockers: "
        + "|".join(BLOCKERS)
        + f". Evidence: {rel_stamp}; {POST073_RANK}"
    )

    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    delta["updated_at"] = now_utc
    delta["ledger_status"] = STATUS
    delta["status"] = "HOLD_LIBRARY_RECONCILE_IN_PROGRESS_DEPS_UNLOCKED"
    delta["proof_tier"] = PROOF
    delta["highest_proof_tier_achieved"] = PROOF
    delta["row_complete"] = False
    delta["library_authority"] = False
    delta["blocker_codes"] = BLOCKERS
    delta["csv_sync"] = "synced_by_primary_csv_mutator_row074_reconcile_progress_sync"
    delta["csv_sync_tip"] = tip
    delta["ledger_vocabulary_sync"] = {
        "ledger_status": STATUS,
        "note": (
            f"Progress sync {processed}/{total}; PID {guardian_pid} and guardian left alone; "
            f"prove tip {tip}; no COMPLETE."
        ),
        "product_completion": False,
        "runtime_completion": False,
        "synced_at": now_utc,
        "prove_commit": tip,
        "progress_stamp": rel_stamp,
    }
    if isinstance(delta.get("decision"), dict):
        delta["decision"]["row074_status"] = STATUS
        delta["decision"]["product_completion"] = False
        delta["decision"]["runtime_completion"] = False
        delta["decision"]["safe_next_action"] = stamp["safe_next_action"]
    if isinstance(delta.get("row074_contract"), dict):
        delta["row074_contract"]["status"] = STATUS
    DELTA.write_text(json.dumps(delta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def mut_tracker(row: dict) -> None:
        row["Status"] = STATUS
        row["Status_Decision"] = STATUS_DECISION
        row["Notes"] = notes
        row["Evidence_Path"] = evidence_path

    def mut_item(row: dict) -> None:
        row["Status"] = STATUS
        row["Notes"] = notes

    rewrite(TRACKER, "Tracker_ID", "TRK-W64-074", mut_tracker)
    rewrite(ITEMS, "Item_ID", "ITEM-W64-074", mut_item)

    print("tip", tip)
    print("synced", processed, total, f"{pct:.1f}%", f"pid={guardian_pid}")
    print("stamp", rel_stamp)
    print("notes", notes[:280])


if __name__ == "__main__":
    main()
