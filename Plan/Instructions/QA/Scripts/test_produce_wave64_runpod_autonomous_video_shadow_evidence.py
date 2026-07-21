from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[4]
PRODUCER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_video_shadow_evidence.py"


def load_producer():
    spec = importlib.util.spec_from_file_location("w64_aqa_video_shadow_producer", PRODUCER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_video(path: Path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 24, (64, 48))
    assert writer.isOpened()
    try:
        for index in range(49):
            y, x = np.indices((48, 64))
            frame = np.stack(
                (
                    (x * 4 + index * 3) % 256,
                    (y * 5 + index * 2) % 256,
                    ((x + y) * 3 + index * 4) % 256,
                ),
                axis=-1,
            ).astype(np.uint8)
            writer.write(frame)
    finally:
        writer.release()


def write_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    video = tmp_path / "video.mp4"
    write_video(video)
    video_sha = sha256_file(video)
    manifest = {
        "outputs": {"strict_source_video": {"sha256": video_sha, "bytes": video.stat().st_size}},
        "source_bindings": {"source_video": {"sha256": video_sha}},
    }
    technical = {"artifact": {"sha256": video_sha}, "technical_pass": True}
    av_shadow = {
        "source": {"source_video_sha256": video_sha},
        "product_promotion_eligible": False,
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
        ("manifest.json", manifest), ("technical.json", technical),
        ("av.json", av_shadow), ("hold.json", hold),
    ):
        path = tmp_path / name
        path.write_text(json.dumps(value), encoding="utf-8")
        paths.append(path)
    return video, *paths


def build(module, video: Path, manifest: Path, technical: Path, av: Path, hold: Path) -> dict:
    return module.build_evidence(
        video_path=video,
        delivery_manifest_path=manifest,
        original_technical_qa_path=technical,
        av_shadow_evidence_path=av,
        strict_hold_path=hold,
        generated_at="2026-07-21T22:50:00Z",
        video_relative_path="fixtures/video.mp4",
        delivery_manifest_relative_path="fixtures/manifest.json",
        original_technical_qa_relative_path="fixtures/technical.json",
        av_shadow_evidence_relative_path="fixtures/av.json",
        observations=["Five sampled frames remain structurally consistent."],
    )


def test_deterministic_video_pass_retains_diagnostic_only_boundary(tmp_path: Path) -> None:
    module = load_producer()
    paths = write_fixture(tmp_path)
    first = build(module, *paths)
    second = build(module, *paths)
    assert first == second
    assert first["measurement"]["disposition"] == "PASS_DETERMINISTIC_GATES"
    assert len(first["measurement"]["sample_manifest"]) >= 16
    assert len(first["contact_sheet_review"]["contact_sheet_sha256"]) == 64
    assert first["contact_sheet_review"]["whole_clip_review_claimed"] is False
    assert first["strict_model_gate"]["runtime_executed"] is False
    assert first["product_promotion_eligible"] is False
    assert first["overall_disposition"] == "PASS_DETERMINISTIC_VIDEO_GATES_DIAGNOSTIC_CONTACT_SHEET_ONLY_STRICT_RUNTIME_HELD"


def test_tampered_video_and_promoted_av_lineage_fail_closed(tmp_path: Path) -> None:
    module = load_producer()
    video, manifest, technical, av, hold = write_fixture(tmp_path)
    video.write_bytes(video.read_bytes() + b"tamper")
    with pytest.raises(module.EvidenceError, match="delivery manifest"):
        build(module, video, manifest, technical, av, hold)

    video, manifest, technical, av, hold = write_fixture(tmp_path)
    av_doc = json.loads(av.read_text(encoding="utf-8"))
    av_doc["product_promotion_eligible"] = True
    av.write_text(json.dumps(av_doc), encoding="utf-8")
    with pytest.raises(module.EvidenceError, match="evidence-only"):
        build(module, video, manifest, technical, av, hold)


def test_false_strict_runtime_claim_fails_closed(tmp_path: Path) -> None:
    module = load_producer()
    video, manifest, technical, av, hold = write_fixture(tmp_path)
    hold_doc = json.loads(hold.read_text(encoding="utf-8"))
    hold_doc["inference_executed"] = True
    hold.write_text(json.dumps(hold_doc), encoding="utf-8")
    with pytest.raises(module.EvidenceError, match="runtime execution"):
        build(module, video, manifest, technical, av, hold)
