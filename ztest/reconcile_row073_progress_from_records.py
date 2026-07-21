#!/usr/bin/env python3
"""One-shot Row073 progress.json recount from records.jsonl (Row075 pattern)."""

from __future__ import annotations

import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime_artifacts/usable_bounds/row073_index_retained_20260720"
PROGRESS_PATH = RUNTIME / "progress.json"
RECORDS_PATH = RUNTIME / "records.jsonl"
OWNER_PATH = RUNTIME / "FULL_RECONCILE_OWNER.txt"


def main() -> None:
    spec = importlib.util.spec_from_file_location(
        "ubd",
        ROOT / "Plan/07_IMPLEMENTATION/scripts/analyze_wave64_usable_bounds_decay.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup = RUNTIME / f"progress.json.bak_pre_reconcile_{stamp}"
    shutil.copy2(PROGRESS_PATH, backup)
    old = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    counts, blocker_histogram, extension_histogram, processed_paths = (
        mod._rebuild_retained_bounds_aggregates_from_records(RECORDS_PATH)
    )
    counts["records_total"] = int((old.get("counts") or {}).get("records_total") or 39771)
    old_next = int(old.get("next_record_index") or 0)
    new_next = max(old_next, len(processed_paths))
    payload = dict(old)
    payload["counts"] = counts
    payload["blocker_histogram"] = blocker_histogram
    payload["extension_histogram"] = extension_histogram
    payload["next_record_index"] = new_next
    payload["complete"] = False
    payload["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload["reconcile_note"] = {
        "method": "recount_from_records_jsonl_row075_pattern",
        "prior_next_record_index": old_next,
        "prior_records_processed": int((old.get("counts") or {}).get("records_processed") or 0),
        "records_jsonl_unique_paths": len(processed_paths),
        "advanced_next_record_index_to": new_next,
        "records_not_truncated": True,
        "stale_owner_pid_cleared": 20200,
    }
    PROGRESS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    OWNER_PATH.write_text(
        "owner=analyze_wave64_usable_bounds_decay.py\n"
        f"started={datetime.now(timezone.utc).isoformat()}\n"
        "pid=PENDING_RELAUNCH\n"
        "command=analyze_wave64_usable_bounds_decay.py --mode index-retained --resume "
        "--retained-runtime-dir runtime_artifacts/usable_bounds/row073_index_retained_20260720\n"
        "lane=library_pcm_exclusive\n"
        "resume_after_pid_20200_death=true\n"
        "reconcile=recount_from_records_jsonl\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "backup": str(backup.relative_to(ROOT)).replace("\\", "/"),
                "prior_next": old_next,
                "prior_processed": int((old.get("counts") or {}).get("records_processed") or 0),
                "new_next": new_next,
                "new_processed": counts["records_processed"],
                "counts": counts,
                "blocker_histogram": blocker_histogram,
                "extension_histogram": extension_histogram,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
