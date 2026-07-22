from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "Plan/10_REGISTRIES/wave64_qwen3_tts_1_7b_voicedesign_promoted_storage_package.json"
CATALOG = ROOT / "Plan/10_REGISTRIES/wave64_hyperreal_audio_model_asset_acquisition_catalog.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_exact_file_set_total_and_catalog_binding() -> None:
    package = load(PACKAGE)
    catalog = load(CATALOG)
    paths = [item["path"] for item in package["files"]]
    assert paths == sorted(paths)
    assert len(paths) == len(set(paths)) == package["file_count"] == 11
    assert sum(item["bytes"] for item in package["files"]) == package["total_bytes"]
    asset = next(item for item in catalog["official_asset_groups"] if item["asset_id"] == package["asset_id"])
    assert (package["repository"], package["revision"], package["license"]) == (asset["repo_id"], asset["revision"], asset["license"])
    files = {item["path"]: item for item in package["files"]}
    for key_file in asset["key_files"]:
        assert files[key_file["filename"]]["bytes"] == key_file["bytes"]
        assert files[key_file["filename"]]["sha256"] == key_file["sha256"]


def test_storage_authority_remains_non_runtime() -> None:
    package = load(PACKAGE)
    assert package["authority"]["storage_identity"] is True
    assert package["verification"]["model_loaded"] is False
    for field in ("dependency_environment", "model_load", "voice_design_quality", "speaker_identity", "operational_activation", "product_promotion"):
        assert package["authority"][field] is False
