#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: Row084 Class E prod cut/camera+visual/contact blocker.

Row074 untouched. Never COMPLETE. ROW084-012 OPEN_HOLD untouched.
"""
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
ROW084_PACKET = (
    f"{EVID}/TRK-W64-084_ROW084-011_CLASS_E_PROD_CUT_CAMERA_VISUAL_CONTACT_BLOCKER_20260721.json"
)
ROW084_DELTA = f"{EVID}/TRK-W64-084_CANONICAL_VIDEO_TIMELINE_CURRENT_DELTA_20260719.json"
ROW084_ARTIFACT = f"{EVID}/TRK-W64-084_canonical_video_timeline.json"
ROW084_HOLD_012 = (
    f"{EVID}/TRK-W64-084_ROW084-012_CLASS_C_SCHEMA_NATIVE_REVERSED_PTS_HOLD_PACKET_20260720.json"
)
ROW084_RECEIPT = (
    f"{EVID}/fixtures/row084/runtime/local_class_e_prod_cut_camera_visual_contact_20260721T104800Z/"
    "class_e_prod_cut_camera_visual_contact_blocker_receipt.json"
)
ROW084_HARD_FAIL = (
    f"{EVID}/TRK-W64-084_ROW084-011_COMPILER_HARD_FAIL_NOT_CLEARABLE_BLOCKER_PACKET_20260721.json"
)
PRIOR_PROMPT = "8681ba01-58a4-4a92-92cf-171d5c2daaf3"
MEDIA_SHA = "0c1153e675bd9209ce9c56d6c6694d9fb93118d69e3935fedcf77e626fed998a"
PROOF = "RUNTIME_PROD_CUT_CAMERA_VISUAL_CONTACT_BLOCKER_BOUNDED"
HOLD_012_SHA = "0e0c3d8648f939f24684be7a9b7ad70aef20b1289f6fadd30d90256dbdeb1ff7"


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8"))


def dump_json(rel: str, obj: dict) -> None:
    path = ROOT / rel.replace("/", "\\")
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
    packet = load_json(ROW084_PACKET)
    receipt = load_json(ROW084_RECEIPT)
    hold_path = ROOT / ROW084_HOLD_012.replace("/", "\\")
    assert sha256_file(hold_path) == HOLD_012_SHA, "REFUSING: 012 HOLD mutated"

    assert packet.get("row_complete") is False
    assert packet.get("production_completion_allowed") is False
    assert packet.get("row084_011_status") == "FAIL"
    assert packet.get("cleared") is False
    assert packet.get("hold_012_unchanged", {}).get("status") == "OPEN_HOLD"
    assert packet.get("production_cut_camera_authority_granted") is False
    assert packet.get("production_combined_visual_contact_pass") is False
    assert receipt.get("production_mux_replay_pass") is True
    assert receipt["cut_camera_eval"]["candidate_probe"]["observed_class"] == "sparse_motion"
    assert receipt["media"]["sha256"] == MEDIA_SHA
    assert receipt["visual_contact_eval"]["local_gold_inventory"][
        "gold_authority_paths_absent"
    ] == "7/7"

    roles_absent = packet["gates"]["production_cut_camera_benchmark_authority"]["roles_absent"]
    row084_status = (
        "Blocked_Visual_Qa_Pass_Bounded_Class_C_Schema_Native_Hold_And_Production_Completion_Blocked"
    )
    row084_decision = "row084_class_e_prod_cut_camera_visual_contact_blocker_no_complete"
    row084_notes = (
        f"Class E prod cut/camera+visual/contact blocker: genuine AV-sync sha={MEDIA_SHA[:12]} "
        f"({PROOF}); observed_class=sparse_motion retained; cut/camera benchmark FAIL "
        f"(roles_absent={roles_absent}); visual/contact FAIL (local+RunPod gold 7/7 ABSENT; "
        "no invent); production_mux_replay_pass=true retained; "
        "production_cut_camera_authority_granted=false; compiler hard-fail retained. "
        f"Prior Comfy gen prompt_id={PRIOR_PROMPT} NON-AUTHORITY. ROW084-011 Class E "
        "FAIL/OPEN; ROW084-012 OPEN_HOLD unchanged (0e0c3d86); row_complete=false; "
        f"NEVER Complete; Row074 left alone; Local+RunPod cite (no EC2). Evidence: "
        f"{ROW084_PACKET}; {ROW084_RECEIPT}; {ROW084_HARD_FAIL}; {ROW084_DELTA}; "
        f"{ROW084_HOLD_012}"
    )
    row084_evidence = (
        f"{ROW084_ARTIFACT}; {ROW084_DELTA}; {ROW084_PACKET}; "
        f"{ROW084_RECEIPT}; {ROW084_HARD_FAIL}; {ROW084_HOLD_012}"
    )

    rewrite_csv(
        SOUND_TRACKER,
        "Tracker_ID",
        {
            "TRK-W64-084": {
                "Status": row084_status,
                "Status_Decision": row084_decision,
                "Notes": row084_notes,
                "Evidence_Path": row084_evidence,
            }
        },
    )
    rewrite_csv(
        SOUND_ITEMS,
        "Item_ID",
        {
            "ITEM-W64-084": {
                "Status": row084_status,
                "Notes": row084_notes,
            }
        },
    )

    delta = load_json(ROW084_DELTA)
    delta["updated_at"] = NOW
    delta["row_complete"] = False
    delta["proof_tier"] = PROOF
    delta["highest_proof_tier_achieved"] = PROOF
    delta["ledger_vocabulary_sync"] = {
        "ledger_status": row084_status,
        "note": (
            f"Mechanical CSV mutator Row084 Class E prod cut/camera+visual/contact "
            f"blocker from tip {tip}; no COMPLETE."
        ),
        "product_completion": False,
        "runtime_completion": False,
        "synced_at": NOW,
        "prove_commits": [tip],
        "prior_prompt_id_non_authority": PRIOR_PROMPT,
        "media_sha256": MEDIA_SHA,
        "production_mux_replay_pass": True,
        "observed_class": "sparse_motion",
        "production_cut_camera_authority_granted": False,
        "production_combined_visual_contact_pass": False,
        "ec2_unused": True,
        "row074_left_alone": True,
    }
    dump_json(ROW084_DELTA, delta)
    print(
        "Notes synced for TRK/ITEM-W64-084; Row074 untouched; "
        "cut/camera+visual/contact FAIL/OPEN landed"
    )


if __name__ == "__main__":
    main()
