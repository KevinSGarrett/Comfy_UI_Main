#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: sync TRK/ITEM-W64-017 Notes for micro_nomouth_v4 232259 climb+VLM."""
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
ROW017_FACE_MASK_EMISSION = (
    f"{EVID}/TRK-W64-017_RUNPOD_FUTURE_PRODUCER_EMISSION_PACKET_20260720T230123-0500.json"
)
ROW017_FACE_MASK_VLM_DEEPEN = f"{EVID}/ROW017_RUNPOD_FACE_MASK_V1_VLM_DEEPEN_20260720T231741-0500.json"
ROW017_FACE_MASK_VLM_OBS = (
    f"{EVID}/TRK-W64-017_RUNPOD_FACE_MASK_V1_VLM_OBSERVATION_20260720T231741-0500.json"
)
ROW017_FACE_MASK_GLOBAL_REVIEW = (
    "Plan/Instructions/QA/Evidence/Image_Artifact_QA/Row017_Canonical_Global_Reviews/"
    "ROW017_RUNPOD_W69_INPAINT_FACE_MASK_V1_20260720T230123-0500_GLOBAL_REVIEW.json"
)
ROW017_MICRO_EMISSION = (
    f"{EVID}/TRK-W64-017_RUNPOD_FUTURE_PRODUCER_EMISSION_PACKET_20260720T232259-0500.json"
)
ROW017_MICRO_CLIMB = (
    f"{EVID}/TRK-W64-017_RUNPOD_FUTURE_PRODUCER_EMISSION_CLIMB_20260720T232259-0500.json"
)
ROW017_MICRO_VLM_DEEPEN = f"{EVID}/ROW017_RUNPOD_MICRO_NOMOUTH_V4_VLM_DEEPEN_20260720T232543-0500.json"
ROW017_MICRO_VLM_OBS = (
    f"{EVID}/TRK-W64-017_RUNPOD_MICRO_NOMOUTH_V4_VLM_OBSERVATION_20260720T232543-0500.json"
)
ROW017_MICRO_GLOBAL_REVIEW = (
    "Plan/Instructions/QA/Evidence/Image_Artifact_QA/Row017_Canonical_Global_Reviews/"
    "ROW017_RUNPOD_W69_INPAINT_MICRO_NOMOUTH_V4_20260720T232259-0500_GLOBAL_REVIEW.json"
)
ROW017_STATUS = "Blocked_Canonical_Future_Localized_Producer_Global_Review_Contract_Pending"
FACE_MASK_TIP = "b15959f5"
MICRO_NOMOUTH_PROVE = "2c109f3f"
MICRO_NOMOUTH_STAMP = "20260720T232259-0500"
MICRO_VLM_STAMP = "20260720T232543-0500"
ITEM_REL = "Plan/Items/Reports/ITEM-W64-017_global_visual_review_not_local_only.json"
SYNC_MARKER = "synced_by_primary_csv_mutator_row017_micro_nomouth_v4_232259_vlm"


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


