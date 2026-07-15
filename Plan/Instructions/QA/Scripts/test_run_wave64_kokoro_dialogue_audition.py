from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from unittest import mock

import numpy as np
import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/run_wave64_kokoro_dialogue_audition.py"
SPEC = importlib.util.spec_from_file_location("wave64_kokoro_runner", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        text=MODULE.EXPECTED_TEXT,
        speeds=["1.0", "1.15", "1.3"],
        seed=MODULE.EXPECTED_SEED,
        character_id="C01",
        line_id="L001",
        delivery_style="focused",
        intensity="controlled",
        model=str(tmp_path / "model.pth"),
        config=str(tmp_path / "config.json"),
        voice=str(tmp_path / "voice.pt"),
        output_dir=str(tmp_path / "output"),
        run_id="test-run",
    )


def test_speeds_are_exact_and_immutable() -> None:
    assert MODULE.parse_speeds(["1.0", "1.15", "1.3"]) == MODULE.EXPECTED_SPEEDS
    with pytest.raises(ValueError, match="exactly"):
        MODULE.parse_speeds(["1.0", "1.2", "1.3"])
    with pytest.raises(ValueError, match="exactly"):
        MODULE.parse_speeds(["1.0", "1.15"])


def test_existing_output_directory_rejects_retry(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ValueError, match="retries are prohibited"):
        MODULE.prepare_output_dir(output)


def test_asset_hash_and_size_are_enforced(tmp_path: Path) -> None:
    path = tmp_path / "asset.bin"
    path.write_bytes(b"wrong")
    with pytest.raises(ValueError, match="hash or byte count mismatch"):
        MODULE.bind_file(path, "asset", {"sha256": "0" * 64, "bytes": 5})


def test_underlength_audio_receives_trailing_silence_only() -> None:
    raw = np.linspace(-0.5, 0.5, 60000, dtype=np.float32)
    packaged, padding = MODULE.package_candidate(raw)
    assert packaged is not None
    assert padding == 12000
    assert packaged.size == MODULE.EXPECTED_SAMPLE_COUNT
    np.testing.assert_array_equal(packaged[: raw.size], raw)
    np.testing.assert_array_equal(packaged[raw.size :], np.zeros(padding, dtype=np.float32))


def test_overlength_audio_is_preserved_but_not_packaged() -> None:
    raw = np.zeros(MODULE.EXPECTED_SAMPLE_COUNT + 1, dtype=np.float32)
    packaged, padding = MODULE.package_candidate(raw)
    assert packaged is None
    assert padding == 0
    assert raw.size == MODULE.EXPECTED_SAMPLE_COUNT + 1


def test_control_contract_prohibits_media_mutation(tmp_path: Path) -> None:
    contract = MODULE.build_control_contract(args(tmp_path), MODULE.EXPECTED_SPEEDS)
    assert contract["retry_allowed"] is False
    assert contract["adaptive_speed_tuning_allowed"] is False
    assert contract["truncation_allowed"] is False
    assert contract["time_stretch_allowed"] is False
    assert contract["loudness_normalization_allowed"] is False
    assert contract["trailing_silence_padding_allowed"] is True
    assert contract["emotion_class"] is None
    assert contract["voice_identity_policy"] == "designed_synthetic_voice"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("text", "changed", "dialogue text"),
        ("seed", 1, "seed"),
        ("character_id", "C02", "character or line"),
        ("line_id", "L002", "character or line"),
        ("delivery_style", "neutral", "delivery style or intensity"),
        ("intensity", "high", "delivery style or intensity"),
    ],
)
def test_control_contract_rejects_drift(tmp_path: Path, field: str, value, message: str) -> None:
    candidate = args(tmp_path)
    setattr(candidate, field, value)
    with pytest.raises(ValueError, match=message):
        MODULE.build_control_contract(candidate, MODULE.EXPECTED_SPEEDS)


def test_runtime_package_identity_rejects_version_drift() -> None:
    versions = dict(MODULE.EXPECTED_PACKAGES)
    versions["kokoro"] = "9.9.9"
    with mock.patch.object(MODULE.importlib.metadata, "version", side_effect=lambda name: versions[name]):
        with mock.patch.dict("sys.modules", {"torch": mock.Mock(__version__=MODULE.EXPECTED_TORCH_VERSION)}):
            with pytest.raises(ValueError, match="runtime package identity mismatch"):
                MODULE.runtime_package_identity()


def test_pcm_range_violation_fails_instead_of_normalizing() -> None:
    result = mock.Mock(audio=np.array([0.0, 1.01], dtype=np.float32))
    with pytest.raises(ValueError, match="normalization is prohibited"):
        MODULE.collect_audio([result])
