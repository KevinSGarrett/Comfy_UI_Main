#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: sync TRK/ITEM-W64-017 Notes for edda4400 face_mask_v1 VLM."""
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
    f"{EVID}/TRK-W64-017_RUNPOD_FUTURE_PRODUCER_EMISSION_PACKET_20260720T230123-0500.json"
)
ROW017_VLM_DEEPEN = f"{EVID}/ROW017_RUNPOD_FACE_MASK_V1_VLM_DEEPEN_20260720T231741-0500.json"
ROW017_VLM_OBS = (
    f"{EVID}/TRK-W64-017_RUNPOD_FACE_MASK_V1_VLM_OBSERVATION_20260720T231741-0500.json"
)
ROW017_GLOBAL_REVIEW = (
    "Plan/Instructions/QA/Evidence/Image_Artifact_QA/Row017_Canonical_Global_Reviews/"
    "ROW017_RUNPOD_W69_INPAINT_FACE_MASK_V1_20260720T230123-0500_GLOBAL_REVIEW.json"
)
ROW017_STATUS = "Blocked_Canonical_Future_Localized_Producer_Global_Review_Contract_Pending"


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
    prove = ["edda4400", tip]
    deepen = load_json(ROW017_VLM_DEEPEN)
    assert deepen.get("vlm_ok") is True
    assert deepen.get("row_complete") is False
    output_sha = deepen["output_sha256"][:12]

    row017_notes = (
        "Class C cleared (70e12e70); Class E emission-proof readiness (cc68fd5a); RunPod "
        "w69_inpaint face_mask_v1 future-producer GLOBAL_REVIEW execute+package "
        "VISUAL_QA_PASS_BOUNDED (20260720T230123-0500) + Ollama qwen2.5vl:7b VLM observation "
        f"vlm_ok ({prove[0]}/20260720T231741-0500); output sha {output_sha}...; "
        f"Status remains {ROW017_STATUS}; row_complete=false; no COMPLETE; "
        "leave Row074 alone. Blockers: "
        "CLASS_E_FUTURE_PRODUCER_GLOBAL_REVIEW_CONTRACT_PENDING|"
        "PRODUCT_CAMPAIGN_ACCEPTANCE_PENDING. "
        f"Evidence: {ROW017_READINESS}; {ROW017_EMISSION}; {ROW017_VLM_DEEPEN}; "
        f"{ROW017_VLM_OBS}; {ROW017_GLOBAL_REVIEW}"
    )
    row017_evidence = (
        f"{ROW017_READINESS}; {ROW017_EMISSION}; {ROW017_VLM_DEEPEN}; "
        f"{ROW017_VLM_OBS}; {ROW017_GLOBAL_REVIEW}"
    )

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
            f"Mechanical CSV mutator Row017 face_mask_v1 VLM sync from {','.join(prove)}; "
            "vlm_ok; future-producer pending; no COMPLETE."
        ),
        "product_completion": False,
        "synced_at": NOW,
        "prove_commits": prove,
    }
    for rel in (
        ROW017_VLM_DEEPEN,
        "Plan/Tracker/Evidence/ROW017_RUNPOD_FACE_MASK_V1_VLM_DEEPEN_20260720T231741-0500.json",
        ROW017_VLM_OBS,
        "Plan/Tracker/Evidence/TRK-W64-017_RUNPOD_FACE_MASK_V1_VLM_OBSERVATION_20260720T231741-0500.json",
        ROW017_EMISSION,
        "Plan/Tracker/Evidence/TRK-W64-017_RUNPOD_FUTURE_PRODUCER_EMISSION_PACKET_20260720T230123-0500.json",
    ):
        packet = load_json(rel)
        packet["csv_sync"] = "synced_by_primary_csv_mutator_row017_face_mask_v1_vlm"
        packet["csv_sync_tip"] = tip
        packet["ledger_vocabulary_sync"] = ledger_vocab
        dump_json(rel, packet)

    item_report = load_json(
        "Plan/Items/Reports/ITEM-W64-017_global_visual_review_not_local_only.json"
    )
    item_report["notes"] = (
        "RunPod face_mask_v1 mid-flight deepen 20260720T230123-0500/20260720T231741-0500: "
        "producer packaged + Ollama qwen2.5vl:7b VLM observation vlm_ok; output sha "
        f"{output_sha}...; Status remains {ROW017_STATUS}; not COMPLETE."
    )
    item_report["csv_sync"] = "synced_by_primary_csv_mutator_row017_face_mask_v1_vlm"
    item_report["csv_sync_tip"] = tip
    dump_json(
        "Plan/Items/Reports/ITEM-W64-017_global_visual_review_not_local_only.json",
        item_report,
    )

    print("tip", tip)
    print("synced TRK/ITEM-W64-017 face_mask_v1 GLOBAL_REVIEW+VLM Notes (edda4400)")
    print("Row074 untouched")


if __name__ == "__main__":
    main()
