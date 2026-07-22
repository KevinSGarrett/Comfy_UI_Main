from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_campaign_bulk_manifest.py"
SPEC = importlib.util.spec_from_file_location("manifest", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
H = "a" * 64


def draft() -> dict:
    ref = {"relative_path": "inputs/a.json", "sha256": H}
    return {"schema_version": "wave64.aqa.campaign_bulk_manifest.v1", "profile": "MULTIMODAL_MEDIA_CAMPAIGN", "prompts": [ref], "negative_prompts": [], "seeds": [42], "source_assets": [ref], "workflows": [ref], "models": [{"checkpoint_sha256": H, "role_id": "ROLE", "family_id": "FAMILY", "residency_group": "image"}], "environment_sha256": H, "outputs": [{"artifact_id": "image-1", "modality": "IMAGE", "candidate_count": 2, "quality_tier": "CRITICAL"}], "generation_parameters": {"dimensions": "1024x1024", "frame_rate": 0, "duration_seconds": 0, "audio_sample_rate": 0, "audio_channels": 0}, "sampling": {"seed": 7, "strata": ["critical"], "expand_to_full_review_on_threshold": True}}


def test_compile_verify_is_deterministic() -> None:
    first = MODULE.compile_manifest(draft())
    second = MODULE.compile_manifest(draft())
    assert first == second
    MODULE.verify_manifest(first)


def test_rejects_path_escape_and_tamper() -> None:
    value = draft()
    value["prompts"][0]["relative_path"] = "../escape"
    with pytest.raises(MODULE.ManifestError):
        MODULE.compile_manifest(value)
    result = MODULE.compile_manifest(draft())
    result["seeds"] = [43]
    with pytest.raises(MODULE.ManifestError, match="manifest_id"):
        MODULE.verify_manifest(result)
