from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
PRODUCER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_image_shadow_evidence.py"


def load_producer():
    spec = importlib.util.spec_from_file_location("w64_aqa_image_shadow_producer", PRODUCER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    artifact = tmp_path / "artifact.png"
    pixels = np.random.default_rng(7).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    Image.fromarray(pixels, "RGB").save(artifact)
    artifact_sha = sha256_file(artifact)
    relative = "fixtures/artifact.png"
    lineage = {"pulled_artifacts": [{"local_path": relative, "sha256": artifact_sha}]}
    visual = {"generated_image": {"sha256": artifact_sha}}
    global_review = {
        "artifact": {"sha256": artifact_sha},
        "overall_decision": "reject",
        "reject_on_any_global_defect": {
            "global_defects": [
                {"code": "contact_placement_not_exact_target", "severity": "blocking"},
                {"code": "contact_shadow_not_clear", "severity": "blocking"},
            ]
        },
    }
    hold = {
        "inference_executed": False,
        "lease_acquired": False,
        "blocker_codes": ["ACTIVE_FOREIGN_GPU_WORKLOAD_PRESENT"],
        "resource_snapshot": {
            "installed_models": [{"name": "qwen2.5vl:32b", "digest": "a" * 64}]
        },
    }
    paths = []
    for name, value in (
        ("lineage.json", lineage), ("visual.json", visual),
        ("global.json", global_review), ("hold.json", hold),
    ):
        path = tmp_path / name
        path.write_text(json.dumps(value), encoding="utf-8")
        paths.append(path)
    return artifact, *paths


def build(module, artifact: Path, lineage: Path, visual: Path, global_review: Path, hold: Path) -> dict:
    return module.build_evidence(
        artifact_path=artifact,
        lineage_manifest_path=lineage,
        visual_qa_path=visual,
        global_review_path=global_review,
        strict_hold_path=hold,
        generated_at="2026-07-21T22:40:00Z",
        artifact_relative_path="fixtures/artifact.png",
        lineage_manifest_relative_path="fixtures/lineage.json",
        visual_qa_relative_path="fixtures/visual.json",
        global_review_relative_path="fixtures/global.json",
    )


def test_deterministic_pass_cannot_override_visual_rejection_or_runtime_hold(tmp_path: Path) -> None:
    module = load_producer()
    paths = write_fixture(tmp_path)
    first = build(module, *paths)
    second = build(module, *paths)
    assert first == second
    assert first["measurement"]["disposition"] == "PASS_DETERMINISTIC_GATES"
    assert first["codex_visual_review"]["status"] == "REJECT_KNOWN_BLOCKING_DEFECTS"
    assert first["strict_model_gate"]["runtime_executed"] is False
    assert first["product_promotion_eligible"] is False
    assert first["overall_disposition"] == "PASS_DETERMINISTIC_IMAGE_GATES_REJECT_VISUAL_DEFECTS_STRICT_RUNTIME_HELD"


def test_tampered_artifact_and_erased_defects_fail_closed(tmp_path: Path) -> None:
    module = load_producer()
    artifact, lineage, visual, global_review, hold = write_fixture(tmp_path)
    artifact.write_bytes(artifact.read_bytes() + b"tamper")
    with pytest.raises(module.EvidenceError, match="lineage manifest"):
        build(module, artifact, lineage, visual, global_review, hold)

    artifact, lineage, visual, global_review, hold = write_fixture(tmp_path)
    review_doc = json.loads(global_review.read_text(encoding="utf-8"))
    review_doc["reject_on_any_global_defect"]["global_defects"] = []
    global_review.write_text(json.dumps(review_doc), encoding="utf-8")
    with pytest.raises(module.EvidenceError, match="blocking visual defects"):
        build(module, artifact, lineage, visual, global_review, hold)


def test_false_strict_runtime_claim_fails_closed(tmp_path: Path) -> None:
    module = load_producer()
    artifact, lineage, visual, global_review, hold = write_fixture(tmp_path)
    hold_doc = json.loads(hold.read_text(encoding="utf-8"))
    hold_doc["inference_executed"] = True
    hold.write_text(json.dumps(hold_doc), encoding="utf-8")
    with pytest.raises(module.EvidenceError, match="runtime execution"):
        build(module, artifact, lineage, visual, global_review, hold)
