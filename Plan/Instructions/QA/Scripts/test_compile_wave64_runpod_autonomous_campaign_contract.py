from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_campaign_contract.py"
SPEC = importlib.util.spec_from_file_location("campaign_compiler", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
H = "a" * 64


def draft() -> dict:
    roles = [
        ("W64-AQA-ROLE-CONTROLLER", "W64-AQA-FAMILY-QWEN-CONTROLLER", "5" * 64),
        ("W64-AQA-ROLE-IMPLEMENTER", "W64-AQA-FAMILY-QWEN-CODER", "1" * 64),
        ("W64-AQA-ROLE-REVIEWER", "W64-AQA-FAMILY-INTERNVL", "2" * 64),
        ("W64-AQA-ROLE-INDEPENDENT-JUROR", "W64-AQA-FAMILY-OMNI", "3" * 64),
        ("W64-AQA-ROLE-ARBITER", "W64-AQA-FAMILY-ARBITER", "4" * 64),
        ("W64-AQA-ROLE-REPAIR-PLANNER", "W64-AQA-FAMILY-QWEN-REPAIR", "6" * 64),
        ("W64-AQA-ROLE-DETERMINISTIC", "W64-AQA-FAMILY-DETERMINISTIC", "7" * 64),
        ("W64-AQA-ROLE-EVIDENCE-COMPILER", "W64-AQA-FAMILY-EVIDENCE", "8" * 64),
    ]
    return {
        "schema_version": "wave64.aqa.campaign.v1",
        "campaign_name": "cpu-shadow-001",
        "campaign_profile": "DEVELOPMENT_CAMPAIGN",
        "qualification_mode": "STATIC_SHADOW",
        "repository": {"remote": "https://example.invalid/repo.git", "commit_sha256": H, "tree_sha256": H},
        "policy": {"policy_id": "W64-AQA-TOOL-POLICY-002", "policy_sha256": H, "max_attempts": 2, "repair_attempts": 1, "abstain_on_unqualified_role": True},
        "jobs": [
            {"node_id": "a", "contract_path": "contracts/a.json", "contract_sha256": H, "contract_id": H, "input_sha256": H, "runtime_sha256": H, "prompt_sha256": H, "environment_sha256": H, "role_id": "W64-AQA-ROLE-IMPLEMENTER", "phase": "CPU", "stage": "GENERATE_OR_IMPLEMENT", "modality": "CODE", "risk_tier": "HIGH", "residency_group": "code", "estimated_vram_gib": 0, "continue_unrelated_branches": True},
            {"node_id": "b", "contract_path": "contracts/b.json", "contract_sha256": H, "contract_id": H, "input_sha256": H, "runtime_sha256": H, "prompt_sha256": H, "environment_sha256": H, "role_id": "W64-AQA-ROLE-REVIEWER", "phase": "GPU", "stage": "PRIMARY_REVIEW", "modality": "CODE", "risk_tier": "HIGH", "residency_group": "review", "estimated_vram_gib": 8, "continue_unrelated_branches": True},
        ],
        "dag": [{"node_id": "a", "depends_on": []}, {"node_id": "b", "depends_on": ["a"]}],
        "model_bindings": [{"role_id": r, "family_id": f, "checkpoint_sha256": c, "qualification_state": "QUALIFIED"} for r, f, c in roles],
        "bulk_manifest": None,
        "authority": {"runpod_may_execute_isolated_batches": True, "runpod_may_propose_deltas": True, "runpod_may_push_git": False, "runpod_may_promote": False, "runpod_may_spend": False, "runpod_may_override_foreign_lease": False, "final_acceptance_authority": "CODEX"},
    }


def test_compile_verify_is_deterministic_and_ordered() -> None:
    first = MODULE.compile_contract(draft())
    second = MODULE.compile_contract(draft())
    assert first == second
    MODULE.verify_contract(first)
    assert MODULE.topological_order(first) == ["a", "b"]


@pytest.mark.parametrize("field", ["contract_sha256", "contract_id", "input_sha256", "runtime_sha256", "prompt_sha256"])
def test_rejects_missing_exact_hash(field: str) -> None:
    value = draft()
    del value["jobs"][0][field]
    with pytest.raises(MODULE.CampaignError, match="schema violation"):
        MODULE.compile_contract(value)


def test_rejects_cycle_and_missing_dependency() -> None:
    value = draft()
    value["dag"][0]["depends_on"] = ["b"]
    with pytest.raises(MODULE.CampaignError, match="cycle"):
        MODULE.compile_contract(value)
    value = draft()
    value["dag"][1]["depends_on"] = ["missing"]
    with pytest.raises(MODULE.CampaignError, match="missing dependencies"):
        MODULE.compile_contract(value)


@pytest.mark.parametrize("path", ["../escape.json", "/absolute.json", "C:\\escape.json"])
def test_rejects_path_escape(path: str) -> None:
    value = draft()
    value["jobs"][0]["contract_path"] = path
    with pytest.raises(MODULE.CampaignError):
        MODULE.compile_contract(value)


def test_rejects_self_review_and_represents_unqualified_authority() -> None:
    value = draft()
    bindings = {item["role_id"]: item for item in value["model_bindings"]}
    bindings["W64-AQA-ROLE-REVIEWER"]["family_id"] = bindings[
        "W64-AQA-ROLE-IMPLEMENTER"
    ]["family_id"]
    with pytest.raises(MODULE.CampaignError, match="independent model families"):
        MODULE.compile_contract(value)
    value = draft()
    binding = next(
        item
        for item in value["model_bindings"]
        if item["role_id"] == "W64-AQA-ROLE-INDEPENDENT-JUROR"
    )
    binding["qualification_state"] = "UNQUALIFIED"
    assert MODULE.compile_contract(value)["admission_disposition"] == "BLOCKED_UNQUALIFIED"


def test_new_bundle_role_unqualified_blocks_admission() -> None:
    value = draft()
    binding = next(
        item
        for item in value["model_bindings"]
        if item["role_id"] == "W64-AQA-ROLE-REPAIR-PLANNER"
    )
    binding["qualification_state"] = "UNQUALIFIED"
    assert MODULE.compile_contract(value)["admission_disposition"] == "BLOCKED_UNQUALIFIED"


def test_missing_bundle_role_is_rejected_exactly() -> None:
    value = draft()
    value["model_bindings"] = [
        item
        for item in value["model_bindings"]
        if item["role_id"] != "W64-AQA-ROLE-EVIDENCE-COMPILER"
    ]
    with pytest.raises(
        MODULE.CampaignError,
        match=r"required campaign roles are missing: \['W64-AQA-ROLE-EVIDENCE-COMPILER'\]",
    ):
        MODULE.compile_contract(value)


@pytest.mark.parametrize("field", ["runpod_may_push_git", "runpod_may_promote", "runpod_may_spend", "runpod_may_override_foreign_lease"])
def test_rejects_authority_weakening(field: str) -> None:
    value = draft()
    value["authority"][field] = True
    with pytest.raises(MODULE.CampaignError, match="schema violation"):
        MODULE.compile_contract(value)


def test_rejects_tampered_compiled_contract() -> None:
    contract = MODULE.compile_contract(draft())
    tampered = copy.deepcopy(contract)
    tampered["jobs"][0]["input_sha256"] = "b" * 64
    with pytest.raises(MODULE.CampaignError, match="campaign_id"):
        MODULE.verify_contract(tampered)


def test_verifies_exact_sealed_child_bytes_and_id(tmp_path: Path) -> None:
    value = draft()
    child = {"contract_id": H, "payload": "sealed"}
    payload = MODULE.canonical_bytes(child)
    child_path = tmp_path / "contracts" / "a.json"
    child_path.parent.mkdir()
    child_path.write_bytes(payload)
    value["jobs"] = [value["jobs"][0]]
    value["dag"] = [{"node_id": "a", "depends_on": []}]
    value["jobs"][0]["contract_sha256"] = MODULE.hashlib.sha256(payload).hexdigest()
    compiled = MODULE.compile_contract(value)
    MODULE.verify_sealed_job_bytes(compiled, tmp_path)
    child_path.write_text('{"contract_id":"' + H + '","payload":"tampered"}', encoding="utf-8")
    with pytest.raises(MODULE.CampaignError, match="hash mismatch"):
        MODULE.verify_sealed_job_bytes(compiled, tmp_path)


def test_multimodal_profile_requires_frozen_manifest() -> None:
    value = draft()
    value["campaign_profile"] = "MULTIMODAL_MEDIA_CAMPAIGN"
    with pytest.raises(MODULE.CampaignError, match="frozen bulk manifest"):
        MODULE.compile_contract(value)


def test_non_shadow_requires_complete_closed_loop() -> None:
    value = draft()
    value["qualification_mode"] = "ISOLATED_QUALIFICATION"
    with pytest.raises(MODULE.CampaignError, match="missing closed-loop stages"):
        MODULE.compile_contract(value)
