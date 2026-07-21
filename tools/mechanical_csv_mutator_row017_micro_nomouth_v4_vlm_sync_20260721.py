#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: sync TRK/ITEM-W64-017 Notes for micro_nomouth_v4 VLM."""
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
ROW017_READINESS = f"{EVID}/TRK-W64-017_FUTURE_PRODUCER_EMISSION_PROOF_READINESS_20260720.json"
ROW017_EMISSION = (
    f"{EVID}/TRK-W64-017_RUNPOD_FUTURE_PRODUCER_EMISSION_PACKET_20260720T232950-0500.json"
)
ROW017_CLIMB = (
    f"{EVID}/ROW017_RUNPOD_FUTURE_PRODUCER_EMISSION_CLIMB_20260720T232950-0500.json"
)
ROW017_VLM_DEEPEN = f"{EVID}/ROW017_RUNPOD_MICRO_NOMOUTH_V4_VLM_DEEPEN_20260720T232956-0500.json"
ROW017_VLM_OBS = (
    f"{EVID}/TRK-W64-017_RUNPOD_MICRO_NOMOUTH_V4_VLM_OBSERVATION_20260720T232956-0500.json"
)
ROW017_GLOBAL_REVIEW = (
    "Plan/Instructions/QA/Evidence/Image_Artifact_QA/Row017_Canonical_Global_Reviews/"
    "ROW017_RUNPOD_W69_INPAINT_MICRO_NOMOUTH_V4_20260720T232950-0500_GLOBAL_REVIEW.json"
)
ROW017_VISUAL_QA = (
    "Plan/Instructions/QA/Evidence/Image_Artifact_QA/"
    "ROW017_RUNPOD_W69_INPAINT_MICRO_NOMOUTH_V4_VISUAL_QA_20260720T232950-0500.json"
)
ROW017_STATUS = "Blocked_Canonical_Future_Localized_Producer_Global_Review_Contract_Pending"
ITEM_REL = "Plan/Items/Reports/ITEM-W64-017_global_visual_review_not_local_only.json"
SYNC_MARKER = "synced_by_primary_csv_mutator_row017_micro_nomouth_v4_vlm"


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


def build_notes(prove: list[str], output_sha: str, mouth_freeze: float) -> str:
    return (
        "Class C cleared (70e12e70); Class E emission-proof readiness (cc68fd5a); RunPod "
        "w69_inpaint micro_nomouth_v4 future-producer GLOBAL_REVIEW pass "
        "VISUAL_QA_PASS_BOUNDED (20260720T232950-0500) + Ollama qwen2.5vl:7b VLM observation "
        f"vlm_ok ({prove[0]}/{prove[1]}/20260720T232956-0500); mouth freeze ~0.001 "
        f"(mouth_region_mean_abs {mouth_freeze:.6f}); output sha {output_sha}...; "
        f"Status remains {ROW017_STATUS}; row_complete=false; NEVER Complete; "
        "leave Row074 alone. Blockers: "
        "CLASS_E_FUTURE_PRODUCER_GLOBAL_REVIEW_CONTRACT_PENDING|"
        "PRODUCT_CAMPAIGN_ACCEPTANCE_PENDING. "
        f"Evidence: {ROW017_READINESS}; {ROW017_EMISSION}; {ROW017_CLIMB}; "
        f"{ROW017_VLM_DEEPEN}; {ROW017_VLM_OBS}; {ROW017_GLOBAL_REVIEW}; {ROW017_VISUAL_QA}"
    )


def build_evidence_path() -> str:
    return (
        f"{ROW017_READINESS}; {ROW017_EMISSION}; {ROW017_CLIMB}; "
        f"{ROW017_VLM_DEEPEN}; {ROW017_VLM_OBS}; {ROW017_GLOBAL_REVIEW}; {ROW017_VISUAL_QA}"
    )


def already_synced(notes: str, prove: list[str]) -> bool:
    return (
        "micro_nomouth_v4 future-producer GLOBAL_REVIEW pass" in notes
        and "vlm_ok" in notes
        and "mouth freeze ~0.001" in notes
        and "20260720T232950-0500" in notes
        and "20260720T232956-0500" in notes
        and prove[0] in notes
        and prove[1] in notes
        and "NEVER Complete" in notes
    )


