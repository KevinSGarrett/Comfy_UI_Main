#!/usr/bin/env python3
"""Synchronize exact Row137 fixture-storage progress without rewriting unrelated rows."""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
OLD_STATUS = "Implementation_Active_LatentSync_Environment_And_Imports_Pass_Model_Load_Video_Fixture_And_AV_QA_Pending"
STATUS = "Implementation_Active_LatentSync_Environment_Imports_And_Fixture_Pass_Model_Load_And_AV_QA_Pending"
OLD_ACTION = (
    "Acquire an exact coordinator GPU lease for a separately admitted model-load canary and "
    "independently create or select an immutable rights-qualified face-video identity fixture "
    "before inference; re-budget storage before any large install."
)
ACTION = (
    "Wait for the foreign coordinator RECOVERY_REQUIRED state to be resolved by its owning "
    "project; then acquire an exact comfyui_main lease for a separately admitted LatentSync "
    "UNet model-load and unload canary without overriding the foreign lease."
)
NOTES = (
    "Exact model storage, code, environment, compatibility, and imports pass. The immutable "
    "project-generated fictional-adult video plus public-domain speech fixture is rights-scoped, "
    "atomically installed, hash-verified, and replayed. Its known identity and light-color drift "
    "remain non-golden. Model load and inference are pending because the shared coordinator is "
    "in a foreign MaskFactory RECOVERY_REQUIRED state; ComfyUI did not clear or override it."
)
EVIDENCE = (
    "Plan/Tracker/Evidence/W64_AQA_LATENTSYNC_FIXTURE_STORAGE_20260722T093100Z/"
    "integration_acceptance.json"
)


def head_text(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    return subprocess.run(
        ["git", "show", f"HEAD:{relative}"], cwd=ROOT, check=True, stdout=subprocess.PIPE
    ).stdout.decode("utf-8-sig")


def atomic_text(path: Path, payload: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def update_json_object(path: Path, replacements: dict[str, str]) -> None:
    payload = head_text(path)
    marker = '"tracker_id": "TRK-W64-137"'
    if payload.count(marker) != 1:
        raise RuntimeError(f"{path}: expected one Row137 object")
    marker_at = payload.index(marker)
    start = payload.rfind("{", 0, marker_at)
    end = payload.find("}", marker_at)
    row = payload[start : end + 1]
    for old, new in replacements.items():
        if row.count(old) != 1:
            raise RuntimeError(f"{path}: expected one exact source field")
        row = row.replace(old, new, 1)
    atomic_text(path, payload[:start] + row + payload[end + 1 :])


def update_csv(path: Path, key: str, updates: dict[str, dict[str, str]]) -> None:
    lines = head_text(path).splitlines(keepends=True)
    fields = next(csv.reader([lines[0]]))
    key_index = fields.index(key)
    matched: set[str] = set()
    output = [lines[0]]
    for line in lines[1:]:
        values = next(csv.reader([line]))
        identity = values[key_index]
        if identity in updates:
            row = dict(zip(fields, values, strict=True))
            row.update(updates[identity])
            buffer = io.StringIO(newline="")
            csv.writer(buffer, lineterminator="\n").writerow([row[name] for name in fields])
            output.append(buffer.getvalue())
            matched.add(identity)
        else:
            output.append(line)
    if matched != set(updates):
        raise RuntimeError(f"{path}: missing target rows")
    atomic_text(path, "".join(output))


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
        {f'"status": "{OLD_STATUS}"': f'"status": "{STATUS}"'},
    )
    update_csv(
        ROOT / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv",
        "Item_ID",
        {"ITEM-W64-137": {"Codex_Action": ACTION, "Evidence_Required": EVIDENCE, "Status": STATUS, "Notes": NOTES, "Coverage_Level": "latentsync_environment_imports_and_fixture_pass", "Coverage_Audit_Status": "model_load_and_av_qa_pending"}},
    )
    update_csv(
        ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv",
        "Tracker_ID",
        {"TRK-W64-137": {"Status": STATUS, "Detailed_Action": ACTION, "Output_Artifact": EVIDENCE, "Codex_Desktop_Action": ACTION, "Evidence_Path": EVIDENCE, "Status_Decision": "latentsync_environment_imports_and_fixture_pass_model_load_and_av_qa_pending", "Notes": NOTES, "Coverage_Level": "latentsync_environment_imports_and_fixture_pass", "Coverage_Audit_Status": "model_load_and_av_qa_pending"}},
    )
    aqa_status = "ASR_OMNI_CLAP_WAV2VEC2_BOUNDED_RUNTIME_PASS_LATENTSYNC_ENVIRONMENT_IMPORTS_AND_FIXTURE_PASS_MODEL_LOAD_PENDING"
    update_csv(
        ROOT / "Plan/Items/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_ITEM_ROWS.csv",
        "Item_ID",
        {"W64-AQA-017": {"Status": aqa_status, "Notes": NOTES}},
    )
    update_csv(
        ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_TRACKER_ROWS.csv",
        "Tracker_ID",
        {"W64-AQA-017": {"Status": aqa_status, "Runtime_Truth": "latentsync_storage_code_environment_imports_and_rights_scoped_fixture_pass_model_load_inference_pending_foreign_coordinator_recovery_hold", "Next_Action": ACTION, "Evidence_Path": EVIDENCE}},
    )
    print("ROW137_LATENTSYNC_FIXTURE_TRACKERS_SYNCHRONIZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
