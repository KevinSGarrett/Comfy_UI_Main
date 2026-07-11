from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
EVALUATOR = ROOT / "Plan/07_IMPLEMENTATION/scripts/benchmark_wave70_facial_gold_evaluator.py"
EVALUATOR_SPEC = importlib.util.spec_from_file_location("facial_evaluator", EVALUATOR)
assert EVALUATOR_SPEC and EVALUATOR_SPEC.loader
evaluator_module = importlib.util.module_from_spec(EVALUATOR_SPEC)
EVALUATOR_SPEC.loader.exec_module(evaluator_module)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_path(path: Path) -> str:
    if path.is_file():
        return sha256_file(path)
    digest = hashlib.sha256()
    for child in sorted(entry for entry in path.rglob("*") if entry.is_file()):
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(child).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def save_mask(path: Path, pixels: list[list[int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("L", (len(pixels[0]), len(pixels)))
    image.putdata([value for row in pixels for value in row])
    image.save(path)


def save_rgb(path: Path, width: int = 4, height: int = 4) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (width, height), color=(32, 64, 96)).save(path)


CELEB_CLASSES = (
    "skin", "l_brow", "r_brow", "l_eye", "r_eye", "eye_g", "l_ear", "r_ear", "ear_r",
    "nose", "mouth", "u_lip", "l_lip", "neck", "neck_l", "cloth", "hair", "hat",
)
REGISTERED_BISENET_NECK_MODEL_SHA256 = "468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567"


def composition_fixture(project: Path) -> tuple[dict, Path, Path]:
    base = project / "base"
    output = project / "output"
    zero = [[0, 0], [0, 0]]
    for class_name in CELEB_CLASSES:
        save_mask(base / f"{class_name}.png", zero)
        save_mask(output / f"{class_name}.png", zero)
    save_mask(base / "nose.png", [[255, 0], [0, 0]])
    save_mask(output / "nose.png", [[255, 0], [0, 0]])
    save_mask(output / "skin.png", [[255, 0], [0, 0]])
    inputs = {
        class_name: sha256_file(base / f"{class_name}.png")
        for class_name in evaluator_module.CELEB_SKIN_UNION_SOURCES
    }
    composition = {
        "enabled": True,
        "composition_rule_id": "celeb_skin_nested_union_v1",
        "target_class": "skin",
        "union_sources": list(evaluator_module.CELEB_SKIN_UNION_SOURCES),
        "base_prediction_path": str(base),
        "base_prediction_sha256": sha256_path(base),
        "composition_input_hashes": inputs,
        "base_skin_sha256_preserved": inputs["skin"],
        "composition_output_sha256": sha256_file(output / "skin.png"),
    }
    return {"composition": composition}, base, output


def u_lip_dilate_exclusive_fixture(project: Path) -> tuple[dict, Path, Path]:
    base = project / "base_u_lip"
    output = project / "output_u_lip"
    zero = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    for class_name in CELEB_CLASSES:
        save_mask(base / f"{class_name}.png", zero)
        save_mask(output / f"{class_name}.png", zero)
    save_mask(base / "u_lip.png", [[0, 0, 0], [0, 255, 0], [0, 0, 0]])
    save_mask(base / "mouth.png", [[0, 0, 0], [0, 0, 255], [0, 0, 0]])
    save_mask(base / "l_lip.png", [[0, 0, 0], [0, 0, 0], [0, 0, 0]])
    save_mask(output / "mouth.png", [[0, 0, 0], [0, 0, 255], [0, 0, 0]])
    save_mask(output / "l_lip.png", [[0, 0, 0], [0, 0, 0], [0, 0, 0]])
    save_mask(output / "u_lip.png", [[255, 255, 255], [255, 255, 0], [255, 255, 255]])
    composition = {
        "enabled": True,
        "composition_rule_id": "u_lip_dilate_exclusive_v1",
        "target_class": "u_lip",
        "base_prediction_path": str(base),
        "base_prediction_sha256": sha256_path(base),
        "composition_source_hashes": {"u_lip": sha256_file(base / "u_lip.png")},
        "composition_exclusion_hashes": {
            "mouth": sha256_file(base / "mouth.png"),
            "l_lip": sha256_file(base / "l_lip.png"),
        },
        "base_u_lip_sha256_preserved": sha256_file(base / "u_lip.png"),
        "fixed_parameters": dict(evaluator_module.U_LIP_DILATE_EXCLUSIVE_PARAMETERS),
        "composition_output_sha256": sha256_file(output / "u_lip.png"),
    }
    return {"composition": composition}, base, output


def test_composition_contract_recomputes_union_and_preserves_non_target(tmp_path: Path) -> None:
    project = tmp_path / "project"
    sample, _, output = composition_fixture(project)
    evaluator_module.validate_celeb_composition(project, sample, output)


def test_composition_contract_rejects_changed_non_target(tmp_path: Path) -> None:
    project = tmp_path / "project"
    sample, _, output = composition_fixture(project)
    save_mask(output / "nose.png", [[0, 0], [0, 0]])
    with pytest.raises(ValueError, match="composition_non_target_class_changed:nose"):
        evaluator_module.validate_celeb_composition(project, sample, output)


def test_composition_contract_rejects_nonreproducible_skin(tmp_path: Path) -> None:
    project = tmp_path / "project"
    sample, _, output = composition_fixture(project)
    save_mask(output / "skin.png", [[255, 255], [0, 0]])
    sample["composition"]["composition_output_sha256"] = sha256_file(output / "skin.png")
    with pytest.raises(ValueError, match="composition_output_not_reproducible"):
        evaluator_module.validate_celeb_composition(project, sample, output)


def test_u_lip_dilate_exclusive_contract_passes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    sample, _, output = u_lip_dilate_exclusive_fixture(project)
    evaluator_module.validate_celeb_composition(project, sample, output)


def test_u_lip_dilate_exclusive_rejects_changed_non_target(tmp_path: Path) -> None:
    project = tmp_path / "project"
    sample, _, output = u_lip_dilate_exclusive_fixture(project)
    save_mask(output / "mouth.png", [[0, 0, 0], [0, 255, 255], [0, 0, 0]])
    with pytest.raises(ValueError, match="composition_non_target_class_changed:mouth"):
        evaluator_module.validate_celeb_composition(project, sample, output)


def test_u_lip_dilate_exclusive_rejects_invalid_fixed_parameters(tmp_path: Path) -> None:
    project = tmp_path / "project"
    sample, _, output = u_lip_dilate_exclusive_fixture(project)
    sample["composition"]["fixed_parameters"]["iterations"] = 2
    with pytest.raises(ValueError, match="composition_fixed_parameters_invalid"):
        evaluator_module.validate_celeb_composition(project, sample, output)


def test_u_lip_dilate_exclusive_rejects_wrong_exclusion_hash(tmp_path: Path) -> None:
    project = tmp_path / "project"
    sample, _, output = u_lip_dilate_exclusive_fixture(project)
    sample["composition"]["composition_exclusion_hashes"]["mouth"] = "f" * 64
    with pytest.raises(ValueError, match="composition_exclusion_hash_mismatch:mouth"):
        evaluator_module.validate_celeb_composition(project, sample, output)


def run_eval(
    project_root: Path, manifest_path: Path, out_path: Path, taxonomy_path: Path | None = None
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(EVALUATOR),
        "--project-root",
        str(project_root),
        "--prediction-manifest",
        str(manifest_path),
        "--out",
        str(out_path),
    ]
    if taxonomy_path is not None:
        cmd.extend(["--taxonomy-binding", str(taxonomy_path)])
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def base_project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    registry_path = project / "Plan/10_REGISTRIES/facial_neck_hair_gold_standard_dataset_registry.json"
    protocol_path = project / "Plan/Instructions/QA/FACIAL_NECK_HAIR_GOLD_STANDARD_BENCHMARK_PROTOCOL.md"
    celeb_images = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img"
    celeb_gold = project / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0"
    lapa_train_images = project / "MaskedWarehouse/LaPa/train/images"
    lapa_train_labels = project / "MaskedWarehouse/LaPa/train/labels"
    lapa_train_landmarks = project / "MaskedWarehouse/LaPa/train/landmarks"
    lapa_val_images = project / "MaskedWarehouse/LaPa/val/images"
    lapa_val_labels = project / "MaskedWarehouse/LaPa/val/labels"
    lapa_val_landmarks = project / "MaskedWarehouse/LaPa/val/landmarks"
    lapa_test_images = project / "MaskedWarehouse/LaPa/test/images"
    lapa_test_labels = project / "MaskedWarehouse/LaPa/test/labels"
    lapa_test_landmarks = project / "MaskedWarehouse/LaPa/test/landmarks"
    protocol_path.parent.mkdir(parents=True, exist_ok=True)
    protocol_path.write_text("benchmark protocol", encoding="utf-8")
    registry = {
        "schema_version": "1.0",
        "registry_id": "facial_neck_hair_gold_standard_dataset_registry",
        "datasets": [
            {
                "dataset_id": "celebamask_hq_shard_0",
                "original_images_root": str(celeb_images),
                "gold_annotations_root": str(celeb_gold),
                "eligible_id_min": 0,
                "eligible_id_max": 1999,
                "class_file_counts": {"skin": 1, "neck": 1, "neck_l": 1},
            },
            {
                "dataset_id": "lapa",
                "splits": {
                    "train": {
                        "images_root": str(lapa_train_images),
                        "labels_root": str(lapa_train_labels),
                        "landmarks_root": str(lapa_train_landmarks),
                    },
                    "val": {
                        "images_root": str(lapa_val_images),
                        "labels_root": str(lapa_val_labels),
                        "landmarks_root": str(lapa_val_landmarks),
                    },
                    "test": {
                        "images_root": str(lapa_test_images),
                        "labels_root": str(lapa_test_labels),
                        "landmarks_root": str(lapa_test_landmarks),
                    },
                },
            },
        ],
    }
    write_json(registry_path, registry)
    return project, registry_path


def celeb_manifest(project: Path, source: Path, prediction_dir: Path, **extra: dict) -> dict:
    source_size = list(Image.open(source).size)
    return {
        "schema_version": "1.0",
        "created_at": "2026-07-10T00:00:00Z",
        "route_id": "route.face.segment",
        "route_model_identity": {"model_id": "fixture-face-parser", "model_sha256": "1" * 64},
        "route_configuration_sha256": "2" * 64,
        "dataset_id": "celebamask_hq_shard_0",
        "run_id": "run-1",
        "producer_contract": {
            "originals_only": True,
            "gold_paths_exposed_to_route": False,
            "prediction_generated_before_evaluation": True,
            "route_input_image_paths": [str(source)],
        },
        "samples": [
            {
                "sample_id": source.stem,
                "source_path": str(source),
                "source_sha256": sha256_file(source),
                "source_size": source_size,
                "prediction_path": str(prediction_dir),
                "prediction_sha256": sha256_path(prediction_dir),
                "classes": ["skin", "neck", "neck_l"],
                "protected_neighbors": {"skin": ["neck"], "neck": ["skin"], "neck_l": ["neck"]},
                "transforms": [{"op": "identity", "from_size": [4, 4], "to_size": [4, 4]}],
            }
        ],
        **extra,
    }


def lapa_manifest(project: Path, source: Path, pred_label: Path, pred_landmarks: Path | None = None, **extra: dict) -> dict:
    sample = {
        "sample_id": source.stem,
        "source_path": str(source),
        "source_sha256": sha256_file(source),
        "source_size": list(Image.open(source).size),
        "prediction_path": str(pred_label),
        "prediction_sha256": sha256_file(pred_label),
        "mode": "semantic_and_landmarks",
        "transforms": [{"op": "identity", "from_size": [4, 4], "to_size": [4, 4]}],
    }
    if pred_landmarks:
        sample["prediction_landmarks_path"] = str(pred_landmarks)
        sample["prediction_landmarks_sha256"] = sha256_file(pred_landmarks)
    return {
        "schema_version": "1.0",
        "created_at": "2026-07-10T00:00:00Z",
        "route_id": "route.face.segment",
        "route_model_identity": {"model_id": "fixture-face-parser", "model_sha256": "1" * 64},
        "route_configuration_sha256": "2" * 64,
        "dataset_id": "lapa",
        "split": "train",
        "run_id": "run-2",
        "producer_contract": {
            "originals_only": True,
            "gold_paths_exposed_to_route": False,
            "prediction_generated_before_evaluation": True,
            "route_input_image_paths": [str(source)],
        },
        "landmark_normalization": {
            "method": "interocular_index_pair",
            "indices": [0, 1],
            "authority_source": "disposable_fixture_only",
        },
        "samples": [sample],
        **extra,
    }


def write_lapa_taxonomy(project: Path) -> Path:
    path = project / "taxonomy_binding.json"
    write_json(
        path,
        {
            "schema_version": "1.0",
            "dataset_id": "lapa",
            "authority_source": "disposable_fixture_only",
            "label_to_class": {str(i): f"class_{i}" for i in range(11)},
            "protected_neighbors": {str(i): [] for i in range(11)},
        },
    )
    return path


def read_evidence(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_celeb_exact_pairing_pass(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/42.jpg"
    save_rgb(source)
    pred_dir = project / "pred/42"
    save_mask(pred_dir / "skin.png", [[255, 0, 0, 0], [255, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(pred_dir / "neck.png", [[0, 0, 0, 0], [0, 0, 0, 0], [255, 255, 0, 0], [255, 255, 0, 0]])
    save_mask(pred_dir / "neck_l.png", [[0, 255, 0, 0], [0, 255, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    gold = project / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0"
    save_mask(gold / "00042_skin.png", [[255, 0, 0, 0], [255, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(gold / "00042_neck.png", [[0, 0, 0, 0], [0, 0, 0, 0], [255, 255, 0, 0], [255, 255, 0, 0]])
    save_mask(gold / "00042_neck_l.png", [[0, 255, 0, 0], [0, 255, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    manifest = celeb_manifest(project, source, pred_dir)
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode == 0
    assert read_evidence(out_path)["status"] == "pass"


def test_absent_class_empty_allowed(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/7.jpg"
    save_rgb(source)
    pred_dir = project / "pred/7"
    save_mask(pred_dir / "skin.png", [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(pred_dir / "neck.png", [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(pred_dir / "neck_l.png", [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    gold = project / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0"
    save_mask(gold / "00007_skin.png", [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(gold / "00007_neck.png", [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    # Intentionally omit neck_l gold file; eligible IDs allow empty class policy.
    manifest = celeb_manifest(project, source, pred_dir)
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode == 0
    assert read_evidence(out_path)["status"] == "pass"


def test_out_of_range_celeb_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/2001.jpg"
    save_rgb(source)
    pred_dir = project / "pred/2001"
    save_mask(pred_dir / "skin.png", [[0, 0, 0, 0]] * 4)
    save_mask(pred_dir / "neck.png", [[0, 0, 0, 0]] * 4)
    save_mask(pred_dir / "neck_l.png", [[0, 0, 0, 0]] * 4)
    manifest = celeb_manifest(project, source, pred_dir)
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode != 0
    events = read_evidence(out_path)["fail_closed_events"]
    assert any(event["code"] == "celeb_id_out_of_range" for event in events)


def test_resize_transform_chain_valid(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/11.jpg"
    save_rgb(source, width=4, height=4)
    pred_dir = project / "pred/11"
    save_mask(pred_dir / "skin.png", [[255, 0], [0, 0]])
    save_mask(pred_dir / "neck.png", [[0, 255], [0, 0]])
    save_mask(pred_dir / "neck_l.png", [[0, 0], [255, 0]])
    gold = project / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0"
    save_mask(gold / "00011_skin.png", [[255, 0, 0, 0], [255, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(gold / "00011_neck.png", [[0, 0, 0, 0], [0, 0, 0, 0], [255, 255, 0, 0], [255, 255, 0, 0]])
    save_mask(gold / "00011_neck_l.png", [[0, 255, 0, 0], [0, 255, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["samples"][0]["transforms"] = [{"op": "resize", "from_size": [4, 4], "to_size": [2, 2]}]
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode == 0


def test_crop_pad_chain_valid(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/15.jpg"
    save_rgb(source, width=4, height=4)
    pred_dir = project / "pred/15"
    save_mask(pred_dir / "skin.png", [[255, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(pred_dir / "neck.png", [[0, 0, 0, 0], [0, 0, 0, 0], [255, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(pred_dir / "neck_l.png", [[0, 255, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    gold = project / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0"
    save_mask(gold / "00015_skin.png", [[255, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(gold / "00015_neck.png", [[0, 0, 0, 0], [0, 0, 0, 0], [255, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(gold / "00015_neck_l.png", [[0, 255, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["samples"][0]["transforms"] = [
        {"op": "pad", "from_size": [2, 2], "to_size": [4, 4], "left": 1, "top": 1, "right": 1, "bottom": 1},
        {"op": "crop", "from_size": [4, 4], "to_size": [4, 4], "x": 0, "y": 0},
    ]
    # Align chain by setting original source to 2x2.
    save_rgb(source, width=2, height=2)
    manifest["samples"][0]["source_sha256"] = sha256_file(source)
    manifest["samples"][0]["source_size"] = [2, 2]
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode == 0


def test_unknown_transform_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/25.jpg"
    save_rgb(source)
    pred_dir = project / "pred/25"
    save_mask(pred_dir / "skin.png", [[0, 0, 0, 0]] * 4)
    save_mask(pred_dir / "neck.png", [[0, 0, 0, 0]] * 4)
    save_mask(pred_dir / "neck_l.png", [[0, 0, 0, 0]] * 4)
    gold = project / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0"
    save_mask(gold / "00025_skin.png", [[0, 0, 0, 0]] * 4)
    save_mask(gold / "00025_neck.png", [[0, 0, 0, 0]] * 4)
    save_mask(gold / "00025_neck_l.png", [[0, 0, 0, 0]] * 4)
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["samples"][0]["transforms"] = [{"op": "warp", "from_size": [4, 4], "to_size": [4, 4]}]
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode != 0
    assert "unknown_transform" in read_evidence(out_path)["fail_closed_events"][-1]["message"]


def test_lapa_taxonomy_missing_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/LaPa/train/images/a.jpg"
    label = project / "MaskedWarehouse/LaPa/train/labels/a.png"
    land = project / "MaskedWarehouse/LaPa/train/landmarks/a.txt"
    save_rgb(source)
    save_mask(label, [[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    land.parent.mkdir(parents=True, exist_ok=True)
    land.write_text("2\n0 0\n1 0\n", encoding="utf-8")
    pred = project / "pred/lapa_a.png"
    save_mask(pred, [[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    pred_land = project / "pred/lapa_a_land.json"
    write_json(pred_land, [[0, 0], [1, 0]])
    manifest = lapa_manifest(project, source, pred, pred_land)
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode != 0
    assert any(evt["code"] == "lapa_taxonomy_missing_or_invalid" for evt in read_evidence(out_path)["fail_closed_events"])


def test_lapa_split_mismatch_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/LaPa/val/images/v1.jpg"
    label = project / "MaskedWarehouse/LaPa/val/labels/v1.png"
    land = project / "MaskedWarehouse/LaPa/val/landmarks/v1.txt"
    save_rgb(source)
    save_mask(label, [[0, 0, 0, 0]] * 4)
    land.parent.mkdir(parents=True, exist_ok=True)
    land.write_text("2\n0 0\n1 0\n", encoding="utf-8")
    pred = project / "pred/v1.png"
    save_mask(pred, [[0, 0, 0, 0]] * 4)
    pred_land = project / "pred/v1_land.json"
    write_json(pred_land, [[0, 0], [1, 0]])
    manifest = lapa_manifest(project, source, pred, pred_land)
    manifest["split"] = "train"
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode != 0
    assert any(evt["code"] == "lapa_split_mismatch" for evt in read_evidence(out_path)["fail_closed_events"])


def test_landmark_nme_zero_normalization_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/LaPa/train/images/lm.jpg"
    label = project / "MaskedWarehouse/LaPa/train/labels/lm.png"
    land = project / "MaskedWarehouse/LaPa/train/landmarks/lm.txt"
    save_rgb(source)
    save_mask(label, [[0, 0, 0, 0]] * 4)
    land.parent.mkdir(parents=True, exist_ok=True)
    land.write_text("2\n1 1\n1 1\n", encoding="utf-8")
    pred = project / "pred/lm.png"
    save_mask(pred, [[0, 0, 0, 0]] * 4)
    pred_land = project / "pred/lm_land.json"
    write_json(pred_land, [[1, 1], [1, 1]])
    manifest = lapa_manifest(project, source, pred, pred_land)
    manifest["samples"][0]["mode"] = "landmarks"
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode != 0
    assert "normalization_distance_must_be_positive" in read_evidence(out_path)["fail_closed_events"][-1]["message"]


def test_landmark_exact_prediction_has_zero_nme(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/LaPa/val/images/exact.jpg"
    label = project / "MaskedWarehouse/LaPa/val/labels/exact.png"
    landmark = project / "MaskedWarehouse/LaPa/val/landmarks/exact.txt"
    save_rgb(source)
    save_mask(label, [[0, 0, 0, 0]] * 4)
    landmark.parent.mkdir(parents=True, exist_ok=True)
    landmark.write_text("3\n0 0\n2 0\n1 2\n", encoding="utf-8")
    prediction = project / "pred/exact.png"
    save_mask(prediction, [[0, 0, 0, 0]] * 4)
    predicted_landmarks = project / "pred/exact_landmarks.json"
    write_json(predicted_landmarks, [[0, 0], [2, 0], [1, 2]])
    manifest = lapa_manifest(project, source, prediction, predicted_landmarks, split="val")
    manifest["split"] = "val"
    manifest["samples"][0]["mode"] = "landmarks"
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode == 0
    landmark_result = read_evidence(out_path)["sample_results"][0]["evaluation"]["landmarks"]
    assert landmark_result["nme"] == 0.0


def test_lapa_semantic_requires_and_accepts_separate_taxonomy(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/LaPa/train/images/semantic.jpg"
    label = project / "MaskedWarehouse/LaPa/train/labels/semantic.png"
    landmark = project / "MaskedWarehouse/LaPa/train/landmarks/semantic.txt"
    save_rgb(source)
    save_mask(label, [[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    landmark.parent.mkdir(parents=True, exist_ok=True)
    landmark.write_text("2\n0 0\n1 0\n", encoding="utf-8")
    prediction = project / "pred/semantic.png"
    save_mask(prediction, [[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    manifest = lapa_manifest(project, source, prediction)
    manifest["samples"][0]["mode"] = "semantic"
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path, write_lapa_taxonomy(project))
    assert result.returncode == 0
    assert read_evidence(out_path)["hashes"]["taxonomy_binding_sha256"]


def test_protected_neighbor_leakage_reported(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/30.jpg"
    save_rgb(source)
    pred_dir = project / "pred/30"
    save_mask(pred_dir / "skin.png", [[255, 255, 0, 0], [255, 255, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(pred_dir / "neck.png", [[0, 0, 0, 0]] * 4)
    save_mask(pred_dir / "neck_l.png", [[0, 0, 0, 0]] * 4)
    gold = project / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0"
    save_mask(gold / "00030_skin.png", [[255, 0, 0, 0], [255, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(gold / "00030_neck.png", [[0, 255, 0, 0], [0, 255, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(gold / "00030_neck_l.png", [[0, 0, 0, 0]] * 4)
    manifest = celeb_manifest(project, source, pred_dir)
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode == 0
    classes = read_evidence(out_path)["sample_results"][0]["evaluation"]["classes"]
    skin = [entry for entry in classes if entry["class_name"] == "skin"][0]
    assert skin["protected_neighbor_leakage"] > 0.0


def test_empty_category_marked(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/31.jpg"
    save_rgb(source)
    pred_dir = project / "pred/31"
    save_mask(pred_dir / "skin.png", [[0, 0, 0, 0]] * 4)
    save_mask(pred_dir / "neck.png", [[0, 0, 0, 0]] * 4)
    save_mask(pred_dir / "neck_l.png", [[0, 0, 0, 0]] * 4)
    gold = project / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0"
    save_mask(gold / "00031_skin.png", [[0, 0, 0, 0]] * 4)
    save_mask(gold / "00031_neck.png", [[0, 0, 0, 0]] * 4)
    manifest = celeb_manifest(project, source, pred_dir)
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode == 0
    classes = read_evidence(out_path)["sample_results"][0]["evaluation"]["classes"]
    assert all(entry["metrics"]["empty_category"] == "gold_empty_pred_empty" for entry in classes)


def test_gold_path_leakage_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/12.jpg"
    save_rgb(source)
    pred_dir = project / "pred/12"
    save_mask(pred_dir / "skin.png", [[0, 0, 0, 0]] * 4)
    save_mask(pred_dir / "neck.png", [[0, 0, 0, 0]] * 4)
    save_mask(pred_dir / "neck_l.png", [[0, 0, 0, 0]] * 4)
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["producer_input_gold_path"] = str(
        project / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0/00012_skin.png"
    )
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode != 0
    evidence = read_evidence(out_path)
    assert evidence["leakage_audit"]["gold_path_exposure_detected"] is True


def test_nonempty_neck_and_neck_l_duplicate_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/51.jpg"
    save_rgb(source)
    pred_dir = project / "pred/51"
    duplicate = [[255, 0, 0, 0], [255, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    save_mask(pred_dir / "skin.png", [[0, 0, 0, 0]] * 4)
    save_mask(pred_dir / "neck.png", duplicate)
    save_mask(pred_dir / "neck_l.png", duplicate)
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, celeb_manifest(project, source, pred_dir))
    result = run_eval(project, manifest_path, out_path)
    assert result.returncode != 0
    assert any(event["code"] == "neck_and_neck_l_pixel_identical" for event in read_evidence(out_path)["fail_closed_events"])


def test_registered_bisenet_neck_candidate_without_new_authority_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/57.jpg"
    save_rgb(source)
    pred_dir = project / "pred/57"
    for name in ("skin", "neck", "neck_l"):
        save_mask(pred_dir / f"{name}.png", [[0, 0, 0, 0]] * 4)
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["route_model_identity"]["model_sha256"] = REGISTERED_BISENET_NECK_MODEL_SHA256
    manifest["candidate_target_classes"] = ["neck"]
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    assert run_eval(project, manifest_path, out_path).returncode != 0
    evidence = read_evidence(out_path)
    assert "neck_candidate_not_distinct_from_registered_route" in evidence["fail_closed_events"][-1]["message"]
    assert evidence["neck_candidate_novelty_audit"]["result"] == "blocked_registered_route_reuse"


def test_registered_bisenet_non_neck_candidate_may_report_unchanged_neck(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/60.jpg"
    save_rgb(source)
    pred_dir = project / "pred/60"
    for name in ("skin", "neck", "neck_l"):
        save_mask(pred_dir / f"{name}.png", [[0, 0, 0, 0]] * 4)
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["route_model_identity"]["model_sha256"] = REGISTERED_BISENET_NECK_MODEL_SHA256
    manifest["candidate_target_classes"] = ["skin"]
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    assert run_eval(project, manifest_path, out_path).returncode == 0
    audit = read_evidence(out_path)["neck_candidate_novelty_audit"]
    assert audit["neck_evaluated"] is True
    assert audit["neck_claimed_as_candidate"] is False
    assert audit["result"] == "not_applicable"


def test_registered_bisenet_neck_candidate_with_fixed_non_gold_authority_passes(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/58.jpg"
    save_rgb(source)
    pred_dir = project / "pred/58"
    for name in ("skin", "neck", "neck_l"):
        save_mask(pred_dir / f"{name}.png", [[0, 0, 0, 0]] * 4)
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["route_model_identity"]["model_sha256"] = REGISTERED_BISENET_NECK_MODEL_SHA256
    manifest["candidate_target_classes"] = ["neck"]
    implementation_path = project / "routes/fixed_neck_reconstruction.py"
    implementation_path.parent.mkdir(parents=True, exist_ok=True)
    implementation_path.write_text("def reconstruct_neck():\n    return 'fixture'\n", encoding="utf-8")
    manifest["neck_candidate_authority"] = {
        "kind": "fixed_non_gold_reconstruction",
        "authority_id": "fixture-neck-reconstruction-v1",
        "implementation_path": str(implementation_path),
        "implementation_sha256": sha256_file(implementation_path),
        "gold_derived": False,
    }
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    assert run_eval(project, manifest_path, out_path).returncode == 0
    evidence = read_evidence(out_path)
    assert evidence["neck_candidate_novelty_audit"]["result"] == "fixed_non_gold_reconstruction"
    assert evidence["neck_candidate_novelty_audit"]["fixed_reconstruction_authority_valid"] is True


def test_registered_bisenet_neck_candidate_with_wrong_implementation_hash_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/59.jpg"
    save_rgb(source)
    pred_dir = project / "pred/59"
    for name in ("skin", "neck", "neck_l"):
        save_mask(pred_dir / f"{name}.png", [[0, 0, 0, 0]] * 4)
    implementation_path = project / "routes/fixed_neck_reconstruction.py"
    implementation_path.parent.mkdir(parents=True, exist_ok=True)
    implementation_path.write_text("def reconstruct_neck():\n    return 'fixture'\n", encoding="utf-8")
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["route_model_identity"]["model_sha256"] = REGISTERED_BISENET_NECK_MODEL_SHA256
    manifest["candidate_target_classes"] = ["neck"]
    manifest["neck_candidate_authority"] = {
        "kind": "fixed_non_gold_reconstruction",
        "authority_id": "fixture-neck-reconstruction-v1",
        "implementation_path": str(implementation_path),
        "implementation_sha256": "3" * 64,
        "gold_derived": False,
    }
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    assert run_eval(project, manifest_path, out_path).returncode != 0
    evidence = read_evidence(out_path)
    assert "neck_candidate_not_distinct_from_registered_route" in evidence["fail_closed_events"][-1]["message"]
    assert evidence["neck_candidate_novelty_audit"]["observed_implementation_sha256"] == sha256_file(implementation_path)


def test_source_hash_mismatch_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/52.jpg"
    save_rgb(source)
    pred_dir = project / "pred/52"
    for name in ("skin", "neck", "neck_l"):
        save_mask(pred_dir / f"{name}.png", [[0, 0, 0, 0]] * 4)
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["samples"][0]["source_sha256"] = "f" * 64
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    assert run_eval(project, manifest_path, out_path).returncode != 0
    assert "source_sha_mismatch" in read_evidence(out_path)["fail_closed_events"][-1]["message"]


def test_prediction_hash_mismatch_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/53.jpg"
    save_rgb(source)
    pred_dir = project / "pred/53"
    for name in ("skin", "neck", "neck_l"):
        save_mask(pred_dir / f"{name}.png", [[0, 0, 0, 0]] * 4)
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["samples"][0]["prediction_sha256"] = "f" * 64
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    assert run_eval(project, manifest_path, out_path).returncode != 0
    assert "prediction_sha_mismatch" in read_evidence(out_path)["fail_closed_events"][-1]["message"]


def test_route_input_source_mismatch_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/54.jpg"
    save_rgb(source)
    pred_dir = project / "pred/54"
    for name in ("skin", "neck", "neck_l"):
        save_mask(pred_dir / f"{name}.png", [[0, 0, 0, 0]] * 4)
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["producer_contract"]["route_input_image_paths"] = [str(project / "different.jpg")]
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    assert run_eval(project, manifest_path, out_path).returncode != 0
    assert "producer_route_inputs_do_not_exactly_match_original_sources" in read_evidence(out_path)["fail_closed_events"][-1]["message"]


def test_horizontal_flip_inversion_passes(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/55.jpg"
    save_rgb(source)
    pred_dir = project / "pred/55"
    save_mask(pred_dir / "skin.png", [[0, 0, 0, 255], [0, 0, 0, 255], [0, 0, 0, 0], [0, 0, 0, 0]])
    save_mask(pred_dir / "neck.png", [[0, 0, 0, 0]] * 4)
    save_mask(pred_dir / "neck_l.png", [[0, 0, 0, 0]] * 4)
    gold = project / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0"
    save_mask(gold / "00055_skin.png", [[255, 0, 0, 0], [255, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["samples"][0]["transforms"] = [{"op": "horizontal_flip", "size": [4, 4]}]
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    assert run_eval(project, manifest_path, out_path).returncode == 0
    skin = read_evidence(out_path)["sample_results"][0]["evaluation"]["classes"][0]
    assert skin["metrics"]["iou"] == 1.0


def test_invalid_celeb_protected_neighbor_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/56.jpg"
    save_rgb(source)
    pred_dir = project / "pred/56"
    for name in ("skin", "neck", "neck_l"):
        save_mask(pred_dir / f"{name}.png", [[0, 0, 0, 0]] * 4)
    manifest = celeb_manifest(project, source, pred_dir)
    manifest["samples"][0]["protected_neighbors"]["skin"] = ["not_a_class"]
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    assert run_eval(project, manifest_path, out_path).returncode != 0
    assert "protected_neighbor_class_invalid" in read_evidence(out_path)["fail_closed_events"][-1]["message"]


def test_invalid_lapa_protected_neighbor_rejected(tmp_path: Path) -> None:
    project, _ = base_project(tmp_path)
    source = project / "MaskedWarehouse/LaPa/train/images/bad_neighbor.jpg"
    label = project / "MaskedWarehouse/LaPa/train/labels/bad_neighbor.png"
    landmark = project / "MaskedWarehouse/LaPa/train/landmarks/bad_neighbor.txt"
    save_rgb(source)
    save_mask(label, [[0, 0, 0, 0]] * 4)
    landmark.parent.mkdir(parents=True, exist_ok=True)
    landmark.write_text("2\n0 0\n1 0\n", encoding="utf-8")
    prediction = project / "pred/bad_neighbor.png"
    save_mask(prediction, [[0, 0, 0, 0]] * 4)
    manifest = lapa_manifest(project, source, prediction)
    manifest["samples"][0]["mode"] = "semantic"
    taxonomy_path = write_lapa_taxonomy(project)
    taxonomy = read_evidence(taxonomy_path)
    taxonomy["protected_neighbors"]["0"] = [99]
    write_json(taxonomy_path, taxonomy)
    manifest_path = project / "manifest.json"
    out_path = project / "out.json"
    write_json(manifest_path, manifest)
    assert run_eval(project, manifest_path, out_path, taxonomy_path).returncode != 0
    assert "protected_neighbor_id_invalid" in read_evidence(out_path)["fail_closed_events"][-1]["message"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run disposable facial gold evaluator regressions.")
    parser.add_argument("--out", help="Optional JSON regression evidence path")
    args = parser.parse_args()
    cases = sorted((name, value) for name, value in globals().items() if name.startswith("test_") and callable(value))
    results = []
    for name, case in cases:
        with tempfile.TemporaryDirectory(prefix="facial_gold_evaluator_") as temp_dir:
            try:
                case(Path(temp_dir))
                results.append({"name": name, "result": "pass", "error": None})
            except Exception:
                results.append({"name": name, "result": "fail", "error": traceback.format_exc()[-4000:]})
    failed = [item for item in results if item["result"] != "pass"]
    record = {
        "schema_version": "1.0",
        "artifact_type": "facial_gold_manifest_evaluator_regression",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": "pass_local_only" if not failed else "fail",
        "test_count": len(results),
        "passing_test_count": len(results) - len(failed),
        "failed_test_count": len(failed),
        "tests": results,
        "local_only": True,
        "model_route_executed": False,
        "gold_dataset_mutated": False,
        "aws_contacted": False,
        "comfyui_contacted": False,
        "promotion_claimed": False,
        "claim_boundary": "Disposable evaluator fixtures only; no production route score or certification.",
    }
    if args.out:
        write_json(Path(args.out), record)
    print(json.dumps(record, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