def main() -> None:
    tip = git_short()
    prove = ["2c109f3f", "43595464", tip]

    deepen = load_json(ROW017_VLM_DEEPEN)
    visual_qa = load_json(ROW017_VISUAL_QA)
    assert deepen.get("vlm_ok") is True
    assert deepen.get("row_complete") is False
    assert deepen.get("producer_stamp") == "20260720T232950-0500"
    output_sha = deepen["output_sha256"][:12]
    mouth_freeze = float(visual_qa["difference_metrics"]["mouth_region_mean_abs"])

    row017_notes = build_notes(prove, output_sha, mouth_freeze)
    row017_evidence = build_evidence_path()

    with E2E_TRACKER.open(encoding="utf-8", newline="") as handle:
        current = next(r for r in csv.DictReader(handle) if r["Tracker_ID"] == "TRK-W64-017")
    if already_synced(current["Notes"], prove):
        print("tip", tip)
        print("no-op: TRK/ITEM-W64-017 micro_nomouth_v4 Notes already synced")
        print("Row074 untouched")
        return

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
            f"Mechanical CSV mutator Row017 micro_nomouth_v4 VLM sync from {','.join(prove)}; "
            "GLOBAL_REVIEW pass; vlm_ok; mouth freeze ~0.001; future-producer pending; no COMPLETE."
        ),
        "product_completion": False,
        "synced_at": NOW,
        "prove_commits": prove,
    }

    def stamp(rel: str) -> None:
        packet = load_json(rel)
        packet["csv_sync"] = SYNC_MARKER
        packet["csv_sync_tip"] = tip
        packet["ledger_vocabulary_sync"] = ledger_vocab
        dump_json(rel, packet)

    for rel in (
        ROW017_VLM_DEEPEN,
        "Plan/Tracker/Evidence/ROW017_RUNPOD_MICRO_NOMOUTH_V4_VLM_DEEPEN_20260720T232956-0500.json",
        ROW017_VLM_OBS,
        "Plan/Tracker/Evidence/TRK-W64-017_RUNPOD_MICRO_NOMOUTH_V4_VLM_OBSERVATION_20260720T232956-0500.json",
        ROW017_EMISSION,
        "Plan/Tracker/Evidence/TRK-W64-017_RUNPOD_FUTURE_PRODUCER_EMISSION_PACKET_20260720T232950-0500.json",
        ROW017_CLIMB,
        "Plan/Tracker/Evidence/ROW017_RUNPOD_FUTURE_PRODUCER_EMISSION_CLIMB_20260720T232950-0500.json",
    ):
        stamp(rel)

    deepen = load_json(ROW017_VLM_DEEPEN)
    deepen["boundaries"]["csv_mutated"] = True
    deepen["csv_sync"] = SYNC_MARKER
    deepen["csv_sync_tip"] = tip
    deepen["ledger_vocabulary_sync"] = ledger_vocab
    dump_json(ROW017_VLM_DEEPEN, deepen)
    dump_json(
        "Plan/Tracker/Evidence/ROW017_RUNPOD_MICRO_NOMOUTH_V4_VLM_DEEPEN_20260720T232956-0500.json",
        deepen,
    )

    item_report = load_json(ITEM_REL)
    item_report["notes"] = (
        "RunPod micro_nomouth_v4 producer+VLM climb 20260720T232950-0500/20260720T232956-0500: "
        "GLOBAL_REVIEW pass + Ollama qwen2.5vl:7b VLM observation vlm_ok; mouth freeze ~0.001; "
        f"output sha {output_sha}...; Status remains {ROW017_STATUS}; row_complete=false; "
        "NEVER Complete."
    )
    item_report["csv_sync"] = SYNC_MARKER
    item_report["csv_sync_tip"] = tip
    dump_json(ITEM_REL, item_report)

    print("tip", tip)
    print("synced TRK/ITEM-W64-017 micro_nomouth_v4 GLOBAL_REVIEW+VLM Notes (2c109f3f/43595464)")
    print("Row074 untouched")


if __name__ == "__main__":
    main()
