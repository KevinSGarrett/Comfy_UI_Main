from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/audit_wave64_hf_snapshot_storage.py"


def _module():
    spec = importlib.util.spec_from_file_location("hf_snapshot_audit", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_audit_verifies_lfs_and_git_blob_identities(tmp_path: Path) -> None:
    module = _module()
    weight = tmp_path / "model.safetensors"
    config = tmp_path / "config.json"
    weight.write_bytes(b"weight")
    config.write_bytes(b"config")
    provider = {
        "sha": "revision",
        "cardData": {"license": "apache-2.0"},
        "siblings": [
            {"rfilename": weight.name, "size": weight.stat().st_size, "lfs": {"sha256": module._sha256(weight)}},
            {"rfilename": config.name, "size": config.stat().st_size, "blobId": module._git_blob_sha1(config)},
        ],
    }
    receipt = module.audit_snapshot(tmp_path, "publisher/model", "revision", lambda *_: provider)
    assert receipt["matching_files"] == 2
    assert receipt["mismatches"] == []
    assert receipt["authority"] == {"storage_identity": True, "model_load": False, "runtime": False}


def test_audit_uses_provider_relative_paths_and_excludes_symlink_aliases(tmp_path: Path) -> None:
    module = _module()
    nested = tmp_path / "tokenizer" / "vocab.json"
    nested.parent.mkdir()
    nested.write_bytes(b"nested")
    alias = tmp_path / "alias.json"
    try:
        alias.symlink_to(nested)
    except OSError:
        pass
    provider = {
        "sha": "revision",
        "siblings": [
            {
                "rfilename": "tokenizer/vocab.json",
                "size": nested.stat().st_size,
                "blobId": module._git_blob_sha1(nested),
            }
        ],
    }
    receipt = module.audit_snapshot(tmp_path, "publisher/model", "revision", lambda *_: provider)
    assert receipt["matching_files"] == 1
    assert receipt["actual_primary_files"] == 1
    assert receipt["extra_primary_files"] == []
    assert receipt["authority"]["storage_identity"] is True


def test_audit_fails_authority_on_missing_drift_extra_and_revision(tmp_path: Path) -> None:
    module = _module()
    expected = tmp_path / "expected.bin"
    expected.write_bytes(b"expected")
    provider = {"sha": "revision", "siblings": [{"rfilename": expected.name, "size": 8, "lfs": {"sha256": module._sha256(expected)}}]}
    expected.write_bytes(b"drifted!")
    (tmp_path / "extra.bin").write_bytes(b"extra")
    receipt = module.audit_snapshot(tmp_path, "publisher/model", "revision", lambda *_: provider)
    assert receipt["authority"]["storage_identity"] is False
    assert receipt["extra_primary_files"] == ["extra.bin"]
    assert len(receipt["mismatches"]) == 1
    try:
        module.audit_snapshot(tmp_path, "publisher/model", "revision", lambda *_: {"sha": "wrong", "siblings": []})
    except ValueError as error:
        assert "revision mismatch" in str(error)
    else:
        raise AssertionError("revision drift was accepted")
