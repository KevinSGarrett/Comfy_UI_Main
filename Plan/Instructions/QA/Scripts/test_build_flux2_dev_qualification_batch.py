from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_flux2_dev_qualification_batch.py"
SPEC = importlib.util.spec_from_file_location("flux2_qualification", SCRIPT); assert SPEC and SPEC.loader
RUNTIME = importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name] = RUNTIME; SPEC.loader.exec_module(RUNTIME)


@pytest.fixture()
def batch_dir():
    path = ROOT / "runtime_artifacts" / "regression" / f"flux2_qualification_{uuid.uuid4().hex}"
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def built(batch_dir): return RUNTIME.build(ROOT, batch_dir)


def test_builds_exact_five_local_only_units(batch_dir):
    index = built(batch_dir); assert index["unit_count"] == 5; assert index["result"] == "pass_local_only"; assert index["execution_allowed"] is False


def test_excludes_completed_proof_seeds_and_covers_distinct_seeds(batch_dir):
    index = built(batch_dir); manifests = [json.loads((ROOT / unit["manifest_path"]).read_text()) for unit in index["units"]]
    seeds = {item["qualification_dimensions"]["seed"] for item in manifests}; assert len(seeds) == 5; assert not seeds & RUNTIME.COMPLETED_SEEDS


def test_subject_resolution_edit_and_seed_robustness_coverage(batch_dir):
    coverage = built(batch_dir)["coverage"]; assert set(coverage["subject_scopes"]) == {"adult_woman", "adult_man", "two_adults", "reference_edit"}; assert len(coverage["resolutions"]) == 4; assert coverage["edit_intents"] == ["environment_material"]; assert coverage["repeated_prompt_distinct_seed"] is True


def test_model_loader_bindings_are_unchanged(batch_dir):
    index = built(batch_dir)
    for unit in index["units"]:
        request = json.loads((batch_dir / unit["case_id"] / "prompt_request.json").read_text())["prompt"]
        assert request["1"]["inputs"]["unet_name"] == "flux2_dev_fp8mixed.safetensors"
        assert request["2"]["inputs"]["clip_name"] == "mistral_3_small_flux2_bf16.safetensors"
        assert request["3"]["inputs"]["vae_name"] == "flux2-vae.safetensors"


def test_manifests_bind_prompt_and_source_workflow_hashes(batch_dir):
    index = built(batch_dir)
    for unit in index["units"]:
        manifest = json.loads((batch_dir / unit["case_id"] / "RUN_PACKAGE_MANIFEST.json").read_text())
        assert manifest["prompt_request"]["sha256"] == unit["prompt_sha256"] == manifest["generated_files"][0]["sha256"]
        assert manifest["source_workflow"]["sha256"] == index["source_workflows"][manifest["source_workflow"]["path"]]
        assert not manifest["aws_contacted"] and not manifest["ec2_started"] and not manifest["generation_executed"] and not manifest["requires_gold_masks"]
