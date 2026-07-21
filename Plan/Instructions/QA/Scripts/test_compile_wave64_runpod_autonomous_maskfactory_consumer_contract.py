from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
COMPILER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_maskfactory_consumer_contract.py"


def load_compiler():
    spec = importlib.util.spec_from_file_location("w64_aqa_maskfactory_consumer", COMPILER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def draft() -> dict:
    roles = [
        ("source", "source_media", "runs/job/source.png", "a"),
        ("candidate", "candidate_mask", "runs/job/candidate.png", "b"),
        ("golden", "accepted_golden_reference", "accepted/golden.png", "c"),
        ("overlay", "target_overlay", "runs/job/overlay.png", "d"),
    ]
    return {
        "schema_version": "wave64.aqa.maskfactory_consumer_contract.v1",
        "producer": {
            "producer_id": "MaskFactory",
            "repository_class": "external_read_only",
            "root_binding": "maskfactory_authoritative",
            "pipeline_fingerprint": "e" * 64,
            "runtime_fingerprint": "f" * 64,
            "qualification_state": "UNQUALIFIED",
        },
        "target_binding": {
            "subject_id": "character-001",
            "instance_id": "character-001/body/primary",
            "target_label": "body",
            "coordinate_space": "source_pixels",
            "source_artifact_id": "source",
        },
        "artifacts": [
            {
                "artifact_id": artifact_id,
                "role": role,
                "relative_path": relative_path,
                "sha256": digest * 64,
                "byte_size": 1024,
                "width": 1024,
                "height": 1024,
            }
            for artifact_id, role, relative_path, digest in roles
        ],
        "authority": {
            "external_writes_allowed": False,
            "candidate_only": True,
            "golden_authority": "integration_accepted_hash_only",
            "product_promotion_allowed": False,
        },
        "quality_contract": {
            "golden_reference_artifact_id": "golden",
            "required_gates": [
                "geometry", "golden_hash", "target_binding", "completeness",
                "leakage", "boundary", "alpha", "topology", "overlay",
            ],
        },
    }


def test_read_only_candidate_contract_is_deterministic_and_grants_no_authority() -> None:
    module = load_compiler()
    first = module.compile_contract(draft())
    second = module.compile_contract(draft())
    assert first == second
    assert first["admission_disposition"] == "READY_FOR_DETERMINISTIC_MASK_QA"
    assert first["runtime_authority_granted"] is False
    assert first["promotion_eligible"] is False
    assert first["producer"]["qualification_state"] == "UNQUALIFIED"


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda value: value["authority"].update(external_writes_allowed=True), "writes are forbidden"),
        (lambda value: value["authority"].update(product_promotion_allowed=True), "cannot grant promotion"),
        (lambda value: value["artifacts"][1].update(relative_path="../escape.png"), "safe relative path"),
        (lambda value: value["artifacts"][1].update(width=512), "geometry must match"),
        (lambda value: value["target_binding"].update(source_artifact_id="candidate"), "source artifact"),
        (lambda value: value["quality_contract"].update(golden_reference_artifact_id="candidate"), "accepted golden hash"),
        (lambda value: value["quality_contract"]["required_gates"].remove("overlay"), "all deterministic"),
        (lambda value: value["artifacts"].pop(), "exact source candidate golden and overlay"),
    ],
)
def test_unsafe_or_incomplete_external_contract_fails_closed(mutate, match: str) -> None:
    module = load_compiler()
    value = draft()
    mutate(value)
    with pytest.raises(module.ConsumerContractError, match=match):
        module.compile_contract(value)
