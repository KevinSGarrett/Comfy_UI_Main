from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_PATH = (
    ROOT
    / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_autonomous_multimodal_qa_control_package.py"
)


def load_validator():
    spec = importlib.util.spec_from_file_location("w64_aqa_validator", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_control_package_validator_passes() -> None:
    validator = load_validator()
    assert validator.collect_errors() == []


def test_item_tracker_and_requirement_ids_match() -> None:
    items_path = (
        ROOT / "Plan/Items/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_ITEM_ROWS.csv"
    )
    tracker_path = (
        ROOT
        / "Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_TRACKER_ROWS.csv"
    )
    requirements_path = (
        ROOT
        / "Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_REQUIREMENTS.json"
    )
    with items_path.open(newline="", encoding="utf-8") as handle:
        item_ids = {row["Item_ID"] for row in csv.DictReader(handle)}
    with tracker_path.open(newline="", encoding="utf-8") as handle:
        tracker_ids = {row["Tracker_ID"] for row in csv.DictReader(handle)}
    requirement_ids = {
        row["id"] for row in json.loads(requirements_path.read_text(encoding="utf-8"))["requirements"]
    }
    assert item_ids == tracker_ids == requirement_ids
    assert len(item_ids) == 16


def test_current_and_future_authority_are_separated() -> None:
    registry_path = (
        ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_multimodal_qa_role_registry.json"
    )
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    roles = {role["role_id"]: role for role in registry["roles"]}
    assert roles["W64-AQA-ROLE-STRICT-VISUAL"]["model"] == "qwen2.5vl:32b"
    assert not roles["W64-AQA-ROLE-FAST-TRIAGE"]["product_approval_sufficient"]
    assert not roles["W64-AQA-ROLE-MULTIGPU-ARBITER"]["current_48gb_pod_eligible"]
    assert roles["W64-AQA-ROLE-WORKFLOW-ENGINEER"]["proposal_only"]


def test_attempt_ceilings_are_fail_closed() -> None:
    registry_path = (
        ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_multimodal_qa_role_registry.json"
    )
    runtime = json.loads(registry_path.read_text(encoding="utf-8"))["runtime_policy"]
    assert runtime["max_repair_attempts_per_defect"] == 2
    assert runtime["max_total_generation_attempts"] == 4
    assert runtime["max_no_progress_cycles"] == 2


def test_schema_covers_all_required_modalities() -> None:
    schema_path = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_multimodal_qa_decision.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert set(schema["properties"]["modality"]["enum"]) == {
        "image",
        "video",
        "audio",
        "av",
        "mask",
        "workflow",
    }
