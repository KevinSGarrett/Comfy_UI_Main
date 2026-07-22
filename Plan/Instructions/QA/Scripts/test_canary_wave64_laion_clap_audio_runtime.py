from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/canary_wave64_laion_clap_audio_runtime.py"


def load_module():
    spec = importlib.util.spec_from_file_location("laion_clap_audio_canary", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def materialize_expected_package(module, root: Path) -> None:
    for relative_path, (size, digest) in module.EXPECTED_FILES.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = bytes.fromhex(digest) * ((size // 32) + 1)
        path.write_bytes(payload[:size])


def test_package_binding_contains_promoted_weight_identity() -> None:
    module = load_module()
    assert len(module.EXPECTED_FILES) == 15
    assert module.EXPECTED_FILES["pytorch_model.bin"] == (
        776444665,
        "314eb00cce6ad68d25237b8446b659ccdb136ed4672c1bca470f142f72455026",
    )
    assert module.UPSTREAM_REVISION == "ada0c23a36c4e8582805bb38fec3905903f18b41"


def test_validate_package_accepts_exact_file_set(monkeypatch, tmp_path: Path) -> None:
    module = load_module()
    materialize_expected_package(module, tmp_path)
    monkeypatch.setattr(
        module,
        "sha256_file",
        lambda path: module.EXPECTED_FILES[path.relative_to(tmp_path).as_posix()][1],
    )
    result = module.validate_package(tmp_path)
    assert result["file_count"] == 15
    assert result["total_bytes"] == sum(size for size, _ in module.EXPECTED_FILES.values())
    assert len(result["aggregate_manifest_sha256"]) == 64


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_validate_package_rejects_file_set_mutation(
    monkeypatch, tmp_path: Path, mutation: str
) -> None:
    module = load_module()
    materialize_expected_package(module, tmp_path)
    monkeypatch.setattr(module, "sha256_file", lambda _path: "0" * 64)
    if mutation == "missing":
        (tmp_path / "config.json").unlink()
    else:
        (tmp_path / "unexpected.bin").write_bytes(b"x")
    with pytest.raises(module.CanaryError, match="file-set mismatch"):
        module.validate_package(tmp_path)


def test_validate_audio_binds_exact_hash(tmp_path: Path) -> None:
    module = load_module()
    audio = tmp_path / "fixture.wav"
    audio.write_bytes(b"fixture")
    digest = hashlib.sha256(b"fixture").hexdigest()
    assert module.validate_audio(audio, digest)["sha256"] == digest
    with pytest.raises(module.CanaryError, match="SHA-256 mismatch"):
        module.validate_audio(audio, "0" * 64)


class FakeVector:
    def __init__(self, values):
        self.values = list(values)

    def __mul__(self, other):
        return FakeVector(a * b for a, b in zip(self.values, other.values))

    def sum(self):
        return FakeScalar(sum(self.values))


class FakeScalar:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


class FakeTensor:
    def __init__(self, rows):
        self.rows = [FakeVector(row) for row in rows]
        self.shape = (len(self.rows), len(self.rows[0].values))

    def __getitem__(self, index):
        return self.rows[index]

    def __sub__(self, other):
        del other
        return self

    def abs(self):
        return self

    def max(self):
        return FakeScalar(0.0)


def test_embedding_gate_requires_expected_speech_label() -> None:
    module = load_module()
    speech = [1.0] + [0.0] * 511
    music = [0.0, 1.0] + [0.0] * 510
    noise = [0.0, 0.0, 1.0] + [0.0] * 509
    silence = [0.0, 0.0, 0.0, 1.0] + [0.0] * 508
    audio = FakeTensor([speech])
    texts = FakeTensor([speech, music, noise, silence])
    result = module.evaluate_embedding_gate(audio, audio, texts)
    assert result["passed"] is True
    assert result["top_label"] == module.EXPECTED_TOP_LABEL


def test_process_exit_cleanup_is_required_for_capacity_authority() -> None:
    module = load_module()
    evidence = {
        "runtime": {},
        "embedding_gate": {"passed": True},
        "error": None,
        "authority": {
            "current_pod_runtime_capacity": False,
            "exact_fixture_speech_event": False,
            "exact_fixture_embedding_determinism": False,
        },
    }
    finalized, exit_code = module.finalize_process_exit_cleanup(
        evidence,
        gpu_before_worker={"used_mib": 648},
        gpu_after_worker_exit={"used_mib": 648},
        worker_returncode=0,
        worker_stdout="",
        worker_stderr="",
    )
    assert exit_code == 0
    assert finalized["authority"]["current_pod_runtime_capacity"] is True
    finalized, exit_code = module.finalize_process_exit_cleanup(
        evidence,
        gpu_before_worker={"used_mib": 648},
        gpu_after_worker_exit={"used_mib": 2048},
        worker_returncode=0,
        worker_stdout="",
        worker_stderr="",
    )
    assert exit_code == 1
    assert finalized["authority"]["current_pod_runtime_capacity"] is False
