from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_stage2_image_calibration_board.py"


def load():
    spec = importlib.util.spec_from_file_location("w64_stage2_image_board", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def fixture(tmp_path: Path) -> tuple[Path, Path]:
    artifacts = tmp_path / "runtime_artifacts"
    items = []
    for number in range(2):
        image = artifacts / "intake" / "incoming" / f"{number}.png"
        image.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 24), color=(number * 80, 30, 120)).save(image)
        items.append(
            {
                "source_root": "intake",
                "path": f"incoming/{number}.png",
                "sha256": sha(image),
                "bytes": image.stat().st_size,
                "width": 32,
                "height": 24,
            }
        )
    panel = artifacts / "panel" / "semantic_review_panel.json"
    write_json(
        panel,
        {
            "schema": "w64.reference_image_semantic_review_panel.v1",
            "contract_sha256": "a" * 64,
            "items": items,
        },
    )
    seal = panel.with_name("semantic_review_panel_seal.json")
    sealed = MODULE.seal(
        {"final_sha256": MODULE.ZERO_HASH, "contract_sha256": "a" * 64},
        field="final_sha256",
    )
    write_json(seal, sealed)
    return panel, seal


def test_builds_hash_bound_nonpromoting_board(tmp_path: Path) -> None:
    panel, panel_seal = fixture(tmp_path)
    root = tmp_path / "board"
    board = MODULE.build_board(
        panel_path=panel,
        panel_seal_path=panel_seal,
        output_root=root,
        source_count=2,
        negative_count=3,
    )
    assert board["state"] == "CALIBRATION_BOARD_DRAFT_UNQUALIFIED"
    assert board["counts"] == {"baseline_reference": 2, "seeded_defect": 3, "total": 5}
    MODULE.verify_seal(board, "board_sha256")
    assert {entry["expected_defects"][0] for entry in board["entries"] if entry["kind"] == "SEEDED_DEFECT"} == set(MODULE.DEFECTS)
    assert all((root / entry["generated"]["relative_path"]).is_file() for entry in board["entries"] if entry["kind"] == "SEEDED_DEFECT")
    MODULE.verify_seal(json.loads((root / "stage2_image_calibration_board_seal.json").read_text(encoding="utf-8")), "final_sha256")


def test_tampered_source_fails_without_output(tmp_path: Path) -> None:
    panel, panel_seal = fixture(tmp_path)
    (tmp_path / "runtime_artifacts" / "intake" / "incoming" / "0.png").write_bytes(b"tampered")
    root = tmp_path / "board"
    with pytest.raises(MODULE.BoardError, match="source"):
        MODULE.build_board(
            panel_path=panel,
            panel_seal_path=panel_seal,
            output_root=root,
            source_count=2,
            negative_count=3,
        )
    assert not root.exists()


def test_output_root_is_immutable(tmp_path: Path) -> None:
    panel, panel_seal = fixture(tmp_path)
    root = tmp_path / "board"
    MODULE.build_board(
        panel_path=panel,
        panel_seal_path=panel_seal,
        output_root=root,
        source_count=2,
        negative_count=3,
    )
    with pytest.raises(MODULE.BoardError, match="already exists"):
        MODULE.build_board(
            panel_path=panel,
            panel_seal_path=panel_seal,
            output_root=root,
            source_count=2,
            negative_count=3,
        )
