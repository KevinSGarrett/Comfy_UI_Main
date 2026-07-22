from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "Plan/10_REGISTRIES/wave64_qwen3_tts_1_7b_base_promoted_storage_package.json"
CATALOG = ROOT / "Plan/10_REGISTRIES/wave64_hyperreal_audio_model_asset_acquisition_catalog.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_exact_file_set_and_total_are_consistent() -> None:
    package = load(PACKAGE)
    paths = [item["path"] for item in package["files"]]
    assert paths == sorted(paths)
    assert len(paths) == len(set(paths)) == package["file_count"] == 11
    assert sum(item["bytes"] for item in package["files"]) == package["total_bytes"]
    assert all(len(item["sha256"]) == 64 for item in package["files"])


def test_provider_revision_and_key_weights_match_canonical_catalog() -> None:
    package = load(PACKAGE)
    catalog = load(CATALOG)
    asset = next(item for item in catalog["official_asset_groups"] if item["asset_id"] == package["asset_id"])
    assert package["repository"] == asset["repo_id"]
    assert package["revision"] == asset["revision"]
    assert package["license"] == asset["license"]
    package_files = {item["path"]: item for item in package["files"]}
    for key_file in asset["key_files"]:
        assert package_files[key_file["filename"]]["bytes"] == key_file["bytes"]
        assert package_files[key_file["filename"]]["sha256"] == key_file["sha256"]


def test_storage_does_not_claim_runtime_or_product_authority() -> None:
    package = load(PACKAGE)
    assert package["verification"]["model_loaded"] is False
    assert package["verification"]["gpu_or_lease_polled"] is False
    assert package["authority"]["storage_identity"] is True
    for field in ("dependency_environment", "model_load", "voice_cloning_quality", "speaker_identity", "operational_activation", "product_promotion"):
        assert package["authority"][field] is False
