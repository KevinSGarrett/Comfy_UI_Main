from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_aqa_sole_pod_qualification_queue.py"


def load_module():
    spec = importlib.util.spec_from_file_location("w64_aqa_qualification_queue", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_queue_replays_with_two_support_campaigns_and_all_twelve_roles() -> None:
    module = load_module()
    queue = module.compile_queue(ROOT)
    assert len(queue["campaigns"]) == 14
    assert queue["coverage"]["all_matrix_roles_bound"] is True
    assert queue["coverage"]["role_campaign_count"] == 12
    assert queue["next_action"]["campaign_id"] == "W64-AQA-CAMPAIGN-ROLE-FAST-TRIAGE"
    assert queue["next_action"]["runnable_now"] is False
    assert queue["authority"] == {
        "execution_planning": True, "runtime": False, "capacity": False,
        "quality": False, "independent_juror": False, "golden_mask": False,
        "activation": False, "promotion": False,
    }


def test_audio_order_is_alignment_then_event_then_exact_audio_role() -> None:
    module = load_module()
    campaigns = module.compile_queue(ROOT)["campaigns"]
    assert campaigns[0]["component"] == "wav2vec2_forced_alignment"
    assert campaigns[0]["readiness"] == "COMPLETED_ACCEPTED_EXACT_SCOPE"
    assert campaigns[0]["blockers"] == []
    assert campaigns[0]["acceptance"]["status"] == "PARTIALLY_ADOPTED_EXACT_WAV2VEC2_ALIGNMENT_CONTROLS_ONLY"
    assert campaigns[1]["component"] == "mit_ast_audioset_event_detection"
    assert campaigns[1]["readiness"] == "COMPLETED_REJECTED_EXACT_SCOPE"
    assert campaigns[1]["acceptance"]["status"] == "REJECTED_SEMANTIC_CALIBRATION_TOP3_GATE_MISS"
    assert campaigns[1]["blockers"] == [
        "TERMINAL_SEMANTIC_CALIBRATION_REJECTION_REPLACEMENT_STRATEGY_REQUIRED"
    ]
    audio = next(item for item in campaigns if item["role_id"] == "W64-AQA-ROLE-AUDIO-SEMANTIC")
    assert audio["package_ids"] == ["W64-AQA-PKG-QWEN3-ASR-17B", "W64-AQA-PKG-QWEN3-OMNI-30B-A3B"]
    assert audio["readiness"] == "PREPARED_DEPENDENCIES_AND_COORDINATOR_GATE_REQUIRED"
    assert audio["depends_on"] == [campaigns[0]["campaign_id"], campaigns[1]["campaign_id"]]


def test_deterministic_role_is_qualified_only_by_current_matrix_bound_certificate() -> None:
    module = load_module()
    campaign = next(
        item for item in module.compile_queue(ROOT)["campaigns"]
        if item["role_id"] == "W64-AQA-ROLE-DETERMINISTIC"
    )
    assert campaign["readiness"] == "QUALIFIED_DECLARED_LOCAL_SCOPE"
    assert campaign["operational"] is True
    assert campaign["blockers"] == []
    assert campaign["certificate"]["certificate_id"] == "c5f5e1216f524b8761e3876b944993f481a8b70b00b94179b5082b0e46ab16f4"
    assert campaign["certificate"]["bundle_id"] == "3914859c7450c0b40a54459e78fc8a1cca8ffc94a61c7f29401ce1b91a18f25d"


def test_generation_role_binds_exact_inactive_stack_without_execution_authority() -> None:
    module = load_module()
    campaign = next(
        item for item in module.compile_queue(ROOT)["campaigns"]
        if item["role_id"] == "W64-AQA-ROLE-GENERATION"
    )
    assert campaign["readiness"] == "HELD_PREREQUISITES_INCOMPLETE"
    assert campaign["generation_stack"]["stack_id"] == "W64-AQA-GEN-FLUX2-KLEIN-4B-FP8"
    assert campaign["generation_stack"]["exact_storage_identity_bound"] is True
    assert campaign["generation_stack"]["executable"] is False
    assert campaign["generation_stack"]["current_pod_complete"] is False
    assert campaign["generation_stack"]["dependency_bundle_id"] == "e939807282ddd3cacc921754c851dd70d5f22f4d957f87d48ac226d1ee73d689"
    assert "PROJECT_LICENSE_ACCEPTANCE_MISSING" in campaign["blockers"]
    assert "EXACT_KLEIN_VAE_CURRENT_POD_IDENTITY_MISMATCH" in campaign["blockers"]
    assert "CURRENT_POD_DEPENDENCY_COMPATIBILITY_NOT_QUALIFIED" in campaign["blockers"]
    assert "CURRENT_POD_OBJECT_INFO_AND_ISOLATED_WORKFLOW_SMOKE_NOT_VERIFIED" not in campaign["blockers"]
    assert "EXACT_GENERATION_STACK_NOT_BOUND_TO_ROLE_PACKAGE_INVENTORY" not in campaign["blockers"]


def test_exact_strict_role_is_prepared_but_downgraded_identity_fails_closed() -> None:
    module = load_module()
    campaigns = module.compile_queue(ROOT)["campaigns"]
    strict = next(item for item in campaigns if item["role_id"] == "W64-AQA-ROLE-STRICT-VISUAL")
    assert strict["readiness"] == "PREPARED_DEPENDENCIES_AND_COORDINATOR_GATE_REQUIRED"
    assert strict["package_evidence"][0]["exact_identity_installed_and_license_accepted"] is True
    assert strict["blockers"] == ["FRESH_COORDINATOR_ADMISSION_AND_EXACT_EXCLUSIVE_LEASE_REQUIRED"]
    controller = next(item for item in campaigns if item["role_id"] == "W64-AQA-ROLE-CONTROLLER")
    assert controller["readiness"] == "PREPARED_DEPENDENCIES_AND_COORDINATOR_GATE_REQUIRED"
    assert controller["package_evidence"][0]["exact_identity_installed_and_license_accepted"] is True
    assert controller["package_evidence"][0]["dependency_environment_required"] is False
    assert controller["package_evidence"][0]["dependency_environment_ready"] is True
    assert controller["blockers"] == ["FRESH_COORDINATOR_ADMISSION_AND_EXACT_EXCLUSIVE_LEASE_REQUIRED"]
    inventory = json.loads((ROOT / module.INVENTORY_PATH).read_text(encoding="utf-8"))
    local = next(item for item in inventory["packages"] if item["package_id"] == "W64-AQA-PKG-QWEN25VL32")
    local["identity"]["identity_state"] = "LOCAL_DIGEST_VERIFIED_UPSTREAM_REVISION_UNVERIFIED"
    evidence, blockers = module.package_evidence(local)
    assert evidence["exact_identity_installed_and_license_accepted"] is False
    assert any("EXACT_UPSTREAM_REVISION_OR_IDENTITY_NOT_VERIFIED" in value for value in blockers)


def test_not_accepted_license_text_never_satisfies_project_acceptance() -> None:
    module = load_module()
    inventory = json.loads((ROOT / module.INVENTORY_PATH).read_text(encoding="utf-8"))
    llava = next(item for item in inventory["packages"] if item["package_id"] == "W64-AQA-PKG-LLAVA13")
    evidence, blockers = module.package_evidence(llava)
    assert evidence["license_state"].endswith("NOT_ACCEPTED")
    assert evidence["exact_identity_installed_and_license_accepted"] is False
    assert blockers == ["W64-AQA-PKG-LLAVA13:PROJECT_LICENSE_ACCEPTANCE_MISSING"]


def test_provisional_juror_and_external_mask_release_fail_closed() -> None:
    module = load_module()
    campaigns = module.compile_queue(ROOT)["campaigns"]
    juror = next(item for item in campaigns if item["role_id"] == "W64-AQA-ROLE-INDEPENDENT-JUROR")
    assert juror["package_ids"] == ["W64-AQA-PKG-INTERNVL35-241B-A28B"]
    assert "PROVISIONAL_INTERNVL35_8B_CANNOT_SUBSTITUTE_FOR_241B_TARGET" in juror["blockers"]
    mask = next(item for item in campaigns if item["role_id"] == "W64-AQA-ROLE-GOLDEN-MASK")
    assert mask["execution_lane"] == "external_release_consumer"
    assert mask["readiness"] == "HELD_PREREQUISITES_INCOMPLETE"


def test_matrix_role_drift_and_admission_status_drift_are_rejected(tmp_path: Path) -> None:
    module = load_module()
    copied = tmp_path / "repo"
    registry = json.loads((ROOT / module.GENERATION_STACK_PATH).read_text(encoding="utf-8"))
    dependency_path = Path(next(item for item in registry["stacks"] if item["selection_state"] == "SELECTED_INACTIVE")["dependency_bundle"]["path"])
    for relative in (module.MATRIX_PATH, module.ROLE_REGISTRY_PATH, module.INVENTORY_PATH, module.POLICY_PATH, module.GENERATION_STACK_PATH, module.GENERATION_STACK_SCHEMA_PATH, module.GENERATION_DEPENDENCY_SCHEMA_PATH, dependency_path, module.SCHEMA_PATH):
        target = copied / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    for source in json.loads((ROOT / module.POLICY_PATH).read_text(encoding="utf-8"))["pre_role_campaigns"]:
        relative = Path(source["admission_path"])
        target = copied / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    matrix = json.loads((copied / module.MATRIX_PATH).read_text(encoding="utf-8"))
    matrix["role_plans"] = matrix["role_plans"][:-1]
    (copied / module.MATRIX_PATH).write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(module.QueueError, match="twelve unique roles"):
        module.compile_queue(copied)
    (copied / module.MATRIX_PATH).write_bytes((ROOT / module.MATRIX_PATH).read_bytes())
    first_admission = Path(json.loads((copied / module.POLICY_PATH).read_text(encoding="utf-8"))["pre_role_campaigns"][0]["admission_path"])
    admission = json.loads((copied / first_admission).read_text(encoding="utf-8"))
    admission["status"] = "DRIFTED"
    (copied / first_admission).write_text(json.dumps(admission), encoding="utf-8")
    with pytest.raises(module.QueueError, match="admission status drift"):
        module.compile_queue(copied)


@pytest.mark.parametrize("package_index", [0, 1])
def test_generation_stack_package_hash_drift_is_rejected(tmp_path: Path, package_index: int) -> None:
    module = load_module()
    copied = tmp_path / "repo"
    registry = json.loads((ROOT / module.GENERATION_STACK_PATH).read_text(encoding="utf-8"))
    dependency_path = Path(next(item for item in registry["stacks"] if item["selection_state"] == "SELECTED_INACTIVE")["dependency_bundle"]["path"])
    relatives = (module.MATRIX_PATH, module.ROLE_REGISTRY_PATH, module.INVENTORY_PATH, module.POLICY_PATH, module.GENERATION_STACK_PATH, module.GENERATION_STACK_SCHEMA_PATH, module.GENERATION_DEPENDENCY_SCHEMA_PATH, dependency_path, module.SCHEMA_PATH)
    policy = json.loads((ROOT / module.POLICY_PATH).read_text(encoding="utf-8"))
    package_paths = [Path(stack["package_binding"]["path"]) for stack in registry["stacks"]]
    admission_paths = [Path(item["admission_path"]) for item in policy["pre_role_campaigns"]]
    acceptance_paths = [
        Path(item[key])
        for item in policy["pre_role_campaigns"]
        for key in ("acceptance_path", "rejection_path")
        if item.get(key)
    ]
    certificate_paths = [
        Path(binding[key])
        for binding in policy["role_bindings"]
        for key in ("certificate_path", "bundle_path")
        if binding.get(key)
    ]
    executor_paths = []
    for bundle_path in [path for path in certificate_paths if path.name == "execution_bundle.json"]:
        bundle = json.loads((ROOT / bundle_path).read_text(encoding="utf-8"))
        executor_paths.append(Path(bundle["inputs"]["executor"]["path"]))
    for relative in (
        *relatives,
        *package_paths,
        *admission_paths,
        *acceptance_paths,
        *certificate_paths,
        *executor_paths,
    ):
        target = copied / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    drifted_package = copied / package_paths[package_index]
    drifted_package.write_bytes(drifted_package.read_bytes() + b"\n")
    with pytest.raises(module.QueueError, match="package hash drift"):
        module.compile_queue(copied)


def test_checked_in_queue_matches_compiler() -> None:
    module = load_module()
    checked_in = ROOT / module.DEFAULT_OUTPUT
    module.validate_queue(ROOT, json.loads(checked_in.read_text(encoding="utf-8")))
