#!/usr/bin/env python3
"""Synchronize exact Row137 environment/import progress across authoritative trackers."""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
STATUS = "Implementation_Active_LatentSync_Environment_And_Imports_Pass_Model_Load_Video_Fixture_And_AV_QA_Pending"
STATUS_DECISION = "latentsync_environment_and_imports_pass_model_load_video_fixture_and_av_qa_pending"
OLD_STATUS = "Implementation_Active_LatentSync_Storage_Code_Lock_And_Source_Wheels_Pass_Isolated_Environment_And_Video_Fixture_Pending"
OLD_ACTION = (
    "Admit and build the isolated Python 3.11/cu121 runtime environment from the accepted "
    "hash lock plus the three exact local source wheels; independently create or select an "
    "immutable rights-qualified face-video identity fixture before requesting a model-load lease."
)
ACTION = (
    "Acquire an exact coordinator GPU lease for a separately admitted model-load canary and "
    "independently create or select an immutable rights-qualified face-video identity fixture "
    "before inference; re-budget storage before any large install."
)
NOTES = (
    "Exact model storage and code, the 149-package wheel-complete v2 lock, repaired decord "
    "metadata, isolated Python 3.11/cu121 environment, 149-package compatibility, and 18 "
    "package/project imports pass. Model load, rights-qualified source video, leased inference, "
    "identity, AV-sync, operational, and product authority remain false."
)
EVIDENCE = (
    "Plan/Tracker/Evidence/W64_AQA_LATENTSYNC_1_6_IMPORT_CANARY_20260722T091000Z/"
    "integration_acceptance.json"
)


def write_text_atomic(path: Path, payload: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def head_text(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    return subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout.decode("utf-8-sig")


def update_json_object(path: Path, replacements: dict[str, str]) -> None:
    payload = head_text(path)
    marker = '"tracker_id": "TRK-W64-137"'
    if payload.count(marker) != 1:
        raise RuntimeError(f"{path}: expected one Row137 object")
    marker_at = payload.index(marker)
    object_start = payload.rfind("{", 0, marker_at)
    object_end = payload.find("}", marker_at)
    if object_start < 0 or object_end < 0:
        raise RuntimeError(f"{path}: could not bound Row137 object")
    row_text = payload[object_start : object_end + 1]
    for old, new in replacements.items():
        if row_text.count(old) != 1:
            raise RuntimeError(f"{path}: expected one exact Row137 source field: {old}")
        row_text = row_text.replace(old, new, 1)
    write_text_atomic(path, payload[:object_start] + row_text + payload[object_end + 1 :])


def update_csv(path: Path, key: str, updates: dict[str, dict[str, str]]) -> None:
    baseline = head_text(path)
    lines = baseline.splitlines(keepends=True)
    if not lines:
        raise RuntimeError(f"{path}: missing CSV header")
    fieldnames = next(csv.reader([lines[0]]))
    if key not in fieldnames:
        raise RuntimeError(f"{path}: missing key column {key}")
    key_index = fieldnames.index(key)
    matched: set[str] = set()
    output_lines = [lines[0]]
    for line in lines[1:]:
        values = next(csv.reader([line]))
        if len(values) != len(fieldnames):
            raise RuntimeError(f"{path}: multiline or malformed CSV row is unsupported")
        identity = values[key_index]
        if identity in updates:
            row = dict(zip(fieldnames, values, strict=True))
            row.update(updates[identity])
            buffer = io.StringIO(newline="")
            csv.writer(buffer, lineterminator="\n").writerow([row[name] for name in fieldnames])
            output_lines.append(buffer.getvalue())
            matched.add(identity)
        else:
            output_lines.append(line)
    if matched != set(updates):
        raise RuntimeError(f"{path}: missing target rows: {set(updates) - matched}")
    write_text_atomic(path, "".join(output_lines))


def main() -> int:
    for relative in (
        "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_REQUIREMENTS.json",
        "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_REQUIREMENTS.json",
    ):
        update_json_object(
            ROOT / relative,
            {
                f'"status": "{OLD_STATUS}"': f'"status": "{STATUS}"',
                f'"implementation_action": "{OLD_ACTION}"': f'"implementation_action": "{ACTION}"',
            },
        )
    update_json_object(
        ROOT / "Plan/10_REGISTRIES/wave64_autonomous_hyperreal_speech_work_package_registry.json",
        {
            '"status": "Planned_Autonomous_Implementation_Required"':
                f'"status": "{STATUS}"'
        },
    )

    update_csv(
        ROOT / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv",
        "Item_ID",
        {
            "ITEM-W64-137": {
                "Codex_Action": ACTION,
                "Evidence_Required": EVIDENCE,
                "Blocker_Policy": "Environment and import success cannot be represented as model-load, inference, identity, AV-sync, operational, or product authority.",
                "Status": STATUS,
                "Notes": NOTES,
                "Coverage_Level": "latentsync_environment_and_imports_pass",
                "Coverage_Audit_Status": "model_load_video_fixture_and_av_qa_pending",
            }
        },
    )
    update_csv(
        ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv",
        "Tracker_ID",
        {
            "TRK-W64-137": {
                "Status": STATUS,
                "Detailed_Action": ACTION,
                "Output_Artifact": EVIDENCE,
                "Codex_Desktop_Action": ACTION,
                "Evidence_Path": EVIDENCE,
                "Rerun_Policy": "Preserve verified storage, code, wheel, environment, and import artifacts; never rerun leased model work without a material change.",
                "Status_Decision": STATUS_DECISION,
                "Notes": NOTES,
                "Coverage_Level": "latentsync_environment_and_imports_pass",
                "Coverage_Audit_Status": "model_load_video_fixture_and_av_qa_pending",
            }
        },
    )

    item_statuses = {
        "W64-AQA-017": "ASR_OMNI_CLAP_WAV2VEC2_BOUNDED_RUNTIME_PASS_LATENTSYNC_ENVIRONMENT_AND_IMPORTS_PASS_BROAD_ACTIVATION_PENDING",
        "W64-AQA-018": "TRANSFER_PASS_CLAP_BOUNDED_RUNTIME_PASS_LATENTSYNC_EXACT_STORAGE_ENVIRONMENT_AND_IMPORTS_PASS_REMAINING_PACKAGES_AND_QUARANTINE_PENDING",
    }
    update_csv(
        ROOT / "Plan/Items/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_ITEM_ROWS.csv",
        "Item_ID",
        {
            identity: {"Status": status, "Notes": NOTES}
            for identity, status in item_statuses.items()
        },
    )
    update_csv(
        ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_TRACKER_ROWS.csv",
        "Tracker_ID",
        {
            identity: {
                "Status": status,
                "Runtime_Truth": "latentsync_storage_code_wheel_complete_v2_environment_149_package_compatibility_and_18_imports_pass_model_load_inference_pending",
                "Next_Action": ACTION,
                "Evidence_Path": EVIDENCE,
            }
            for identity, status in item_statuses.items()
        },
    )
    print("ROW137_LATENTSYNC_ENVIRONMENT_IMPORT_TRACKERS_SYNCHRONIZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
