#!/usr/bin/env python3
"""Apply the hash-bound CV3 calibration to the affected Wave64 row ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_REL = "Plan/Instructions/QA/Evidence/Wave64/W64_CV3_EVAL_LOCAL_CALIBRATION_20260714T233144-0500.json"
EVIDENCE_SHA256 = "4ea6604d2336357cf67ee70ed133b2300d1b8b47ba6d4e48f6d42ab821cc66f0"
TRACKER_PATHS = (
    "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv",
    "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
)
ITEM_PATHS = (
    "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
)
ROW_SPECS = {
    "025": {
        "tracker_id": "TRK-W64-025",
        "item_id": "ITEM-W64-025",
        "status": "Blocked_Audio_Production_Runtime_Proof_Missing",
    },
    "027": {
        "tracker_id": "TRK-W64-027",
        "item_id": "ITEM-W64-027",
        "status": "Blocked_Voice_Dialogue_Production_Proof_Missing",
    },
    "031": {
        "tracker_id": "TRK-W64-031",
        "item_id": "ITEM-W64-031",
        "status": "Blocked_Strict_Audio_Production_Review_Proof_Missing",
    },
}
NOTE = (
    "Wave64 CV3 local calibration 2026-07-14: eleven adapter regressions pass; the immutable Parler "
    "candidate is bound to its packet and dialogue contract, WER is 0.10, and DNSMOS OVRL is 3.0586 "
    "at the 75th percentile of eight local reference clips. ERes2Net execution and cross-file scoring "
    "sanity are verified without speaker-identity labels. Candidate speaker identity, emotion-model "
    "evaluation, independent playback, production authority, row completion, and certification remain blocked."
)
COVERAGE_TAGS = (
    "cv3_eval_local_calibration_hash_bound",
    "speaker_identity_emotion_playback_authority_blocked",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_unique(current: str, value: str, separator: str) -> str:
    entries = [entry.strip() for entry in (current or "").split(separator) if entry.strip()]
    if value not in entries:
        entries.append(value)
    return separator.join(entries)


def update_csv(
    path: Path,
    key: str,
    evidence_field: str,
    specs: dict[str, dict],
    apply: bool,
) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    required_fields = {key, "Status", evidence_field, "Coverage_Audit_Status", "Notes"}
    missing = required_fields - set(fields)
    if missing:
        raise ValueError(f"{path} is missing fields: {sorted(missing)}")

    by_id = {spec[key]: spec for spec in specs.values()}
    changed = []
    for row in rows:
        row_id = row.get(key)
        if row_id not in by_id:
            continue
        spec = by_id[row_id]
        if row.get("Status") != spec["status"]:
            raise ValueError(f"{path} status drift for {row_id}: {row.get('Status')}")
        if "Status_Decision" in fields and row.get("Status_Decision") != spec["status"]:
            raise ValueError(f"{path} status decision drift for {row_id}: {row.get('Status_Decision')}")
        row[evidence_field] = append_unique(row.get(evidence_field, ""), EVIDENCE_REL, "; ")
        for tag in COVERAGE_TAGS:
            row["Coverage_Audit_Status"] = append_unique(row.get("Coverage_Audit_Status", ""), tag, "; ")
        row["Notes"] = append_unique(row.get("Notes", ""), NOTE, " | ")
        changed.append(
            {
                "id": row_id,
                "status": row["Status"],
                "evidence_linked": EVIDENCE_REL in row[evidence_field],
                "note_linked": NOTE in row["Notes"],
            }
        )
    if len(changed) != len(specs):
        raise ValueError(f"{path} matched {len(changed)} rows, expected {len(specs)}")

    if apply:
        temporary = path.with_name(f".{path.name}.cv3.tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return changed


def verify_evidence() -> dict:
    qa_path = ROOT / EVIDENCE_REL
    tracker_path = ROOT / "Plan/Tracker/Evidence/Wave64" / Path(EVIDENCE_REL).name
    for path in (qa_path, tracker_path):
        if not path.is_file() or sha256(path) != EVIDENCE_SHA256:
            raise ValueError(f"CV3 evidence hash mismatch: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("row_complete") is not False:
            raise ValueError(f"CV3 evidence must remain row-incomplete: {path}")
        acceptance = payload.get("acceptance", {})
        if acceptance.get("speaker_identity_claim_allowed") is not False:
            raise ValueError(f"CV3 evidence must block speaker identity: {path}")
        if acceptance.get("independent_playback_review_pass") is not False:
            raise ValueError(f"CV3 evidence must block playback review: {path}")
    return {"qa": str(qa_path), "tracker": str(tracker_path), "sha256": EVIDENCE_SHA256}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the verified updates; otherwise perform a dry run.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evidence = verify_evidence()
    tracker_specs = {
        key: {**value, "Tracker_ID": value["tracker_id"]} for key, value in ROW_SPECS.items()
    }
    item_specs = {key: {**value, "Item_ID": value["item_id"]} for key, value in ROW_SPECS.items()}
    results = {
        "mode": "apply" if args.apply else "dry_run",
        "evidence": evidence,
        "tracker": [
            {
                "path": path,
                "rows": update_csv(ROOT / path, "Tracker_ID", "Evidence_Path", tracker_specs, args.apply),
            }
            for path in TRACKER_PATHS
        ],
        "items": [
            {
                "path": path,
                "rows": update_csv(ROOT / path, "Item_ID", "Evidence_Required", item_specs, args.apply),
            }
            for path in ITEM_PATHS
        ],
    }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
