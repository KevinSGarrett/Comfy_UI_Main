#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 POD Class B VLM Notes sync only (20260721)."""
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
POD_CLASS_B = f"{EVID}/TRK-W64-019_023_POD_CLASS_B_VLM_SUBSTITUTE_20260721T041516Z.json"
POD_CLASS_B_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_POD_CLASS_B_VLM_SUBSTITUTE_20260721T041516Z.json"
)
POD_CLASS_AF = f"{EVID}/TRK-W64-019_023_POD_CLASS_A_F_BLOCKER_DISPOSITION_PACKET_20260720T225545-0500.json"
CLASS_B_LEDGER = f"{EVID}/TRK-W64-019_023_CLASS_B_BLOCKER_LEDGER_20260720.json"
CLASS_B_LEDGER_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/TRK-W64-019_023_CLASS_B_BLOCKER_LEDGER_20260720.json"
)
FLUX_CANARY = (
    "Plan/Instructions/QA/Evidence/Runtime_Readiness/"
    "RUNPOD_1q4ji0gg1fkhvt_FLUX_CANARY_GENERATION_PASS_20260721T034826Z.json"
)


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


def sibling_row075_109_already_synced() -> bool:
    delta075 = load_json(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-075_AUDIO_QUALITY_DEFECT_CURRENT_DELTA_20260719.json"
    )
    delta109 = load_json(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-109_AUDIO_BENCHMARK_CORPUS_CURRENT_DELTA_20260720.json"
    )
    return (
        delta075.get("csv_sync") == "synced_by_primary_csv_mutator_row075_109_vlm"
        and delta109.get("csv_sync") == "synced_by_primary_csv_mutator_row075_109_vlm"
    )


def main() -> None:
    tip = git_short()
    prove = ["cd787d5b", tip]
    assert sibling_row075_109_already_synced(), "Row075/109 sibling VLM sync required first"

    row019_notes = (
        "Class B POD autonomous VLM substitute (cd787d5b/041516Z): Scenes Flux contact/soft-body "
        "frames + Ollama qwen2.5vl:7b 4/4 reviewed 4/4 REJECT_RETAINED; Wan TI2V 0/3 absent; "
        "gold authority 7/7 ABSENT on pod; no Flux seed spam; no Wan download; "
        "proof_tier=POD_CLASS_B_VLM_SUBSTITUTE_BOUNDED; row_complete=false; no COMPLETE; "
        f"Row074 PCM left alone. Evidence: {POD_CLASS_B}; {POD_CLASS_AF}; {CLASS_B_LEDGER}"
    )
    row023_notes = (
        "Class B POD autonomous VLM substitute (cd787d5b/041516Z): immutable Row023 Wan reject "
        "reaffirmed + Scenes synthetic contact/soft-body VLM 4/4 REJECT_RETAINED; Wan TI2V 0/3 "
        "absent; gold-mask authority absent on pod; synthetic+VLM bounded only (not gold "
        "promotion); proof_tier=POD_CLASS_B_VLM_SUBSTITUTE_BOUNDED; row_complete=false; "
        f"no COMPLETE; Row074 PCM left alone. Evidence: {POD_CLASS_B}; {POD_CLASS_AF}; "
        f"{CLASS_B_LEDGER}; {FLUX_CANARY}"
    )
    row019_evidence = f"{POD_CLASS_B}; {POD_CLASS_AF}; {CLASS_B_LEDGER}"
    row023_evidence = f"{POD_CLASS_B}; {POD_CLASS_AF}; {CLASS_B_LEDGER}; {FLUX_CANARY}"

    e2e_tracker_updates = {
        "TRK-W64-019": {
            "Notes": row019_notes,
            "Evidence_Path": row019_evidence,
        },
        "TRK-W64-023": {
            "Notes": row023_notes,
            "Evidence_Path": row023_evidence,
        },
    }
    e2e_item_updates = {
        "ITEM-W64-019": {"Notes": row019_notes},
        "ITEM-W64-023": {"Notes": row023_notes},
    }

    rewrite_csv(E2E_TRACKER, "Tracker_ID", e2e_tracker_updates)
    rewrite_csv(E2E_TRACKER_WAVES, "Tracker_ID", e2e_tracker_updates)
    rewrite_csv(E2E_ITEMS, "Item_ID", e2e_item_updates)
    rewrite_csv(E2E_ITEMS_WAVES, "Item_ID", e2e_item_updates)

    ledger_vocab = {
        "note": (
            f"Mechanical CSV mutator Row019/023 Class B VLM sync from {','.join(prove)}; "
            "4/4 REJECT_RETAINED; Wan 0/3; gold absent; no COMPLETE."
        ),
        "product_completion": False,
        "synced_at": NOW,
        "prove_commits": prove,
    }
    for rel in (POD_CLASS_B, POD_CLASS_B_TRACKER):
        packet = load_json(rel)
        packet["csv_sync"] = "synced_by_primary_csv_mutator_row019_023_pod_class_b_vlm"
        packet["csv_sync_tip"] = tip
        packet["ledger_vocabulary_sync"] = ledger_vocab
        dump_json(rel, packet)

    for rel in (CLASS_B_LEDGER, CLASS_B_LEDGER_TRACKER):
        ledger = load_json(rel)
        ledger["csv_sync"] = "synced_by_primary_csv_mutator_row019_023_pod_class_b_vlm"
        ledger["csv_sync_tip"] = tip
        dump_json(rel, ledger)

    print("tip", tip)
    print("synced Row019/023 POD Class B VLM Notes (cd787d5b/041516Z)")
    print("Row074 untouched; Row075/109 left to sibling sync")


if __name__ == "__main__":
    main()
