#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: sync TRK/ITEM-W64-076 Notes from live reconcile progress.

Status stays in-progress / HOLD — never product COMPLETE. Reads live progress.json + PID.
Does not kill PID 31808; does not start Row077; does not claim coverage_complete.
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
OWNER = ROOT / "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/FULL_RECONCILE_OWNER.txt"
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
ROW074_HOLD = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-074_MULTI_EVENT_SEGMENTATION_RECONCILE_PROGRESS_20260721T0252-0500.json"
)
PRIOR_START = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-076_REVERB_DRYNESS_RECONCILE_PROGRESS_20260721T0935-0500.json"
)

STATUS = "Blocked_Library_Reconcile_In_Progress_Deps_Unlocked"
STATUS_DECISION = "row076_library_reconcile_in_progress_deps_unlocked"
PROOF = "RUNTIME_PASS_BOUNDED"
BLOCKERS = [
    "FULL_LIBRARY_RECONCILE_IN_PROGRESS_TIME_BOUND",
    "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
    "REPRESENTATIVE_ROOM_SOURCE_CALIBRATION_ABSENT",
    "DOUBLE_REVERB_GUARD_LIBRARY_ENFORCEMENT_ABSENT",
]
RESUME_CMD = (
    "analyze_wave64_audio_reverb_dryness.py --mode index-retained --resume "
    "--retained-runtime-dir runtime_artifacts/reverb_dryness/row076_index_retained_20260720"
)
EXPECTED_PID = 31808
CSV_STAMP = "synced_by_primary_csv_mutator_row076_reconcile_progress_sync"


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


def resolve_pid() -> int:
    if OWNER.is_file():
        for line in OWNER.read_text(encoding="utf-8").splitlines():
            if line.startswith("pid="):
                return int(line.split("=", 1)[1].strip())
    return EXPECTED_PID


def assert_pid_alive(pid: int) -> None:
    out = subprocess.check_output(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        text=True,
        errors="replace",
    )
    if str(pid) not in out or "No tasks" in out:
        raise SystemExit(f"ROW076_PID_NOT_ALIVE:{pid}")


