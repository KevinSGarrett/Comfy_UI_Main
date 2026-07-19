import csv
import importlib.util
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = PROJECT_ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_autonomous_sound_intelligence_control_package.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("sound_control_package", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_control_package_validation_passes():
    result = _load_module().validate()
    assert result["status"] == "PASS"
    assert result["row_count"] == 46
    assert result["planning_complete_runtime_complete"] is False


def test_item_tracker_rows_are_contiguous_and_mirrored():
    module = _load_module()
    with module.ITEMS_CSV.open(encoding="utf-8", newline="") as handle:
        items = list(csv.DictReader(handle))
    with module.TRACKER_CSV.open(encoding="utf-8", newline="") as handle:
        trackers = list(csv.DictReader(handle))
    assert [row["Item_ID"] for row in items] == [f"ITEM-W64-{row:03d}" for row in range(67, 113)]
    assert [row["Tracker_ID"] for row in trackers] == [f"TRK-W64-{row:03d}" for row in range(67, 113)]
    assert all(row["Status"] == module.STATUS for row in items + trackers)


def test_requirements_and_evidence_mirrors_are_exact():
    module = _load_module()
    assert module.ITEMS_REQUIREMENTS.read_bytes() == module.TRACKER_REQUIREMENTS.read_bytes()
    assert module.EVIDENCE.read_bytes() == module.TRACKER_EVIDENCE.read_bytes()
    payload = json.loads(module.ITEMS_REQUIREMENTS.read_text(encoding="utf-8"))
    assert payload["planning_complete_runtime_complete"] is False
    assert payload["inventory_boundary"]["content_based_suppression"] is False


def test_all_dependencies_point_to_prior_reserved_rows():
    module = _load_module()
    for work in module.WORK_PACKAGES:
        assert all(67 <= dependency < work.row for dependency in work.dependencies)
