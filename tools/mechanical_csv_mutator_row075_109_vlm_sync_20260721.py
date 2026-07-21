#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row075/109 VLM Notes sync only (20260721)."""
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
ROW075_VLM = (
    f"{EVID}/TRK-W64-075_VLM_AUTONOMOUS_STRATA_LABEL_PACKET_20260720T231859-0500.json"
)
ROW075_DELTA = f"{EVID}/TRK-W64-075_AUDIO_QUALITY_DEFECT_CURRENT_DELTA_20260719.json"
ROW109_VLM = (
    f"{EVID}/TRK-W64-109_VLM_SYNTHETIC_CORPUS_PATH_PACKET_20260720T231855-0500.json"
)
ROW109_CHECKLIST = (
    f"{EVID}/TRK-W64-109_CLASS_F_STEP2_GENUINE_MEDIA_ACQUISITION_RIGHTS_CHECKLIST_PACKET_20260720.json"
)
ROW109_DELTA = f"{EVID}/TRK-W64-109_AUDIO_BENCHMARK_CORPUS_CURRENT_DELTA_20260720.json"


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8"))


def dump_json(rel: str, obj: dict) -> None:
    path = ROOT / rel.replace("/", "\\")
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    prove = ["561559d5", "cd787d5b", tip]

    row075_notes = (
        "VLM_METADATA autonomous strata labeling landed (561559d5): 13-candidate shortlist "
        "retained; vlm_labeled=6/vlm_blocked=2/live_vlm=8; "
        "synthetic_fixture_truth_labeled_retained=5; threshold_authority FROZEN; blockers "
        "retained (CALIBRATED_LIBRARY_DEFECT_STRATA_ABSENT|"
        "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY|"
        "LIBRARY_DEFECT_TRUTH_HUMAN_GOLD_LABELS_ABSENT); row_complete=false; "
        "library_authority=false; no COMPLETE. Leave Row074 PCM alone. "
        f"Evidence: {ROW075_VLM}; {ROW075_DELTA}"
    )

    row109_notes = (
        "VLM_SYNTHETIC autonomous corpus path landed (cd787d5b): 31 synthetic-fixture cases "
        "annotated (4 live_vlm/27 metadata_proxy_fallback); step2_still_blocked; "
        "genuine-media/rights production gates retained "
        "(GENUINE_ANNOTATED_MEDIA_CORPUS_ABSENT|COMBINED_FRAME_CONTACT_AUDIO_REVIEW_ABSENT|"
        "PRODUCTION_BENCHMARK_AUTHORITY_ABSENT|HELD_OUT_RUNTIME_PROOF_ABSENT); proof_tier="
        "AUTONOMOUS_VLM_SYNTHETIC_CORPUS_PATH_BOUNDED; row_complete=false; "
        "library_authority=false; no COMPLETE. "
        f"Evidence: {ROW109_VLM}; {ROW109_CHECKLIST}; {ROW109_DELTA}"
    )

    row075_evidence = (
        f"{EVID}/TRK-W64-075_audio_defect_classification.json; "
        f"{EVID}/TRK-W64-075_AUDIO_DEFECT_RECONCILE_PROGRESS_20260720T0929-0500.json; "
        f"{EVID}/TRK-W64-075_LIBRARY_BENCHMARK_STRATA_CANDIDATE_PACKET_20260720.json; "
        f"{ROW075_DELTA}; {ROW075_VLM}"
    )
    row109_evidence = f"{ROW109_CHECKLIST}; {ROW109_VLM}; {ROW109_DELTA}"

    sound_tracker_updates = {
        "TRK-W64-075": {
            "Notes": row075_notes,
            "Evidence_Path": row075_evidence,
        },
        "TRK-W64-109": {
            "Notes": row109_notes,
            "Evidence_Path": row109_evidence,
        },
    }
    sound_item_updates = {
        "ITEM-W64-075": {"Notes": row075_notes},
        "ITEM-W64-109": {"Notes": row109_notes},
    }

    rewrite_csv(SOUND_TRACKER, "Tracker_ID", sound_tracker_updates)
    rewrite_csv(SOUND_ITEMS, "Item_ID", sound_item_updates)

    for rel in (ROW075_DELTA, ROW109_DELTA):
        delta = load_json(rel)
        delta["csv_sync"] = "synced_by_primary_csv_mutator_row075_109_vlm"
        delta["csv_sync_tip"] = tip
        delta["ledger_vocabulary_sync"] = {
            "note": f"Mechanical CSV mutator Row075/109 VLM sync from {','.join(prove)}; no COMPLETE.",
            "product_completion": False,
            "synced_at": NOW,
            "prove_commits": prove,
        }
        dump_json(rel, delta)

    tracker_delta = ROOT / "Plan/Tracker/Evidence/Wave64/TRK-W64-075_AUDIO_QUALITY_DEFECT_CURRENT_DELTA_20260719.json"
    if tracker_delta.exists():
        td = json.loads(tracker_delta.read_text(encoding="utf-8"))
        td["csv_sync"] = "synced_by_primary_csv_mutator_row075_109_vlm"
        td["csv_sync_tip"] = tip
        tracker_delta.write_text(json.dumps(td, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("tip", tip)
    print("synced Row075 VLM_METADATA Notes (561559d5)")
    print("synced Row109 VLM_SYNTHETIC Notes (cd787d5b)")
    print("Row074 untouched")


if __name__ == "__main__":
    main()