def main() -> None:
    tip = git_short()
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    counts = live["counts"]
    processed = int(counts["records_processed"])
    total = int(counts["records_total"])
    pct = 100.0 * processed / total
    assert live.get("complete") is False
    assert live.get("limit") is None, live.get("limit")
    assert processed >= 250, processed
    assert total == 39771
    assert processed < total

    pid = resolve_pid()
    assert pid == EXPECTED_PID, pid
    assert_pid_alive(pid)

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
        "evidence_id": f"TRK-W64-076-REVERB-RECONCILE-PROGRESS-{stamp_local}",
        "explicit_non_claims": [
            "COMPLETE",
            "product_completion",
            "library_authority",
            "full_library_coverage",
        ],
        "highest_proof_tier_achieved": PROOF,
        "item_id": "ITEM-W64-076",
        "library_authority": False,
        "process": {
            "action": "continued_full_library_index_retained_resume_notes_only_sync",
            "alive": True,
            "command": RESUME_CMD,
            "exclusive_lane": "library_pcm",
            "parallel_077_refused": True,
            "pid": pid,
            "pid_left_alone": True,
            "prior_row074_gate": {
                "coverage_complete": True,
                "guardian_mode": "done_hold_stamped",
                "records": "39771/39771",
                "evidence": ROW074_HOLD,
            },
            "prior_start_stamp": PRIOR_START,
            "resumed_from_probe": {
                "prior_limit": 25,
                "prior_records_processed": 25,
            },
        },
        "product_completion_claimed": False,
        "progress": {
            "blocker_histogram": live.get("blocker_histogram", {}),
            "classification_ambiguous": int(counts.get("classification_ambiguous", 0)),
            "classification_dry": int(counts.get("classification_dry", 0)),
            "classification_wet": int(counts.get("classification_wet", 0)),
            "complete": False,
            "coverage_complete": False,
            "double_reverb_guard_enforced": int(counts.get("double_reverb_guard_enforced", 0)),
            "exact_blockers": int(counts.get("exact_blockers", 0)),
            "extension_histogram": live.get("extension_histogram", {}),
            "feature_pass_inputs": int(counts.get("feature_pass_inputs", processed)),
            "limit": None,
            "next_record_index": int(live["next_record_index"]),
            "pcm_sha_verified": int(counts.get("pcm_sha_verified", processed)),
            "percent_complete": round(pct, 2),
            "records_processed": processed,
            "records_total": total,
            "reverb_pass": int(counts.get("reverb_pass", processed)),
            "source_immutable_true": int(counts.get("source_immutable_true", processed)),
            "started_at": live.get("started_at"),
            "updated_at": live.get("updated_at"),
        },
        "proof_tier": PROOF,
        "remaining_blockers": BLOCKERS,
        "row_complete": False,
        "runtime_completion_claimed": False,
        "runtime_paths": {
            "owner_path": (
                "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/"
                "FULL_RECONCILE_OWNER.txt"
            ),
            "progress_path": (
                "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/progress.json"
            ),
            "records_path": (
                "runtime_artifacts/reverb_dryness/row076_index_retained_20260720/records.jsonl"
            ),
            "retained_runtime_dir": (
                "runtime_artifacts/reverb_dryness/row076_index_retained_20260720"
            ),
        },
        "safe_next_action": (
            f"Do not kill healthy PID {pid}; finish retained-index reverb/dryness reconcile "
            "to coverage_complete under frozen suggestion-only thresholds. Do not start "
            "Row077 library PCM until Row076 coverage_complete. No product COMPLETE. "
            "Avoid another Row010 PuLID lock-trait envelope (FACE/SIDE/BODYFORWARD/REAR "
            "already solo_lock=0.0). Row084 remains blocked on external gold masks."
        ),
        "schema_version": "1.0",
        "source_commit": tip,
        "status": "HOLD_LIBRARY_RECONCILE_IN_PROGRESS_DEPS_UNLOCKED",
        "tracker_id": "TRK-W64-076",
    }
    (EVID_DIR / stamp_name).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")

    evidence_path = (
        f"{ANALYSIS}; {SUMMARY}; {rel_stamp}; {PRIOR_START}; {POST073_RANK}; "
        f"{DELTA_REL}; {ROW074_HOLD}"
    )
    notes = (
        f"In progress: full-library index-retained reverb/dryness reconcile PID {pid} healthy "
        f"({tip} progress sync); resumed from limit-25 probe after Row074 coverage_complete HOLD "
        f"(39771/39771 done_hold_stamped); post-073 exclusive PCM #2; "
        f"{processed}/{total} (~{pct:.1f}%); limit=null; proof_tier={PROOF}; "
        f"coverage_complete=false; row_complete=false; library_authority=false; "
        f"do not start 077; no COMPLETE. Blockers: "
        + "|".join(BLOCKERS)
        + f". Evidence: {rel_stamp}; {PRIOR_START}; {POST073_RANK}."
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
    delta["csv_sync"] = CSV_STAMP
    delta["csv_sync_tip"] = tip
    delta["ledger_vocabulary_sync"] = {
        "ledger_status": STATUS,
        "note": (
            f"Reconcile progress sync {processed}/{total}; PID {pid} left alone; "
            f"prove tip {tip}; no COMPLETE; 077 not started."
        ),
        "product_completion": False,
        "runtime_completion": False,
        "synced_at": now_utc,
        "prove_commit": tip,
        "progress_stamp": rel_stamp,
    }
    if isinstance(delta.get("decision"), dict):
        delta["decision"]["row076_status"] = STATUS
        delta["decision"]["product_completion"] = False
        delta["decision"]["runtime_completion"] = False
        delta["decision"]["safe_next_action"] = stamp["safe_next_action"]
    DELTA.write_text(json.dumps(delta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def mut_tracker(row: dict) -> None:
        row["Status"] = STATUS
        row["Status_Decision"] = STATUS_DECISION
        row["Notes"] = notes
        row["Evidence_Path"] = evidence_path

    def mut_item(row: dict) -> None:
        row["Status"] = STATUS
        row["Notes"] = notes

    rewrite(TRACKER, "Tracker_ID", "TRK-W64-076", mut_tracker)
    rewrite(ITEMS, "Item_ID", "ITEM-W64-076", mut_item)

    print("tip", tip)
    print("synced", processed, total, f"{pct:.1f}%", f"pid={pid}")
    print("stamp", rel_stamp)
    print("notes", notes[:360])


if __name__ == "__main__":
    main()
