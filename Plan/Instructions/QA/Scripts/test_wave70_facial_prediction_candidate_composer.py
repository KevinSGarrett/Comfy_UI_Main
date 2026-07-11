from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "Plan/07_IMPLEMENTATION/scripts"
sys.path.insert(0, str(SCRIPTS))
COMPOSER_PATH = SCRIPTS / "compose_wave70_facial_prediction_candidate.py"
SPEC = importlib.util.spec_from_file_location("facial_candidate_composer", COMPOSER_PATH)
assert SPEC and SPEC.loader
composer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(composer)


def save_mask(path: Path, value: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("L", (4, 4), value).save(path)


def fixture_manifest(project: Path) -> Path:
    source = project / "originals/0.jpg"
    source.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), (20, 30, 40)).save(source)
    predictions = project / "predictions/0"
    for class_name in composer.CLASS_ORDER:
        save_mask(predictions / f"{class_name}.png")
    save_mask(predictions / "u_lip.png", 255)
    manifest = {
        "schema_version": "1.0",
        "created_at": "2026-07-10T00:00:00Z",
        "route_id": "fixture.face.route",
        "route_model_identity": {"model_id": "fixture", "model_sha256": "1" * 64},
        "route_configuration_sha256": "2" * 64,
        "dataset_id": "celebamask_hq_shard_0",
        "run_id": "fixture-run",
        "producer_contract": {
            "originals_only": True,
            "gold_paths_exposed_to_route": False,
            "prediction_generated_before_evaluation": True,
            "route_input_image_paths": [str(source.relative_to(project))],
        },
        "samples": [
            {
                "sample_id": "0",
                "source_path": str(source.relative_to(project)),
                "prediction_path": str(predictions.relative_to(project)),
                "prediction_sha256": composer.sha256_directory(predictions),
                "classes": list(composer.CLASS_ORDER),
            }
        ],
    }
    path = project / "source_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_composer_reuses_hash_verified_predictions_and_changes_only_target(tmp_path: Path) -> None:
    project = tmp_path / "project"
    source_manifest = fixture_manifest(project)
    source = json.loads(source_manifest.read_text(encoding="utf-8"))
    base_dir = project / source["samples"][0]["prediction_path"]
    base_skin_hash = composer.sha256_file(base_dir / "skin.png")
    out_manifest = project / "candidate/manifest.json"
    result = composer.compose_manifest(
        project, source_manifest, project / "candidate/runtime", out_manifest, "u_lip_dilate_exclusive_v1"
    )
    sample = result["samples"][0]
    output_dir = project / sample["prediction_path"]
    assert result["candidate_target_classes"] == ["u_lip"]
    assert result["route_execution"]["model_route_executed"] is False
    assert composer.sha256_file(output_dir / "skin.png") == base_skin_hash
    assert sample["composition"]["composition_rule_id"] == "u_lip_dilate_exclusive_v1"


def test_composer_rejects_source_prediction_hash_drift(tmp_path: Path) -> None:
    project = tmp_path / "project"
    source_manifest = fixture_manifest(project)
    source = json.loads(source_manifest.read_text(encoding="utf-8"))
    save_mask(project / source["samples"][0]["prediction_path"] / "skin.png", 255)
    with pytest.raises(ValueError, match="source_prediction_hash_mismatch:0"):
        composer.compose_manifest(
            project,
            source_manifest,
            project / "candidate/runtime",
            project / "candidate/manifest.json",
            "u_lip_dilate_exclusive_v1",
        )


def test_composer_supports_vertical_upper_lip_candidate(tmp_path: Path) -> None:
    project = tmp_path / "project"
    source_manifest = fixture_manifest(project)
    result = composer.compose_manifest(
        project,
        source_manifest,
        project / "candidate_vertical/runtime",
        project / "candidate_vertical/manifest.json",
        "u_lip_dilate_vertical_exclusive_v2",
    )
    assert result["candidate_target_classes"] == ["u_lip"]
    assert result["samples"][0]["composition"]["composition_rule_id"] == "u_lip_dilate_vertical_exclusive_v2"


def test_composer_rejects_nonempty_candidate_destination(tmp_path: Path) -> None:
    project = tmp_path / "project"
    source_manifest = fixture_manifest(project)
    runtime = project / "candidate/runtime"
    stale = runtime / "normalized_predictions/0/stale.txt"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("stale", encoding="utf-8")
    with pytest.raises(ValueError, match="candidate_output_directory_not_empty:0"):
        composer.compose_manifest(
            project,
            source_manifest,
            runtime,
            project / "candidate/manifest.json",
            "u_lip_dilate_exclusive_v1",
        )
