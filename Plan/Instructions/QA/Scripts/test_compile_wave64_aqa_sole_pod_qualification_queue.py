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
    assert queue["next_action"]["campaign_id"] == "W64-AQA-CAMPAIGN-WAV2VEC2-EXPANDED-ALIGNMENT"
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
    assert campaigns[1]["component"] == "mit_ast_audioset_event_detection"
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
    assert campaign["certificate"]["certificate_id"] == "81329165d759a60fc0b112dff3b606163a38bffa48b9c0f4d90a0ee4400296a1"
    assert campaign["certificate"]["bundle_id"] == "f385abbb1b4eda4b7ccd84f2b277818b782a167fd48eedb4c6724d60c9464253"


def test_local_digest_and_upstream_name_do_not_grant_exact_role_readiness() -> None:
    module = load_module()
    campaigns = module.compile_queue(ROOT)["campaigns"]
    strict = next(item for item in campaigns if item["role_id"] == "W64-AQA-ROLE-STRICT-VISUAL")
    assert strict["readiness"] == "HELD_PREREQUISITES_INCOMPLETE"
    assert any("PROJECT_LICENSE_ACCEPTANCE_MISSING" in value for value in strict["blockers"])
    controller = next(item for item in campaigns if item["role_id"] == "W64-AQA-ROLE-CONTROLLER")
    assert controller["readiness"] == "HELD_PREREQUISITES_INCOMPLETE"
    assert any("EXACT_ARTIFACT_NOT_INSTALLED" in value for value in controller["blockers"])
    inventory = json.loads((ROOT / module.INVENTORY_PATH).read_text(encoding="utf-8"))
    local = next(item for item in inventory["packages"] if item["package_id"] == "W64-AQA-PKG-QWEN25VL32")
    local["identity"]["license_state"] = "PROJECT_LICENSE_ACCEPTED"
    evidence, blockers = module.package_evidence(local)
    assert evidence["exact_identity_installed_and_license_accepted"] is False
    assert any("EXACT_UPSTREAM_REVISION_OR_IDENTITY_NOT_VERIFIED" in value for value in blockers)


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
    for relative in (module.MATRIX_PATH, module.ROLE_REGISTRY_PATH, module.INVENTORY_PATH, module.POLICY_PATH, module.SCHEMA_PATH):
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


def test_checked_in_queue_matches_compiler() -> None:
    module = load_module()
    checked_in = ROOT / module.DEFAULT_OUTPUT
    module.validate_queue(ROOT, json.loads(checked_in.read_text(encoding="utf-8")))
