#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: sync TRK/ITEM-W64-017 Notes for mf70_eyes_full tournament blocker."""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
NOW = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

E2E_TRACKER = ROOT / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv"
E2E_TRACKER_WAVES = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"
E2E_ITEMS = ROOT / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv"
E2E_ITEMS_WAVES = ROOT / "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"

EVID = "Plan/Instructions/QA/Evidence/Wave64"
STAMP = "20260721T022347-0500"
ROW017_READINESS = f"{EVID}/TRK-W64-017_FUTURE_PRODUCER_EMISSION_PROOF_READINESS_20260720.json"
ROW017_RIGHT_EYE_TIP = f"{EVID}/ROW017_RUNPOD_MF70_RIGHT_EYE_VLM_DEEPEN_20260721T015606-0500.json"
ROW017_INVENTORY = f"{EVID}/ROW017_RUNPOD_PREPARED_LOCALIZED_LANE_INVENTORY_{STAMP}.json"
ROW017_BLOCKER = f"{EVID}/ROW017_RUNPOD_MF70_EYES_FULL_TOURNAMENT_GPU_BLOCKER_{STAMP}.json"
ROW017_STATUS = "Blocked_Canonical_Future_Localized_Producer_Global_Review_Contract_Pending"
ITEM_REL = "Plan/Items/Reports/ITEM-W64-017_global_visual_review_not_local_only.json"
SYNC_MARKER = "synced_by_primary_csv_mutator_row017_mf70_eyes_full_tournament_blocker"
REGION = "mf70_eyes_full"
PRIOR_TIP = "bd7120ab"


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8"))


def dump_json(rel: str, obj: dict) -> None:
    path = ROOT / rel.replace("/", "\\")
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_row017_notes() -> str:
    with E2E_TRACKER.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("Tracker_ID") == "TRK-W64-017":
                return row.get("Notes", "")
    raise RuntimeError("TRK-W64-017 missing from tracker CSV")


def build_notes(land_commit: str) -> str:
    return (
        "Class C cleared (70e12e70); Class E emission-proof readiness (cc68fd5a); RunPod "
        f"mf70_right_eye tip {PRIOR_TIP} GLOBAL_REVIEW+VLM remains latest producer proof; "
        f"preferred next unused prepared {REGION} blocked by active gold-tournament grow-wave "
        f"GPU hold ({STAMP}/{land_commit}); prepared mask present; :8188 contested/down; "
        "did not kill foreign jobs; Status remains "
        f"{ROW017_STATUS}; row_complete=false; NEVER Complete. Blockers: "
        "CLASS_E_FUTURE_PRODUCER_GLOBAL_REVIEW_CONTRACT_PENDING|"
        "PRODUCT_CAMPAIGN_ACCEPTANCE_PENDING|"
        "RUNPOD_GOLD_TOURNAMENT_GPU_HOLD. "
        f"Evidence: {ROW017_READINESS}; {ROW017_RIGHT_EYE_TIP}; {ROW017_INVENTORY}; {ROW017_BLOCKER}"
    )


def build_evidence_path() -> str:
    return (
        f"{ROW017_READINESS}; {ROW017_RIGHT_EYE_TIP}; {ROW017_INVENTORY}; {ROW017_BLOCKER}"
    )


def already_synced(notes: str, land_commit: str) -> bool:
    return (
        f"preferred next unused prepared {REGION} blocked" in notes
        and STAMP in notes
        and land_commit in notes
        and "NEVER Complete" in notes
    )


def rewrite_csv(path: Path, id_col: str, updates: dict[str, dict[str, str]]) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    assert fields
    before = len(rows)
    assert before >= 60, f"refusing rewrite of suspiciously short CSV {path}: {before} rows"
    for row in rows:
        key = row[id_col]
        if key in updates:
            row.update(updates[key])
    for key in updates:
        assert any(r[id_col] == key for r in rows), f"missing {key} in {path}"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            lineterminator="\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)
    with path.open(encoding="utf-8", newline="") as handle:
        after = len(list(csv.DictReader(handle)))
    assert after == before, f"CSV row-count drift in {path}: {before} -> {after}"


def main() -> None:
    tip = git_short()
    notes = read_row017_notes()
    if already_synced(notes, tip):
        print("tip", tip)
        print(f"no-op: TRK/ITEM-W64-017 {REGION} tournament-blocker Notes already synced")
        print("Row074 untouched")
        return

    blocker = load_json(ROW017_BLOCKER)
    inventory = load_json(ROW017_INVENTORY)
    assert blocker.get("row_complete") is False
    assert inventory.get("preferred_next_unused_prepared_lane") == REGION
    assert inventory.get("preferred_lane_status") == "blocked_active_gold_tournament_gpu_hold"

    row017_notes = build_notes(tip)
    row017_evidence = build_evidence_path()
    e2e_tracker_updates = {
        "TRK-W64-017": {
            "Status": ROW017_STATUS,
            "Notes": row017_notes,
            "Evidence_Path": row017_evidence,
        },
    }
    e2e_item_updates = {
        "ITEM-W64-017": {
            "Status": ROW017_STATUS,
            "Notes": row017_notes,
        },
    }
    rewrite_csv(E2E_TRACKER, "Tracker_ID", e2e_tracker_updates)
    rewrite_csv(E2E_TRACKER_WAVES, "Tracker_ID", e2e_tracker_updates)
    rewrite_csv(E2E_ITEMS, "Item_ID", e2e_item_updates)
    rewrite_csv(E2E_ITEMS_WAVES, "Item_ID", e2e_item_updates)

    ledger_vocab = {
        "note": (
            f"Mechanical CSV mutator Row017 {REGION} tournament-blocker tip sync from {tip}; "
            "no COMPLETE; leave Row074 alone."
        ),
        "product_completion": False,
        "synced_at": NOW,
        "prove_commits": [tip],
    }

    for rel in (
        ROW017_BLOCKER,
        f"Plan/Tracker/Evidence/ROW017_RUNPOD_MF70_EYES_FULL_TOURNAMENT_GPU_BLOCKER_{STAMP}.json",
        ROW017_INVENTORY,
        f"Plan/Tracker/Evidence/ROW017_RUNPOD_PREPARED_LOCALIZED_LANE_INVENTORY_{STAMP}.json",
    ):
        packet = load_json(rel)
        packet["csv_sync"] = SYNC_MARKER
        packet["csv_sync_tip"] = tip
        packet["ledger_vocabulary_sync"] = ledger_vocab
        dump_json(rel, packet)

    item_report = load_json(ITEM_REL)
    item_report["csv_sync"] = SYNC_MARKER
    item_report["csv_sync_tip"] = tip
    item_report["row_complete"] = False
    item_report["status"] = ROW017_STATUS
    item_report["latest_region"] = REGION
    item_report["ledger_vocabulary_sync"] = ledger_vocab
    dump_json(ITEM_REL, item_report)

    print("tip", tip)
    print(f"synced TRK/ITEM-W64-017 {REGION} tournament-blocker Notes")
    print("Row074 untouched")


if __name__ == "__main__":
    main()