def already_cited(notes: str) -> bool:
    return MICRO_NOMOUTH_STAMP in notes and "micro_nomouth_v4" in notes and MICRO_NOMOUTH_PROVE in notes


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
    notes = read_row017_notes()
    if already_cited(notes):
        print("no-op: TRK/ITEM-W64-017 Notes already cite micro_nomouth_v4 climb")
        print(f"stamp {MICRO_NOMOUTH_STAMP}; Row074 untouched")
        return

    tip = git_short()
    prove = [FACE_MASK_TIP, MICRO_NOMOUTH_PROVE, tip]

    face_deepen = load_json(ROW017_FACE_MASK_VLM_DEEPEN)
    assert face_deepen.get("vlm_ok") is True
    assert face_deepen.get("row_complete") is False
    face_output_sha = face_deepen["output_sha256"][:12]

    micro_deepen = load_json(ROW017_MICRO_VLM_DEEPEN)
    assert micro_deepen.get("row_complete") is False
    assert micro_deepen["vlm"]["ok"] is True
    micro_output_sha = micro_deepen["artifact"]["sha256"][:12]

    row017_notes = (
        "Class C cleared (70e12e70); Class E emission-proof readiness (cc68fd5a); RunPod "
        "w69_inpaint face_mask_v1 future-producer GLOBAL_REVIEW execute+package "
        "VISUAL_QA_PASS_BOUNDED (20260720T230123-0500) + Ollama qwen2.5vl:7b VLM observation "
        f"vlm_ok ({FACE_MASK_TIP}/20260720T231741-0500); output sha {face_output_sha}...; "
        "RunPod w69_inpaint micro_nomouth_v4 future-producer GLOBAL_REVIEW execute+package "
        f"VISUAL_QA_PASS_BOUNDED ({MICRO_NOMOUTH_STAMP}) + Ollama qwen2.5vl:7b VLM observation "
        f"vlm_ok ({MICRO_NOMOUTH_PROVE}/{MICRO_VLM_STAMP}); output sha {micro_output_sha}...; "
        f"Status remains {ROW017_STATUS}; row_complete=false; no COMPLETE; "
        "leave Row074 alone. Blockers: "
        "CLASS_E_FUTURE_PRODUCER_GLOBAL_REVIEW_CONTRACT_PENDING|"
        "PRODUCT_CAMPAIGN_ACCEPTANCE_PENDING. "
        f"Evidence: {ROW017_READINESS}; {ROW017_FACE_MASK_EMISSION}; {ROW017_FACE_MASK_VLM_DEEPEN}; "
        f"{ROW017_FACE_MASK_VLM_OBS}; {ROW017_FACE_MASK_GLOBAL_REVIEW}; {ROW017_MICRO_EMISSION}; "
        f"{ROW017_MICRO_CLIMB}; {ROW017_MICRO_VLM_DEEPEN}; {ROW017_MICRO_VLM_OBS}; "
        f"{ROW017_MICRO_GLOBAL_REVIEW}"
    )
    row017_evidence = (
        f"{ROW017_READINESS}; {ROW017_FACE_MASK_EMISSION}; {ROW017_FACE_MASK_VLM_DEEPEN}; "
        f"{ROW017_FACE_MASK_VLM_OBS}; {ROW017_FACE_MASK_GLOBAL_REVIEW}; {ROW017_MICRO_EMISSION}; "
        f"{ROW017_MICRO_CLIMB}; {ROW017_MICRO_VLM_DEEPEN}; {ROW017_MICRO_VLM_OBS}; "
        f"{ROW017_MICRO_GLOBAL_REVIEW}"
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
            f"Mechanical CSV mutator Row017 micro_nomouth_v4 232259 climb+VLM sync from "
            f"{','.join(prove)}; GLOBAL_REVIEW+VLM ok; future-producer pending; no COMPLETE."
        ),
        "product_completion": False,
        "synced_at": NOW,
        "prove_commits": prove,
    }
    for rel in (
        ROW017_MICRO_VLM_DEEPEN,
        "Plan/Tracker/Evidence/ROW017_RUNPOD_MICRO_NOMOUTH_V4_VLM_DEEPEN_20260720T232543-0500.json",
        ROW017_MICRO_VLM_OBS,
        "Plan/Tracker/Evidence/TRK-W64-017_RUNPOD_MICRO_NOMOUTH_V4_VLM_OBSERVATION_20260720T232543-0500.json",
        ROW017_MICRO_EMISSION,
        "Plan/Tracker/Evidence/TRK-W64-017_RUNPOD_FUTURE_PRODUCER_EMISSION_PACKET_20260720T232259-0500.json",
        ROW017_MICRO_CLIMB,
        "Plan/Tracker/Evidence/ROW017_RUNPOD_FUTURE_PRODUCER_EMISSION_CLIMB_20260720T232259-0500.json",
    ):
        packet = load_json(rel)
        packet["csv_sync"] = SYNC_MARKER
        packet["csv_sync_tip"] = tip
        packet["ledger_vocabulary_sync"] = ledger_vocab
        if packet.get("csv_update_deferred"):
            packet["csv_update_deferred"] = False
        dump_json(rel, packet)

    item_report = load_json(ITEM_REL)
    item_report["notes"] = (
        "RunPod face_mask_v1 mid-flight deepen 20260720T230123-0500/20260720T231741-0500: "
        "producer packaged + Ollama qwen2.5vl:7b VLM observation vlm_ok; output sha "
        f"{face_output_sha}...; RunPod micro_nomouth_v4 climb {MICRO_NOMOUTH_STAMP}/"
        f"{MICRO_VLM_STAMP}: GLOBAL_REVIEW+VLM ok ({MICRO_NOMOUTH_PROVE}); output sha "
        f"{micro_output_sha}...; Status remains {ROW017_STATUS}; row_complete=false; not COMPLETE."
    )
    item_report["csv_sync"] = SYNC_MARKER
    item_report["csv_sync_tip"] = tip
    dump_json(ITEM_REL, item_report)

    print("tip", tip)
    print(
        f"synced TRK/ITEM-W64-017 face_mask_v1 ({FACE_MASK_TIP}) + "
        f"micro_nomouth_v4 climb ({MICRO_NOMOUTH_PROVE}/{MICRO_NOMOUTH_STAMP})"
    )
    print("Row074 untouched")


if __name__ == "__main__":
    main()
