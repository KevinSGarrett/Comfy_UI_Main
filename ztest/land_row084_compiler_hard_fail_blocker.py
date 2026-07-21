#!/usr/bin/env python3
"""Land Row084 COMPILER_HARD_FAIL not-clearable blocker packet (evidence + CSV)."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
EVID = ROOT / "Plan/Instructions/QA/Evidence/Wave64"
PACKET = EVID / "TRK-W64-084_ROW084-011_COMPILER_HARD_FAIL_NOT_CLEARABLE_BLOCKER_PACKET_20260721.json"
DELTA = EVID / "TRK-W64-084_CANONICAL_VIDEO_TIMELINE_CURRENT_DELTA_20260719.json"
ARTIFACT = EVID / "TRK-W64-084_canonical_video_timeline.json"
HOLD_012 = EVID / "TRK-W64-084_ROW084-012_CLASS_C_SCHEMA_NATIVE_REVERSED_PTS_HOLD_PACKET_20260720.json"
PROD_PACKET = EVID / "TRK-W64-084_ROW084-011_CLASS_E_RUNPOD_PROD_MEDIA_CUT_CAMERA_MUX_PROBE_20260721.json"
SOUND_TRACKER = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_TRACKER_ROWS.csv"
SOUND_ITEMS = ROOT / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_SOUND_INTELLIGENCE_ITEM_ROWS.csv"

BLOCKER = "COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED"
HOLD_012_SHA = "0e0c3d8648f939f24684be7a9b7ad70aef20b1289f6fadd30d90256dbdeb1ff7"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_short() -> str:
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj: dict) -> None:
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
    assert "TRK-W64-074" not in updates
    assert "ITEM-W64-074" not in updates
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    tip = git_short()
    assert PACKET.is_file()
    assert HOLD_012.is_file()
    assert sha256(HOLD_012) == HOLD_012_SHA

    packet = load(PACKET)
    assert packet["clearable_on_current_evidence"] is False
    assert packet["cleared"] is False
    assert packet["row_complete"] is False
    assert packet["production_completion_allowed"] is False
    assert packet["hold_012_unchanged"]["status"] == "OPEN_HOLD"
    assert packet["hold_012_unchanged"]["thrashed"] is False
    packet_sha = sha256(PACKET)
    packet["tip_at_probe"] = tip
    packet["updated_at"] = NOW
    dump(PACKET, packet)
    packet_sha = sha256(PACKET)

    delta = load(DELTA)
    codes = delta.setdefault("blocker_codes", [])
    if BLOCKER not in codes:
        codes.append(BLOCKER)

    bc = delta.setdefault("blocker_classification", {})
    class_e = bc.setdefault("PRODUCTION_COMPLETION_AND_ROW_COMPLETE_BLOCKED", {})
    class_e["status"] = "OPEN"
    class_e["compiler_hard_fail_blocker_packet"] = PACKET.relative_to(ROOT).as_posix()
    class_e["compiler_hard_fail_blocker_packet_sha256"] = packet_sha
    class_e["compiler_hard_fail_clearable"] = False
    class_e["detail"] = (
        "COMPLETE/row_complete intentionally withheld. COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED "
        "remains correctly OPEN: compile_wave64_canonical_video_timeline.py:844-847 unconditionally forces "
        "production_completion_allowed=false. Not clearable on current evidence — production mux replay / "
        "cut-camera / visual beyond held-out lavfi still absent; removing hard-fail alone would enable claim cheat. "
        f"Blocker packet {packet_sha[:12]}. ROW084-012 OPEN_HOLD untouched."
    )

    for check in delta.get("checks", []):
        if check.get("check_id") == "ROW084-011":
            check["status"] = "FAIL"
            check["compiler_hard_fail_blocker_packet"] = PACKET.relative_to(ROOT).as_posix()
            check["compiler_hard_fail_blocker_packet_sha256"] = packet_sha
            check["compiler_hard_fail_clearable"] = False
            check["note"] = (
                "Class E FAIL/OPEN retained. Gate #1 COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED "
                "not clearable by bounded fix: enforced at compile_wave64_canonical_video_timeline.py:844-847; "
                "production mux/cut/camera/visual authority still absent after prod-media probe. "
                "Do not remove hard-fail; do not COMPLETE. ROW084-012 OPEN_HOLD unchanged."
            )
            break

    fltr = delta.setdefault("focused_local_test_result", {})
    fltr["compiler_hard_fail_clearability"] = {
        "blocker_id": BLOCKER,
        "blocker_class": "E",
        "cleared": False,
        "clearable_on_current_evidence": False,
        "enforcement": "Plan/07_IMPLEMENTATION/scripts/compile_wave64_canonical_video_timeline.py:844-847",
        "packet": PACKET.relative_to(ROOT).as_posix(),
        "packet_sha256": packet_sha,
        "production_completion_allowed": False,
        "row_complete": False,
        "status": "HOLD",
        "verdict": "NOT_CLEARABLE_BY_BOUNDED_FIX_ON_CURRENT_EVIDENCE",
    }

    sd = delta.setdefault("status_decision", {})
    sd["decision"] = "HOLD_ROW084_COMPILER_HARD_FAIL_NOT_CLEARABLE_NO_COMPLETE"
    sd["reason"] = (
        "Compiler hard-fail gate remains correctly FAIL/OPEN; not clearable without production "
        "mux/cut/camera/visual authority. ROW084-012 OPEN_HOLD not thrashed; COMPLETE withheld."
    )
    sd["safe_next_action"] = packet["safe_next_action"]

    impl = delta.setdefault("implementation", {})
    still = impl.setdefault("still_absent", [])
    for item in [
        "production mux replay proof",
        "production cut/camera/benchmark authority beyond held-out lavfi",
        "compiler production_completion_allowed hard fail-close removal",
        "production-candidate media camera class calibration (unclassified under held-out thresholds)",
        "production media combined visual/contact beyond held-out lavfi",
    ]:
        if item not in still:
            still.append(item)
    impl["compiler_hard_fail_blocker_packet_path"] = PACKET.relative_to(ROOT).as_posix()
    impl["compiler_hard_fail_blocker_packet_sha256"] = packet_sha
    impl["compiler_hard_fail_clearable_on_current_evidence"] = False

    slice_ = delta.setdefault("implementation_slice", {})
    still2 = slice_.setdefault("still_absent", [])
    for item in [
        "production mux replay proof",
        "production cut/camera/benchmark authority beyond held-out lavfi",
        "JSON Schema native end_pts > start_pts comparison",
        "row_complete / acceptance COMPLETE",
        "production media combined visual/contact beyond held-out lavfi",
        "compiler production_completion_allowed hard fail-close removal",
    ]:
        if item not in still2:
            still2.append(item)

    inc = delta.setdefault("increment", {})
    inc["kind"] = "compiler_hard_fail_not_clearable_blocker_packet"
    inc["row_complete"] = False
    inc["comfyui_8188_invoked"] = False
    inc["summary"] = packet["summary"]

    delta["updated_at"] = NOW
    delta["row_complete"] = False
    delta["product_completion_claimed"] = False
    delta["qa_decision"] = "HOLD"
    delta["status"] = "HOLD_ROW084_COMPILER_HARD_FAIL_NOT_CLEARABLE_NO_COMPLETE"
    dump(DELTA, delta)

    art = load(ARTIFACT)
    holds = art.setdefault("hold_reasons", [])
    for reason in [
        "compiler_hard_fail_closes_production_completion_allowed",
        "compiler_hard_fail_not_clearable_on_current_evidence",
    ]:
        if reason not in holds:
            holds.append(reason)
    art["compiler_hard_fail_blocker_packet"] = PACKET.relative_to(ROOT).as_posix()
    art["compiler_hard_fail_blocker_packet_sha256"] = packet_sha
    art["compiler_hard_fail_clearable_on_current_evidence"] = False
    art["production_completion_allowed"] = False
    art["row_complete"] = False
    art["implementation_completion_claimed"] = False
    art["class_e_011_status"] = "FAIL"
    art["status"] = "HOLD_COMPILER_HARD_FAIL_NOT_CLEARABLE_CLASS_E_NO_COMPLETE"
    art["updated_at"] = NOW
    dump(ARTIFACT, art)

    if PROD_PACKET.is_file():
        prod = load(PROD_PACKET)
        rem = prod.setdefault("remaining_blockers", [])
        if BLOCKER not in rem:
            rem.insert(0, BLOCKER)
        prod["compiler_hard_fail_blocker_packet"] = PACKET.relative_to(ROOT).as_posix()
        prod["compiler_hard_fail_blocker_packet_sha256"] = packet_sha
        prod["compiler_hard_fail_clearable_on_current_evidence"] = False
        dump(PROD_PACKET, prod)

    rel_packet = PACKET.relative_to(ROOT).as_posix()
    rel_delta = DELTA.relative_to(ROOT).as_posix()
    rel_art = ARTIFACT.relative_to(ROOT).as_posix()
    rel_hold = HOLD_012.relative_to(ROOT).as_posix()
    status = (
        "Blocked_Visual_Qa_Pass_Bounded_Class_C_Schema_Native_Hold_And_Production_Completion_Blocked"
    )
    decision = "row084_compiler_hard_fail_not_clearable_no_complete"
    notes = (
        f"COMPILER_HARD_FAIL_CLOSES_PRODUCTION_COMPLETION_ALLOWED adjudicated NOT CLEARABLE on current "
        f"evidence (tip {tip}). Enforced at compile_wave64_canonical_video_timeline.py:844-847 "
        "(unconditional force production_completion_allowed=false). Production mux replay / cut-camera / "
        "visual beyond held-out lavfi still absent after Class E prod-media probe 753e72f6; removing "
        "hard-fail alone would enable claim cheat — withheld. ROW084-011 FAIL/OPEN; ROW084-012 OPEN_HOLD "
        f"unchanged ({HOLD_012_SHA[:8]}); row_complete=false; NEVER Complete; Row074 left alone; "
        f"no Wan re-fetch; no 017 redo; EC2 unused. Blocker: {rel_packet}"
    )
    evidence = f"{rel_art}; {rel_delta}; {rel_packet}; {rel_hold}"

    rewrite_csv(
        SOUND_TRACKER,
        "Tracker_ID",
        {
            "TRK-W64-084": {
                "Status": status,
                "Status_Decision": decision,
                "Notes": notes,
                "Evidence_Path": evidence,
            }
        },
    )
    rewrite_csv(
        SOUND_ITEMS,
        "Item_ID",
        {
            "ITEM-W64-084": {
                "Status": status,
                "Notes": notes,
            }
        },
    )

    delta = load(DELTA)
    delta["csv_sync"] = "synced_by_land_row084_compiler_hard_fail_blocker"
    delta["csv_sync_tip"] = tip
    delta["ledger_vocabulary_sync"] = {
        "ledger_status": status,
        "note": f"COMPILER_HARD_FAIL not-clearable blocker from tip {tip}; no COMPLETE.",
        "product_completion": False,
        "runtime_completion": False,
        "synced_at": NOW,
        "prove_commits": [tip],
        "compiler_hard_fail_clearable": False,
        "row074_left_alone": True,
        "ec2_unused": True,
    }
    dump(DELTA, delta)

    packet = load(PACKET)
    packet["csv_sync"] = "synced_by_land_row084_compiler_hard_fail_blocker"
    packet["csv_sync_tip"] = tip
    dump(PACKET, packet)

    print("packet_sha", packet_sha)
    print("tip", tip)
    print("clearable=no; ROW084-011 FAIL; ROW084-012 OPEN_HOLD; row_complete=false")


if __name__ == "__main__":
    main()
