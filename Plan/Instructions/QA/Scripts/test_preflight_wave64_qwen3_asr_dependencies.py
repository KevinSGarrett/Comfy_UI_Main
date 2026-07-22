from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/preflight_wave64_qwen3_asr_dependencies.py"
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_qwen3_asr_dependency_preflight.schema.json"
SPEC = importlib.util.spec_from_file_location("preflight_wave64_qwen3_asr_dependencies", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_model_root(tmp_path: Path) -> Path:
    root = tmp_path / "Qwen3-ASR-1.7B" / MODULE.EXPECTED_REVISION
    root.mkdir(parents=True)
    (root / "config.json").write_text(
        json.dumps(
            {
                "model_type": "qwen3_asr",
                "architectures": ["Qwen3ASRForConditionalGeneration"],
                "transformers_version": "4.57.6",
            }
        ),
        encoding="utf-8",
    )
    (root / "preprocessor_config.json").write_text(
        json.dumps({"processor_class": "Qwen3ASRProcessor"}), encoding="utf-8"
    )
    return root


def test_missing_dependencies_are_typed_without_runtime_claims(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_model_root(tmp_path)
    monkeypatch.setattr(MODULE, "distribution_version", lambda _name: None)
    monkeypatch.setattr(MODULE, "transformers_support_paths", lambda: [])
    receipt = MODULE.build_receipt(root)
    assert receipt["classification"] == "CONFIG_IDENTITY_PASS_DEPENDENCY_ACTION_REQUIRED"
    assert receipt["dependency_gaps"] == [
        "QWEN_ASR_DISTRIBUTION_MISSING",
        "TRANSFORMERS_DISTRIBUTION_MISSING",
    ]
    assert not any(receipt["runtime_claims"].values())


def test_metadata_present_does_not_claim_import_or_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_model_root(tmp_path)
    monkeypatch.setattr(MODULE, "distribution_version", lambda _name: "1.0")
    monkeypatch.setattr(MODULE, "transformers_support_paths", lambda: ["transformers/models/qwen3_asr/modeling.py"])
    receipt = MODULE.build_receipt(root)
    assert receipt["classification"] == "METADATA_DEPENDENCIES_PRESENT_IMPORT_AND_LOAD_UNQUALIFIED"
    assert receipt["dependency_gaps"] == []
    assert not any(receipt["runtime_claims"].values())


def test_config_mismatch_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_model_root(tmp_path)
    (root / "config.json").write_text(json.dumps({"model_type": "wrong"}), encoding="utf-8")
    monkeypatch.setattr(MODULE, "distribution_version", lambda _name: "1.0")
    monkeypatch.setattr(MODULE, "transformers_support_paths", lambda: ["transformers/models/qwen3_asr/modeling.py"])
    receipt = MODULE.build_receipt(root)
    assert receipt["classification"] == "MODEL_CONFIG_IDENTITY_FAIL"
    assert "MODEL_CONFIG_IDENTITY_MISMATCH" in receipt["dependency_gaps"]


def test_symlinked_config_is_rejected(tmp_path: Path) -> None:
    root = make_model_root(tmp_path)
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    (root / "config.json").unlink()
    try:
        (root / "config.json").symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable")
    with pytest.raises(ValueError, match="symlinked"):
        MODULE.build_receipt(root)


def test_receipt_write_is_atomic_and_no_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    MODULE.write_json_atomic_no_overwrite(output, {"ok": True})
    assert json.loads(output.read_text(encoding="utf-8")) == {"ok": True}
    with pytest.raises(FileExistsError, match="overwrite"):
        MODULE.write_json_atomic_no_overwrite(output, {"ok": False})


def test_schema_accepts_valid_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_model_root(tmp_path)
    monkeypatch.setattr(MODULE, "distribution_version", lambda _name: None)
    monkeypatch.setattr(MODULE, "transformers_support_paths", lambda: [])
    receipt = MODULE.build_receipt(root)
    receipt["model_root"] = f"/workspace/w64_aqa/models/Qwen3-ASR-1.7B/{MODULE.EXPECTED_REVISION}"
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(receipt)


def test_source_has_no_model_gpu_network_or_process_execution() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8").lower()
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imported_roots.intersection({"torch", "transformers", "qwen_asr"})
    forbidden_runtime_tokens = (
        "from_pretrained",
        "cuda",
        "nvidia-smi",
        "subprocess",
        "requests",
        "urllib",
        "socket",
    )
    assert not [token for token in forbidden_runtime_tokens if token in source]
