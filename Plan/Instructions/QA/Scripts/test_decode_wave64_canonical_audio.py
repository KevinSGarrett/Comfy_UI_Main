from __future__ import annotations

import importlib.util
import json
import struct
import sys
import wave
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/decode_wave64_canonical_audio.py"
SPEC = importlib.util.spec_from_file_location("decode_wave64_canonical_audio", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def _write_pcm16_wav(path: Path, *, frames: int = 128, sample_rate_hz: int = 48000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate_hz)
        payload = b"".join(struct.pack("<h", (index * 13) % 1000) for index in range(frames))
        handle.writeframes(payload)


def test_row069_admission_fails_closed_on_current_hold_delta():
    admission = MOD.evaluate_row069_admission(ROOT)
    assert admission["dependency_satisfied"] is False
    assert "ROW069_DEPENDENCY_NOT_ACCEPTED" in admission["blocker_codes"]
    assert admission["row_complete"] is False


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert "ROW069_DEPENDENCY_NOT_ACCEPTED" in payload["blocker_codes"]
    assert "FULL_LIBRARY_RUNTIME_RECORD_ABSENT" in payload["blocker_codes"]
    assert payload["decoder_revision"] == MOD.DECODER_REVISION
    assert payload["canonical_pcm_contract"] == MOD.CANONICAL_PCM_CONTRACT
    assert len(payload["fixture_calibration"]["records"]) == 3


def test_fixture_wav_decode_is_deterministic_and_schema_valid(tmp_path: Path):
    wav_path = tmp_path / "probe.wav"
    _write_pcm16_wav(wav_path)
    first = MOD.decode_wav_file(ROOT, wav_path, asset_id="fixture:probe")
    second = MOD.decode_wav_file(ROOT, wav_path, asset_id="fixture:probe")
    MOD.validate_decode_record(ROOT, first)
    assert first == second
    assert first["decode_status"] == "pass"
    assert isinstance(first["canonical_pcm_sha256"], str)
    assert len(first["canonical_pcm_sha256"]) == 64
    assert first["source_immutable"] is True
    assert first["decision"]["library_authority"] is False
    assert "LIBRARY_AUTHORITY_NOT_GRANTED" in first["decision"]["blocker_codes"]
    assert first["canonical_pcm_contract"] == MOD.CANONICAL_PCM_CONTRACT
    assert first["codec"] == "pcm_s16le"
    assert first["channels"] == 1
    assert first["bit_depth"] == 16
    assert first["channel_layout"] == "mono"


def test_unsupported_extension_fails_closed(tmp_path: Path):
    path = tmp_path / "clip.mp3"
    path.write_bytes(b"ID3fake")
    record = MOD.decode_wav_file(ROOT, path, asset_id="fixture:mp3")
    MOD.validate_decode_record(ROOT, record)
    assert record["decode_status"] == "blocked"
    assert record["canonical_pcm_sha256"] is None
    assert record["blocker"]["code"] == "UNSUPPORTED_CODEC_OR_CONTAINER"
    assert record["decision"]["library_authority"] is False


def test_corrupt_wav_fails_closed(tmp_path: Path):
    path = tmp_path / "corrupt.wav"
    path.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    record = MOD.decode_wav_file(ROOT, path, asset_id="fixture:corrupt")
    MOD.validate_decode_record(ROOT, record)
    assert record["decode_status"] == "failed"
    assert record["canonical_pcm_sha256"] is None
    assert record["blocker"]["code"] == "DECODE_FAILED_CORRUPT_OR_UNREADABLE"
    assert record["source_immutable"] is True


def test_source_bytes_unchanged_after_decode(tmp_path: Path):
    wav_path = tmp_path / "immutable.wav"
    _write_pcm16_wav(wav_path)
    before = wav_path.read_bytes()
    record = MOD.decode_wav_file(ROOT, wav_path, asset_id="fixture:immutable")
    after = wav_path.read_bytes()
    assert before == after
    assert record["source_immutable"] is True
    assert record["source_sha256"] == MOD.sha256_bytes(before)


def test_pass_claim_without_pcm_hash_fails_closed():
    record = MOD.build_record(
        asset_id="bad",
        source_path="x.wav",
        source_sha256="0" * 64,
        source_bytes=1,
        codec="pcm_s16le",
        duration_seconds=1.0,
        sample_rate_hz=48000,
        channels=1,
        bit_depth=16,
        channel_layout="mono",
        decode_status="pass",
        canonical_pcm_sha256=None,
        frame_count=48000,
        source_immutable=True,
        blocker=None,
        library_authority=False,
        blocker_codes=["LIBRARY_AUTHORITY_NOT_GRANTED"],
    )
    with pytest.raises(MOD.CanonicalDecodeError):
        MOD.validate_decode_record(ROOT, record)


def test_blocked_without_typed_blocker_fails_closed():
    record = MOD.build_record(
        asset_id="bad-block",
        source_path="x.mp3",
        source_sha256="1" * 64,
        source_bytes=1,
        codec="mp3",
        duration_seconds=0.0,
        sample_rate_hz=1,
        channels=1,
        bit_depth=1,
        channel_layout="mono",
        decode_status="blocked",
        canonical_pcm_sha256=None,
        frame_count=0,
        source_immutable=True,
        blocker=None,
        library_authority=False,
        blocker_codes=["UNSUPPORTED_CODEC_OR_CONTAINER"],
    )
    with pytest.raises(MOD.CanonicalDecodeError):
        MOD.validate_decode_record(ROOT, record)


def test_main_library_mode_writes_hold_evidence(tmp_path: Path):
    output = tmp_path / "row070_hold.json"
    rc = MOD.main(["--root", str(ROOT), "--mode", "library", "--output", str(output)])
    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["row_complete"] is False
    assert payload["decision"]["row070_acceptance"] == "held"
