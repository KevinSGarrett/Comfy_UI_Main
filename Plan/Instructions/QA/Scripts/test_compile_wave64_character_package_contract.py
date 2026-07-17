from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_character_package_contract.py"
SPEC = importlib.util.spec_from_file_location("wave64_character_package_compiler", SCRIPT)
assert SPEC and SPEC.loader
COMPILER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = COMPILER
SPEC.loader.exec_module(COMPILER)


def contract():
    return COMPILER.load_json(ROOT / COMPILER.DEFAULT_CONTRACT)


def schema():
    return COMPILER.load_json(ROOT / COMPILER.DEFAULT_SCHEMA)


def compile_candidate(candidate):
    return COMPILER.compile_contract(ROOT, candidate, schema())


def test_live_fixture_compiles_all_five_rows_without_runtime_promotion():
    result = compile_candidate(contract())
    assert result["classification"] == "WAVE64_CHARACTER_PACKAGE_COMPILATION_SLICE_PASS"
    assert result["rows_covered"] == [154, 155, 156, 157, 158]
    assert result["payload_hash_count"] == 11
    assert result["character_state_count"] == 8
    assert result["runtime_completion_claimed"] is False
    assert result["production_promotion_allowed"] is False


def test_character_payload_cannot_embed_fixed_windows_path():
    candidate = contract()
    candidate["character_states"][0]["payload"] = {"source": "C:\\characters\\c01.png"}
    candidate["character_states"][0]["payload_sha256"] = COMPILER.sha256_value(
        candidate["character_states"][0]["payload"]
    )
    with pytest.raises(COMPILER.CompilationError, match="fixed_character_path_forbidden"):
        compile_candidate(candidate)


def test_character_payload_cannot_embed_fixed_comfy_node_id():
    candidate = contract()
    candidate["character_states"][0]["payload"] = {"comfy_node_id": "42"}
    candidate["character_states"][0]["payload_sha256"] = COMPILER.sha256_value(
        candidate["character_states"][0]["payload"]
    )
    with pytest.raises(COMPILER.CompilationError, match="fixed_character_path_or_node_key_forbidden"):
        compile_candidate(candidate)


def test_controlled_payload_hash_mismatch_fails_closed():
    candidate = contract()
    candidate["character_states"][0]["payload_sha256"] = "0" * 64
    with pytest.raises(COMPILER.CompilationError, match="payload_hash_mismatch"):
        compile_candidate(candidate)


def test_character_state_type_set_must_be_exact_and_complete():
    candidate = contract()
    candidate["character_states"][-1]["state_type"] = "morphology"
    with pytest.raises(COMPILER.CompilationError, match="character_state_type_set_incomplete_or_duplicate"):
        compile_candidate(candidate)


def test_character_state_owner_cannot_cross_identity():
    candidate = contract()
    candidate["character_states"][0]["owner_character_id"] = "char_other"
    with pytest.raises(COMPILER.CompilationError, match="character_state_owner_mismatch"):
        compile_candidate(candidate)


def test_character_state_cannot_mutate_identity_core():
    candidate = contract()
    candidate["character_states"][0]["payload"] = {"identity_core": {"replace": True}}
    candidate["character_states"][0]["payload_sha256"] = COMPILER.sha256_value(
        candidate["character_states"][0]["payload"]
    )
    with pytest.raises(COMPILER.CompilationError, match="character_state_attempts_identity_mutation"):
        compile_candidate(candidate)


def test_character_package_cannot_consume_rejected_reference_as_truth():
    candidate = contract()
    candidate["character_package"]["identity_core"]["approved_reference_artifact_ids"].append(
        "ref_c01_blurred_rejected"
    )
    with pytest.raises(COMPILER.CompilationError, match="character_reference_not_accepted"):
        compile_candidate(candidate)


