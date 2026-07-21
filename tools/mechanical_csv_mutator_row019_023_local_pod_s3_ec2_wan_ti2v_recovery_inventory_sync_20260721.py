#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row019/023 local+pod+S3+EC2 Wan TI2V recovery inventory Notes sync."""
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
RECOVERY_INV = (
    f"{EVID}/TRK-W64-019_023_LOCAL_POD_S3_EC2_WAN_TI2V_RECOVERY_INVENTORY_20260720T234159-0500.json"
)
RECOVERY_INV_TRACKER = (
    "Plan/Tracker/Evidence/Wave64/"
    "TRK-W64-019_023_LOCAL_POD_S3_EC2_WAN_TI2V_RECOVERY_INVENTORY_20260720T234159-0500.json"
)
NEG_INV = (
    f"{EVID}/TRK-W64-019_023_LOCAL_POD_WAN_TI2V_NEGATIVE_INVENTORY_20260720T233253-0500.json"
)
POD_CLASS_B = f"{EVID}/TRK-W64-019_023_POD_CLASS_B_VLM_SUBSTITUTE_20260721T041516Z.json"
POD_CLASS_AF = f"{EVID}/TRK-W64-019_023_POD_CLASS_A_F_BLOCKER_DISPOSITION_PACKET_20260720T225545-0500.json"
CLASS_B_LEDGER = f"{EVID}/TRK-W64-019_023_CLASS_B_BLOCKER_LEDGER_20260720.json"
FLUX_CANARY = (
    "Plan/Instructions/QA/Evidence/Runtime_Readiness/"
    "RUNPOD_1q4ji0gg1fkhvt_FLUX_CANARY_GENERATION_PASS_20260721T034826Z.json"
)

PROVE = "f3f6cc84"
STAMP = "20260720T234159-0500"
SYNC_MARKER = (
    "synced_by_primary_csv_mutator_row019_023_local_pod_s3_ec2_wan_ti2v_recovery_inventory"
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


def read_notes(tracker_id: str) -> str:
    with E2E_TRACKER.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("Tracker_ID") == tracker_id:
                return row.get("Notes", "")
    raise RuntimeError(f"{tracker_id} missing from tracker CSV")


def already_synced(notes: str, prove: list[str]) -> bool:
    return (
        STAMP in notes
        and "0/3 present local+pod+S3" in notes
        and "EC2 live 3/3 ASSET_PRESENT_OK" in notes
        and "Class F retained until bounded copy completes" in notes
        and prove[0] in notes
        and prove[1] in notes
        and "no COMPLETE" in notes
    )


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
    prove = [PROVE, tip]
    if already_synced(read_notes("TRK-W64-019"), prove):
        print("tip", tip)
        print("no-op: TRK/ITEM-W64-019/023 recovery inventory Notes already synced")
        print("Row074 untouched")
        return

    recovery = load_json(RECOVERY_INV)
    assert recovery.get("blocker_class_retained") == "F"
    assert recovery.get("wan_ti2v_present_ratio_local") == "0/3"
    assert recovery.get("wan_ti2v_present_ratio_pod") == "0/3"
    assert recovery.get("wan_ti2v_present_ratio_s3") == "0/3"
    assert recovery.get("ec2_authority", {}).get("live_sha_verify", {}).get("ratio") == "3/3"
    assert recovery.get("row_complete") is False
    assert recovery.get("constraints", {}).get("row074_untouched") is True
    assert recovery.get("constraints", {}).get("no_complete") is True

    row019_notes = (
        f"Class F local+pod+S3 Wan TI2V recovery inventory reaffirm ({PROVE}/{STAMP}): "
        "Wan TI2V 0/3 present local+pod+S3 (3/3 ABSENT); EC2 live 3/3 ASSET_PRESENT_OK "
        "(i-0560bf8d143f93bb1); Class F retained until bounded copy completes; "
        "no copy/scp this pass; proof_tier=LOCAL_POD_S3_INVENTORY_BLOCKER_WITH_EC2_RECOVERY_AUTHORITY; "
        "row_complete=false; no COMPLETE; Row074 PCM left alone. "
        f"Evidence: {RECOVERY_INV}; {NEG_INV}; {POD_CLASS_B}; {POD_CLASS_AF}; {CLASS_B_LEDGER}"
    )
    row023_notes = (
        f"Class F local+pod+S3 Wan TI2V recovery inventory reaffirm ({PROVE}/{STAMP}): "
        "immutable Row023 Wan reject reaffirmed; Wan TI2V 0/3 present local+pod+S3; "
        "EC2 live 3/3 ASSET_PRESENT_OK; Class F retained until bounded copy completes; "
        "no copy/scp this pass; proof_tier=LOCAL_POD_S3_INVENTORY_BLOCKER_WITH_EC2_RECOVERY_AUTHORITY; "
        "row_complete=false; no COMPLETE; Row074 PCM left alone. "
        f"Evidence: {RECOVERY_INV}; {NEG_INV}; {POD_CLASS_B}; {POD_CLASS_AF}; "
        f"{CLASS_B_LEDGER}; {FLUX_CANARY}"
    )
    row019_evidence = f"{RECOVERY_INV}; {NEG_INV}; {POD_CLASS_B}; {POD_CLASS_AF}; {CLASS_B_LEDGER}"
    row023_evidence = (
        f"{RECOVERY_INV}; {NEG_INV}; {POD_CLASS_B}; {POD_CLASS_AF}; "
        f"{CLASS_B_LEDGER}; {FLUX_CANARY}"
    )

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
            f"Mechanical CSV mutator Row019/023 local+pod+S3+EC2 recovery inventory sync "
            f"from {','.join(prove)}; Wan 0/3 local+pod+S3; EC2 live 3/3 ASSET_PRESENT_OK; "
            "Class F until copy completes; no COMPLETE."
        ),
        "product_completion": False,
        "synced_at": NOW,
        "prove_commits": prove,
    }
    for rel in (RECOVERY_INV, RECOVERY_INV_TRACKER):
        packet = load_json(rel)
        packet["csv_sync"] = SYNC_MARKER
        packet["csv_sync_tip"] = tip
        packet["ledger_vocabulary_sync"] = ledger_vocab
        dump_json(rel, packet)

    print("tip", tip)
    print(f"synced Row019/023 local+pod+S3+EC2 recovery inventory Notes ({PROVE}/{STAMP})")
    print("Row074 untouched")


if __name__ == "__main__":
    main()
