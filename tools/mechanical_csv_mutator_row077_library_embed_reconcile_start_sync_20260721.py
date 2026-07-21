#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: sync TRK/ITEM-W64-077 Notes for library embed reconcile start.

Status stays in-progress / HOLD — never product COMPLETE. Reads live progress.json + PID.
Leaves Row074 HOLD and Row076 coverage_complete HOLD untouched.
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
LIVE = ROOT / "runtime_artifacts/embeddings/row077_library_20260720/progress.json"
OWNER = ROOT / "runtime_artifacts/embeddings/row077_library_20260720/FULL_RECONCILE_OWNER.txt"
EVID_DIR = ROOT / "Plan/Instructions/QA/Evidence/Wave64"
ANALYSIS = "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-077_semantic_audio_embeddings.json"
SUMMARY = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-077_ACCEPTED_INDEX_RETAINED_LIBRARY_EMBED_SUMMARY_20260721.json"
)
DELTA_REL = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-077_SEMANTIC_AUDIO_EMBEDDING_CURRENT_DELTA_20260719.json"
)
POST073_RANK = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-POST073_EXCLUSIVE_PCM_HANDOFF_RANKING_074_076_077_20260720.json"
)
PRIOR_ABSENT = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-077_LIBRARY_EMBED_RUNNER_ABSENT_AFTER_076_20260721T1119-0500.json"
)
ROW076_HOLD = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-076_REVERB_DRYNESS_RECONCILE_PROGRESS_20260721T1119-0500.json"
)

