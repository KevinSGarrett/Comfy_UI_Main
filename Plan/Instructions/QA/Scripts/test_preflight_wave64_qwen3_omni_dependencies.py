from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/preflight_wave64_qwen3_omni_dependencies.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_qwen3_omni_dependency_preflight.schema.json"
SPEC = importlib.util.spec_from_file_location("qwen3_omni_dependency_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_model_root(tmp_path: Path) -> Path:
    root = tmp_path / "Qwen3-Omni-30B-A3B-Thinking" / MODULE.EXPECTED_REVISION
    root.mkdir(parents=True)
    (root / "config.json").write_text(
        json.dumps(
            {
                "model_type": "qwen3_omni_moe",
                "architectures": ["Qwen3OmniMoeForConditionalGeneration"],
                "transformers_version": "4.57.0.dev0",
                "thinker_config": {
                    "model_type": "qwen3_omni_moe_thinker",
                    "audio_config": {"model_type": "qwen3_omni_moe_audio_encoder"},
                    "vision_config": {"model_type": "qwen3_omni_moe_vision_encoder"},
                    "text_config": {"model_type": "qwen3_omni_moe_text"},
                },
            }
        ),
        encoding="utf-8",
    )
    (root / "preprocessor_config.json").write_text(
        json.dumps({"processor_class": "Qwen3OmniMoeProcessor"}), encoding="utf-8"
    )
    return root


def test_missing_dependencies_are_typed_without_runtime_claims(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_model_root(tmp_path)
    monkeypatch.setattr(MODULE, "distribution_version", lambda _name: None)
    monkeypatch.setattr(MODULE, "transformers_support_paths", lambda: [])
    receipt = MODULE.build_receipt(root)
    assert receipt["classification"] == "CONFIG_IDENTITY_PASS_DEPENDENCY_ACTION_REQUIRED"
    assert receipt["dependency_gaps"] == [
        "QWEN_OMNI_UTILS_DISTRIBUTION_MISSING",
        "TRANSFORMERS_DISTRIBUTION_MISSING",
    ]
    assert not any(receipt["runtime_claims"].values())


def test_present_metadata_still_does_not_claim_import_or_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_model_root(tmp_path)
    monkeypatch.setattr(MODULE, "distribution_version", lambda _name: "5.2.0")
    monkeypatch.setattr(
        MODULE,
        "transformers_support_paths",
        lambda: ["transformers/models/qwen3_omni_moe/modeling.py"],
    )
    receipt = MODULE.build_receipt(root)
    assert receipt["classification"] == "METADATA_DEPENDENCIES_PRESENT_IMPORT_AND_LOAD_UNQUALIFIED"
    assert receipt["dependency_gaps"] == []
    assert not any(receipt["runtime_claims"].values())


def test_component_mismatch_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_model_root(tmp_path)
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    config["thinker_config"]["audio_config"]["model_type"] = "wrong"
    (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(MODULE, "distribution_version", lambda _name: "1")
    monkeypatch.setattr(MODULE, "transformers_support_paths", lambda: ["support"])
    receipt = MODULE.build_receipt(root)
    assert receipt["classification"] == "MODEL_CONFIG_IDENTITY_FAIL"
    assert not receipt["assertions"]["component_types_exact"]


def test_schema_accepts_valid_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_model_root(tmp_path)
    monkeypatch.setattr(MODULE, "distribution_version", lambda _name: None)
    monkeypatch.setattr(MODULE, "transformers_support_paths", lambda: [])
    receipt = MODULE.build_receipt(root)
    receipt["model_root"] = (
        "/workspace/w64_aqa/models/Qwen3-Omni-30B-A3B-Thinking/"
        + MODULE.EXPECTED_REVISION
    )
    jsonschema.Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8"))
    ).validate(receipt)


def test_receipt_write_is_no_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    MODULE.write_json_atomic_no_overwrite(output, {"ok": True})
    with pytest.raises(FileExistsError, match="overwrite"):
        MODULE.write_json_atomic_no_overwrite(output, {"ok": False})


def test_source_has_no_model_gpu_network_or_process_execution() -> None:
    source = SCRIPT.read_text(encoding="utf-8").lower()
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imported_roots.intersection({"torch", "transformers", "qwen_omni_utils"})
    forbidden = ("from_pretrained", "cuda", "nvidia-smi", "subprocess", "requests", "urllib", "socket")
    assert not [token for token in forbidden if token in source]
