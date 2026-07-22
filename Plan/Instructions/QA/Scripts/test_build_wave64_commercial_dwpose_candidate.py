from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_commercial_dwpose_candidate.py"
CONTRACT = ROOT / "Plan/10_REGISTRIES/wave64_wave42_commercial_dwpose_replacement_contract.json"


def _module():
    spec = importlib.util.spec_from_file_location("dwpose_candidate", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(path: Path, node_ids: list[int], pose_model: str = "dw-ll_ucoco_384_bs5.torchscript.pt") -> None:
    nodes = [
        {"id": node_id, "type": "DWPreprocessor", "widgets_values": ["enable", "enable", "disable", 1024, "yolox_l.onnx", pose_model, "disable"]}
        for node_id in node_ids
    ]
    path.write_text(json.dumps({"nodes": nodes}), encoding="utf-8")


def test_transform_preserves_sources_and_replaces_only_contract_nodes(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "source"
    output = tmp_path / "candidate"
    source.mkdir()
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    for workflow in contract["source_workflows"]:
        path = source / workflow["filename"]
        _fixture(path, workflow["node_ids"])
        workflow["sha256"] = module._sha256(path)
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    before = {path.name: path.read_bytes() for path in source.iterdir()}
    manifest = module.build_candidates(source, output, contract_path)
    assert {path.name: path.read_bytes() for path in source.iterdir()} == before
    assert len(manifest["workflows"]) == 2
    for workflow in contract["source_workflows"]:
        candidate = json.loads((output / workflow["filename"]).read_text(encoding="utf-8"))
        assert {node["id"] for node in candidate["nodes"]} == set(workflow["node_ids"])
        assert all(node["type"] == "Wave64CommercialDWPosePreprocessor" for node in candidate["nodes"])
        assert all(node["widgets_values"][5] == "dw-ll_ucoco_384.onnx" for node in candidate["nodes"])
        assert all(node["properties"]["wave64_replacement_contract_id"] == contract["contract_id"] for node in candidate["nodes"])


def test_transform_fails_closed_on_in_place_hash_and_widget_drift(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "source"
    source.mkdir()
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    for workflow in contract["source_workflows"]:
        path = source / workflow["filename"]
        _fixture(path, workflow["node_ids"])
        workflow["sha256"] = module._sha256(path)
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    with pytest.raises(ValueError, match="in-place"):
        module.build_candidates(source, source, contract_path)
    first = source / contract["source_workflows"][0]["filename"]
    _fixture(first, contract["source_workflows"][0]["node_ids"], pose_model="drifted.pt")
    with pytest.raises(ValueError, match="hash mismatch"):
        module.build_candidates(source, tmp_path / "out", contract_path)
