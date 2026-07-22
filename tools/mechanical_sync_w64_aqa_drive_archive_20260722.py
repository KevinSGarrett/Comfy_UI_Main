#!/usr/bin/env python3
"""Synchronize the accepted Drive archive and partial EC2 truth into W64-AQA-018."""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
STATUS = (
    "TRANSFER_AND_DRIVE_ARCHIVE_PASS_EC2_ARCHIVE_PARTIAL_LATENTSYNC_ENVIRONMENT_"
    "AND_IMPORTS_PASS_REMAINING_PACKAGE_AND_QUARANTINE_QUALIFICATION_PENDING"
)
EVIDENCE = "Plan/Tracker/Evidence/W64_AQA_GOOGLE_DRIVE_ARCHIVE_RECONCILIATION_20260722.json"
NOTES = (
    "RunPod byte transfer remains accepted at 56 files and 55,804,915,269 bytes plus three "
    "aliases. The accessible Drive archive is accepted at 335 unique payload files and "
    "395,510,389,604 bytes plus 27 evidence files; completed local and S3 classes are "
    "hash/content verified. EC2 remains partial with 51 retained Drive objects and 411 "
    "audited model files (281,349,317,254 bytes) outstanding. The stale F: Docker VHD "
    "independently rehashed equal, but execution policy blocked deletion before process start, "
    "so it remains present. Archive authority grants no runtime, workflow, quality, activation, "
    "or product authority."
)
RUNTIME_TRUTH = (
    "runpod_56_file_transfer_and_drive_335_file_accessible_archive_pass_ec2_archive_partial_"
    "411_model_files_remaining_latentsync_environment_imports_pass_no_model_load"
)
NEXT_ACTION = (
    "Continue the Row137 exact model-load gate on the sole current pod after a fresh storage "
    "budget and immutable rights-qualified fixture; separately resume EC2 archive only when "
    "g5 capacity or exact ModifyInstanceAttribute authority exists; keep quarantine inactive."
)


def head_text(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    return subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout.decode("utf-8-sig")


def write_text_atomic(path: Path, payload: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def update_csv(path: Path, key: str, identity: str, updates: dict[str, str]) -> None:
    lines = head_text(path).splitlines(keepends=True)
    fieldnames = next(csv.reader([lines[0]]))
    key_index = fieldnames.index(key)
    matches = 0
    output = [lines[0]]
    for line in lines[1:]:
        values = next(csv.reader([line]))
        if len(values) != len(fieldnames):
            raise RuntimeError(f"{path}: malformed or multiline CSV row")
        if values[key_index] == identity:
            row = dict(zip(fieldnames, values, strict=True))
            row.update(updates)
            buffer = io.StringIO(newline="")
            csv.writer(buffer, lineterminator="\n").writerow([row[name] for name in fieldnames])
            output.append(buffer.getvalue())
            matches += 1
        else:
            output.append(line)
    if matches != 1:
        raise RuntimeError(f"{path}: expected one {identity} row, found {matches}")
    write_text_atomic(path, "".join(output))


def main() -> int:
    update_csv(
        ROOT / "Plan/Items/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_ITEM_ROWS.csv",
        "Item_ID",
        "W64-AQA-018",
        {"Status": STATUS, "Notes": NOTES},
    )
    update_csv(
        ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_TRACKER_ROWS.csv",
        "Tracker_ID",
        "W64-AQA-018",
        {
            "Status": STATUS,
            "Runtime_Truth": RUNTIME_TRUTH,
            "Next_Action": NEXT_ACTION,
            "Evidence_Path": EVIDENCE,
        },
    )
    print("W64_AQA_DRIVE_ARCHIVE_RECONCILIATION_SYNCHRONIZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
