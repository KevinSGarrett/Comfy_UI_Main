#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row124 Path C ASR/DNSMOS sync (eccc54f0/2c109f3f). Row074 untouched."""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
NOW = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

SPEECH_TRACKER = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv"
SPEECH_ITEMS = ROOT / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv"

EVID_WAVE = "Plan/Instructions/QA/Evidence/Wave64"
EVID_AUDIO = "Plan/Instructions/QA/Evidence/Audio_Asset_Intake"
ROW124_DELTA = f"{EVID_WAVE}/TRK-W64-124_MULTI_REF_LISTENING_CURRENT_DELTA_20260720G.json"
ROW124_ASR = f"{EVID_AUDIO}/TRK-W64-124_AUTONOMOUS_ASR_LLM_LISTENING_REVIEW_20260720G.json"
ROW124_ROW = f"{EVID_AUDIO}/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW124.json"
PROVE = ["eccc54f0", "2c109f3f"]


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
    prove = PROVE + [tip]

    delta = load_json(ROW124_DELTA)
    asr = load_json(ROW124_ASR)
    row124 = load_json(ROW124_ROW)

    assert delta.get("decision", {}).get("row_complete") is False
    assert delta.get("decision", {}).get("product_completion") is False
    assert asr.get("status") == "AUTONOMOUS_ASR_LLM_LISTENING_REVIEW_FAIL"
    assert asr.get("blocker_code") == "AUTONOMOUS_ASR_LLM_LISTENING_REVIEW_FAIL"
    assert "INDEPENDENT_PLAYBACK_REVIEW_ABSENT" in delta.get("blocker_classes", [{}])[2].get(
        "cleared_by_this_packet", []
    )
    assert delta.get("boundaries", {}).get("row074_touched") is False

    failing = asr.get("failing_categories") or [
        "pacing_timing",
        "naturalness",
        "technical_cleanliness",
    ]
    fail_label = "|".join(failing)

    row124_status = "Blocked_Production_Voice_Authority_And_Multi_Reference_Validation_Pending"
    row124_decision = (
        "blocked_production_voice_authority_path_c_asr_fail_timing_waiver_not_granted_20260720g"
    )
    row124_notes = (
        "OFFLINE_PROOF_BOUNDED (eccc54f0/20260720G): multi-ref drift/leakage matrix complete; "
        "Path C autonomous ASR/DNSMOS/LLM listening review executed and FAIL "
        f"({fail_label} below minimum); INDEPENDENT_PLAYBACK_REVIEW_ABSENT cleared (review ran); "
        "AUTONOMOUS_ASR_LLM_LISTENING_REVIEW_FAIL retained; production blocker "
        "PRODUCTION_CHARACTER_REFERENCE_AUTHORITY_ABSENT retained; Path A bounded stretch "
        "live-measured OUT OF BOUNDS; fail-closed timing waiver NOT granted "
        "(RAW_DIALOGUE_TIMING_OUT_OF_TOLERANCE); human-listening fail-closed retained; "
        "listening_authority_granted=false; row_complete=false; no COMPLETE; Row074 left alone. "
        f"Evidence: {ROW124_DELTA}; {ROW124_ASR}; {ROW124_ROW}"
    )
    row124_evidence = f"{ROW124_ROW}; {ROW124_DELTA}; {ROW124_ASR}"

    speech_tracker_updates = {
        "TRK-W64-124": {
            "Status": row124_status,
            "Status_Decision": row124_decision,
            "Notes": row124_notes,
            "Evidence_Path": row124_evidence,
        },
    }
    speech_item_updates = {
        "ITEM-W64-124": {
            "Status": row124_status,
            "Notes": row124_notes,
        },
    }

    rewrite_csv(SPEECH_TRACKER, "Tracker_ID", speech_tracker_updates)
    rewrite_csv(SPEECH_ITEMS, "Item_ID", speech_item_updates)

    delta["updated_at"] = NOW
    delta["csv_sync"] = "synced_by_primary_csv_mutator_row124_path_c_asr_sync"
    delta["csv_sync_tip"] = tip
    delta["ledger_vocabulary_sync"] = {
        "ledger_status": row124_status,
        "note": (
            f"Mechanical CSV mutator Row124 Path C ASR sync from {','.join(prove)}; "
            "INDEPENDENT_PLAYBACK_REVIEW_ABSENT cleared; no COMPLETE."
        ),
        "product_completion": False,
        "runtime_completion": False,
        "synced_at": NOW,
        "prove_commits": prove,
        "row074_left_alone": True,
    }
    dump_json(ROW124_DELTA, delta)

    asr["csv_sync"] = "synced_by_primary_csv_mutator_row124_path_c_asr_sync"
    asr["csv_sync_tip"] = tip
    dump_json(ROW124_ASR, asr)

    row124["csv_sync"] = "synced_by_primary_csv_mutator_row124_path_c_asr_sync"
    row124["csv_sync_tip"] = tip
    dump_json(ROW124_ROW, row124)

    print("tip", tip)
    print("synced TRK/ITEM-W64-124 Path C ASR/DNSMOS FAIL", prove)
    print("INDEPENDENT_PLAYBACK_REVIEW_ABSENT cleared; production/timing blockers retained")
    print("row_complete=false; Row074 left alone")


if __name__ == "__main__":
    main()
