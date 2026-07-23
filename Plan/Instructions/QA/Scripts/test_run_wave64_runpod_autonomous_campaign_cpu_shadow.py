from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_campaign_cpu_shadow.py"
SPEC = importlib.util.spec_from_file_location("shadow", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_exact_18_task_cpu_shadow(tmp_path: Path) -> None:
    packet = MODULE.execute(tmp_path / "shadow")
    assert packet["assertions"]["task_count"] == 18
    assert packet["assertions"]["all_static_shadow_gates_pass"] is True
    assert packet["assertions"]["durable_mission_terminal"] is True
    assert packet["assertions"]["durable_mission_result_bound"] is True
    assert packet["assertions"]["deliberate_crash_recovered"] is True
    assert packet["assertions"]["mission_queue_cleanup_complete"] is True
    assert packet["assertions"]["production_roles_qualified"] is False
    assert packet["result"]["metrics"]["evidence_completeness_rate"] == 1.0
    assert packet["result"]["metrics"]["known_bad_false_accepts"] == 0
    assert packet["result"]["metrics"]["first_pass_validation_rate"] >= 0.70