def test_reference_conflict_must_name_known_hash_bound_assets():
    candidate = contract()
    candidate["reference_intake"]["conflicts"][0]["artifact_ids"][1] = "ref_missing"
    with pytest.raises(COMPILER.CompilationError, match="reference_conflict_unknown_artifact"):
        compile_candidate(candidate)


def test_open_reference_conflict_blocks_compilation():
    candidate = contract()
    candidate["reference_intake"]["conflicts"][0]["resolution_status"] = "open_blocking"
    candidate["reference_intake"]["conflicts"][0]["resolution_evidence_id"] = None
    with pytest.raises(COMPILER.CompilationError, match="reference_conflict_open_blocking"):
        compile_candidate(candidate)


def test_voice_binding_requires_exact_reference_authority_binding():
    candidate = contract()
    candidate["reference_intake"]["voice_reference_bindings"] = []
    with pytest.raises(COMPILER.CompilationError, match="voice_binding_missing_reference_authority"):
        compile_candidate(candidate)


def test_scene_shot_take_scope_cannot_drift():
    candidate = contract()
    candidate["scope_binding"]["take_id"] = "take002"
    with pytest.raises(COMPILER.CompilationError, match="scene_shot_take_scope_mismatch"):
        compile_candidate(candidate)


def test_pass_target_must_resolve_to_shot_owner_instance():
    candidate = contract()
    candidate["scope_binding"]["target_owner_instance_ids"] = ["charinst_missing"]
    with pytest.raises(COMPILER.CompilationError, match="pass_target_owner_unknown"):
        compile_candidate(candidate)


def test_scene_and_shot_character_instances_must_match():
    candidate = contract()
    candidate["shot_pose_package"]["instances"][0]["character_instance_id"] = "charinst_other"
    with pytest.raises(COMPILER.CompilationError, match="scene_and_shot_character_instances_mismatch"):
        compile_candidate(candidate)


def test_artifact_parent_must_be_known_and_topologically_prior():
    candidate = contract()
    candidate["artifact_manifests"][0]["parent_artifact_ids"] = ["artifact_future"]
    with pytest.raises(COMPILER.CompilationError, match="artifact_parent_not_prior_or_unknown"):
        compile_candidate(candidate)


def test_artifact_bytes_must_use_exact_content_addressed_uri():
    candidate = contract()
    candidate["artifact_manifests"][0]["files"][0]["path_or_uri"] = "outputs/result.json"
    with pytest.raises(COMPILER.CompilationError, match="artifact_file_not_content_addressed"):
        compile_candidate(candidate)


def test_synthetic_artifact_cannot_claim_acceptance_or_promotion():
    candidate = contract()
    candidate["artifact_manifests"][0]["promotion_state"] = "candidate"
    with pytest.raises(COMPILER.CompilationError, match="synthetic_artifact_false_promotion"):
        compile_candidate(candidate)


def test_embedded_schema_rejects_unhashed_engine_binding():
    candidate = contract()
    candidate["character_package"]["engine_bindings"][0]["artifact_hashes"] = ["not-a-sha"]
    with pytest.raises(COMPILER.CompilationError, match="schema_validation_failed:character_package"):
        compile_candidate(candidate)


def test_cli_evidence_outputs_are_exact_mirrors(tmp_path):
    result = compile_candidate(contract())
    evidence = COMPILER.build_evidence(ROOT, result, COMPILER.DEFAULT_CONTRACT, COMPILER.DEFAULT_SCHEMA)
    qa_path = tmp_path / "qa.json"
    tracker_path = tmp_path / "tracker.json"
    COMPILER.write_json(qa_path, evidence)
    COMPILER.write_json(tracker_path, evidence)
    assert qa_path.read_bytes() == tracker_path.read_bytes()
    payload = json.loads(qa_path.read_text(encoding="utf-8"))
    assert payload["boundaries"]["synthetic_contract_only"] is True
    assert payload["boundaries"]["promotion_authority_granted"] is False
    assert payload["authority"]["contract_sha256"]
