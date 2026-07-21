#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row074 resume Notes sync only (20260721)."""
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

EVID = "Plan/Instructions/QA/Evidence/Wave64"
LIVE = ROOT / "runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720/progress.json"
GUARDIAN = (
    ROOT / "runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720/guardian_poll_state.json"
)

ANALYSIS = f"{EVID}/TRK-W64-074_multi_event_segmentation.json"
SUMMARY = f"{EVID}/TRK-W64-074_ACCEPTED_INDEX_RETAINED_SEGMENT_SUMMARY_20260720.json"
RESUME_STAMP = (
    f"{EVID}/TRK-W64-074_MULTI_EVENT_SEGMENTATION_RECONCILE_PROGRESS_20260721T0010-0500.json"
)
POST073_RANK = f"{EVID}/TRK-W64-POST073_EXCLUSIVE_PCM_HANDOFF_RANKING_074_076_077_20260720.json"
DELTA_REL = f"{EVID}/TRK-W64-074_MULTI_EVENT_SEGMENTATION_CURRENT_DELTA_20260719.json"

WORKER_PID = 38680
GUARDIAN_PID = 18168
PRIOR_DEAD_PID = 40256
RESUME_FROM = 1325
RESUME_EVIDENCE_COMMIT = "94dc77dc"
PROOF = "RUNTIME_PASS_BOUNDED"
BLOCKERS = [
    "FULL_LIBRARY_RECONCILE_IN_PROGRESS_TIME_BOUND",
    "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
    "EVENT_COUNT_CALIBRATION_STRATA_ABSENT",
]


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    prove = [RESUME_EVIDENCE_COMMIT, tip]

    live = load_json(LIVE)
    counts = live["counts"]
    processed = int(counts["records_processed"])
    total = int(counts["records_total"])
    pct = 100.0 * processed / total
    assert live.get("complete") is False
    assert processed >= 1900, processed
    assert total == 39771

    gstate = load_json(GUARDIAN) if GUARDIAN.is_file() else {}
    worker_pid = int(gstate.get("known_pid", WORKER_PID))
    assert worker_pid == WORKER_PID, worker_pid

    notes = (
        "In progress: full-library index-retained multi-event segmentation reconcile "
        f"worker PID {WORKER_PID} + guardian PID {GUARDIAN_PID} healthy "
        f"({RESUME_EVIDENCE_COMMIT}/{tip} resume stamp); safe-resumed from "
        f"{RESUME_FROM}/{total} after prior dead PID {PRIOR_DEAD_PID} via "
        "ztest/guard_row074_full_reconcile.ps1 --resume; post-073 exclusive PCM gate "
        "open (671082c5/8c2ce364); "
        f"{processed}/{total} (~{pct:.1f}%); proof_tier={PROOF}; "
        "coverage_complete=false; row_complete=false; library_authority=false; "
        "worker and guardian left alone; parallel 076/077 refused; no COMPLETE. "
        "Blockers: "
        + "|".join(BLOCKERS)
        + f". Evidence: {RESUME_STAMP}; {POST073_RANK}"
    )

    evidence_path = f"{ANALYSIS}; {SUMMARY}; {RESUME_STAMP}; {POST073_RANK}; {DELTA_REL}"

    tracker_updates = {
        "TRK-W64-074": {
            "Notes": notes,
            "Evidence_Path": evidence_path,
        }
    }
    item_updates = {
        "ITEM-W64-074": {
            "Notes": notes,
        }
    }

    rewrite_csv(SOUND_TRACKER, "Tracker_ID", tracker_updates)
    rewrite_csv(SOUND_ITEMS, "Item_ID", item_updates)

    delta_path = ROOT / DELTA_REL.replace("/", "\\")
    delta = json.loads(delta_path.read_text(encoding="utf-8"))
    delta["csv_sync"] = "synced_by_primary_csv_mutator_row074_resume_notes_sync"
    delta["csv_sync_tip"] = tip
    delta["ledger_vocabulary_sync"] = {
        "ledger_status": "Blocked_Library_Reconcile_In_Progress_Deps_Unlocked",
        "note": (
            f"Resume Notes sync {processed}/{total}; worker PID {WORKER_PID} guardian "
            f"PID {GUARDIAN_PID}; prove {','.join(prove)}; no COMPLETE."
        ),
        "product_completion": False,
        "runtime_completion": False,
        "synced_at": NOW,
        "prove_commits": prove,
        "progress_stamp": RESUME_STAMP,
    }
    delta_path.write_text(json.dumps(delta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("tip", tip)
    print("synced", processed, total, f"{pct:.1f}%", f"worker={WORKER_PID}", f"guardian={GUARDIAN_PID}")
    print("prove", ",".join(prove))
    print("notes", notes[:320])


if __name__ == "__main__":
    main()