STATUS = "Blocked_Library_Embed_Reconcile_In_Progress_Heldout_Runtime_Bound"
STATUS_DECISION = "row077_library_embed_reconcile_in_progress_heldout_runtime_bound"
PROOF = "RUNTIME_PASS_BOUNDED"
BLOCKERS = [
    "FULL_LIBRARY_EMBEDDING_RECONCILIATION_IN_PROGRESS",
    "LIBRARY_AUTHORITY_NOT_GRANTED",
]
RESUME_CMD = (
    "compile_wave64_semantic_audio_embeddings.py --mode index-retained --resume "
    "--retained-runtime-dir runtime_artifacts/embeddings/row077_library_20260720"
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


def resolve_pid() -> int:
    if OWNER.is_file():
        for line in OWNER.read_text(encoding="utf-8").splitlines():
            if line.startswith("pid="):
                return int(line.split("=", 1)[1].strip())
    raise SystemExit("ROW077_OWNER_PID_ABSENT")


def assert_pid_alive(pid: int) -> None:
    out = subprocess.check_output(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        text=True,
        errors="replace",
    )
    if str(pid) not in out or "No tasks" in out:
        raise SystemExit(f"ROW077_PID_NOT_ALIVE:{pid}")


def main() -> None:
    tip = git_short()
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    counts = live["counts"]
    processed = int(counts["records_processed"])
    total = int(counts["records_total"])
    pct = 100.0 * processed / total
    assert live.get("complete") is False
    assert live.get("limit") is None, live.get("limit")
    assert processed >= 25, processed
    assert total == 39771
    assert processed < total
    assert int(counts.get("embed_pass", 0)) >= 1
    assert live.get("model_weights_loaded") is True
    assert live.get("device") in {"cuda", "cpu"}

    pid = resolve_pid()
    assert_pid_alive(pid)

    local = datetime.now(ZoneInfo("America/Chicago"))
    stamp_local = local.strftime("%Y%m%dT%H%M-0500")
    created_local = local.strftime("%Y-%m-%dT%H:%M:%S-05:00")

    stamp_name = f"TRK-W64-077_LIBRARY_EMBED_RECONCILE_PROGRESS_{stamp_local}.json"
    rel_stamp = f"Plan/Instructions/QA/Evidence/Wave64/{stamp_name}"
    stamp = {
        "created_at": created_local,
        "csv_stamp": "synced_by_primary_csv_mutator_row077_library_embed_reconcile_start_sync",
        "csv_sync_tip": tip,
        "evidence_id": f"TRK-W64-077-LIBRARY-EMBED-RECONCILE-START-{stamp_local}",
        "explicit_non_claims": [
            "COMPLETE",
            "product_completion",
            "library_authority",
            "full_library_coverage",
        ],
        "highest_proof_tier_achieved": PROOF,
        "item_id": "ITEM-W64-077",
        "library_authority": False,
        "process": {
            "action": "started_full_library_index_retained_embed_after_runner_landed",
            "alive": True,
            "command": RESUME_CMD,
            "exclusive_lane": "library_embed",
            "python": r"C:\Comfy_UI_Main\ComfyUI\.venv\Scripts\python.exe",
            "pid": pid,
            "prior_runner_absent": PRIOR_ABSENT,
            "prior_row076_gate": {
                "coverage_complete": True,
                "records": "39771/39771",
                "evidence": ROW076_HOLD,
            },
            "row074_left_alone": True,
            "row076_left_alone": True,
        },
        "product_completion_claimed": False,
        "progress": {
            "blocker_histogram": live.get("blocker_histogram", {}),
            "complete": False,
            "coverage_complete": False,
            "embed_blocked": int(counts.get("embed_blocked", 0)),
            "embed_pass": int(counts.get("embed_pass", 0)),
            "exact_blockers": int(counts.get("exact_blockers", 0)),
            "extension_histogram": live.get("extension_histogram", {}),
            "feature_pass_inputs": int(counts.get("feature_pass_inputs", 0)),
            "limit": None,
            "next_record_index": int(live["next_record_index"]),
            "pcm_sha_verified": int(counts.get("pcm_sha_verified", 0)),
            "percent_complete": round(pct, 2),
            "records_processed": processed,
            "records_total": total,
            "source_immutable_true": int(counts.get("source_immutable_true", 0)),
            "started_at": live.get("started_at"),
            "updated_at": live.get("updated_at"),
            "vectors_written": int(counts.get("vectors_written", 0)),
            "device": live.get("device"),
            "model_weights_loaded": True,
        },
        "proof_tier": PROOF,
        "remaining_blockers": BLOCKERS,
        "row_complete": False,
        "runtime_completion_claimed": False,
        "runtime_paths": {
            "owner_path": (
                "runtime_artifacts/embeddings/row077_library_20260720/FULL_RECONCILE_OWNER.txt"
            ),
            "progress_path": (
                "runtime_artifacts/embeddings/row077_library_20260720/progress.json"
            ),
            "records_path": (
                "runtime_artifacts/embeddings/row077_library_20260720/records.jsonl"
            ),
            "vectors_path": (
                "runtime_artifacts/embeddings/row077_library_20260720/vectors.jsonl"
            ),
            "retained_runtime_dir": "runtime_artifacts/embeddings/row077_library_20260720",
        },
        "safe_next_action": (
            "Leave exclusive Row077 owner running to coverage_complete; do not claim COMPLETE; "
            "do not invent vectors; leave Row074 HOLD and Row076 coverage_complete HOLD alone."
        ),
        "schema_version": "1.0",
        "source_commit": tip,
        "status": "HOLD_LIBRARY_EMBED_RECONCILE_IN_PROGRESS_HELDOUT_WEIGHTS_RUNTIME_BOUND",
        "tracker_id": "TRK-W64-077",
        "evidence_links": [ANALYSIS, SUMMARY, DELTA_REL, POST073_RANK, PRIOR_ABSENT, ROW076_HOLD],
    }
    stamp_path = EVID_DIR / stamp_name
    stamp_path.write_text(json.dumps(stamp, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    notes = (
        f"IN_PROGRESS: exclusive Row077 library embed reconcile started after landing "
        f"--mode index-retained --resume runner; PID {pid} alive; progress "
        f"{processed}/{total} ({pct:.2f}%); embed_pass={counts.get('embed_pass')}; "
        f"device={live.get('device')}; limit=null; complete=false; "
        f"runtime=runtime_artifacts/embeddings/row077_library_20260720; "
        f"held-out RUNTIME_PASS_BOUNDED retained; Row074 HOLD left alone; "
        f"Row076 coverage_complete HOLD left alone; no COMPLETE; no invented vectors. "
        f"Blockers: {'|'.join(BLOCKERS)}. "
        f"Evidence: {rel_stamp}; {ANALYSIS}; {SUMMARY}; {PRIOR_ABSENT}; {POST073_RANK}."
    )

    def mut_tracker(row: dict[str, str]) -> None:
        row["Status"] = STATUS
        row["Status_Decision"] = STATUS_DECISION
        row["Notes"] = notes
        row["Output_Artifact"] = (
            f"{ANALYSIS}; {rel_stamp}; {SUMMARY}; "
            "runtime_artifacts/embeddings/row077_library_20260720/progress.json"
        )

    def mut_item(row: dict[str, str]) -> None:
        row["Status"] = STATUS
        row["Notes"] = notes

    rewrite(TRACKER, "Tracker_ID", "TRK-W64-077", mut_tracker)
    rewrite(ITEMS, "Item_ID", "ITEM-W64-077", mut_item)
    print(
        json.dumps(
            {
                "pid": pid,
                "processed": processed,
                "total": total,
                "stamp": rel_stamp,
                "status": STATUS,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
