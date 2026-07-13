from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path(__file__).with_name("implement_wave64_organization_system.py")
SPEC = spec_from_file_location("row057_organization", SCRIPT)
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_debt_present_stays_blocked():
    runtime = [f"runtime_artifacts/example_{index}.json" for index in range(84)]
    archives = ["Comfy_UI_Main_Autonomous_Codex_Desktop_Waves58_62_Cumulative.zip"]
    state = MODULE.organization_state(runtime, archives)
    assert state["blocked"] is True
    assert state["status"] == "Blocked_Legacy_Tracked_Placement_Debt"
    assert state["qa_decision"] == "organization_governance_controls_pass_legacy_placement_debt_blocked"
    assert len(state["placement_debt"]) == 85
    assert "85 tracked violations" in state["next_action"]


def test_zero_debt_completes_row():
    state = MODULE.organization_state([], [])
    assert state["blocked"] is False
    assert state["status"] == "Completed_Current_Organization_Governance_Pass"
    assert state["qa_decision"] == "organization_governance_pass_no_tracked_placement_debt"
    assert state["placement_debt"] == []
    assert "tracked placement debt is zero" in state["next_action"]


if __name__ == "__main__":
    test_debt_present_stays_blocked()
    test_zero_debt_completes_row()
    print("ROW057_ORGANIZATION_STATE_TESTS_PASS 2/2")
