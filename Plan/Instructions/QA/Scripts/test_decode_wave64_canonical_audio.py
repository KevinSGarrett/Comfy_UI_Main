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


def _write_pcm24_wav(path: Path, *, frames: int = 128, sample_rate_hz: int = 48000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(3)
        handle.setframerate(sample_rate_hz)
        payload = bytearray()
        for index in range(frames):
            value = ((index * 97) % 200000) - 100000
            payload.extend(int(value).to_bytes(3, "little", signed=True))
        handle.writeframes(bytes(payload))


def _write_tone_mp3(path: Path, *, frames: int = 2048, sample_rate_hz: int = 44100) -> None:
    import numpy as np
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    tone = (np.linspace(-0.2, 0.2, frames, dtype=np.float32)).reshape(-1, 1)
    sf.write(str(path), tone, sample_rate_hz, format="MP3")


def test_row069_admission_accepts_current_library_index_authority():
    admission = MOD.evaluate_row069_admission(ROOT)
    assert admission["dependency_satisfied"] is True
    assert admission["blocker_codes"] == []
    assert admission["row_complete"] is True
    assert "PASS_LIBRARY_INDEX_AUTHORITY_ACCEPTED" in str(admission.get("status") or "")


def test_library_mode_emits_hold_packet_without_false_completion():
    payload = MOD.build_library_blocker_packet(ROOT)
    assert payload["row_complete"] is False
    assert payload["implementation_completion_claimed"] is False
    assert payload["runtime_completion_claimed"] is False
    assert payload["library_authority"] is False
    assert payload["decision"]["status"] == "blocked"
    assert payload["decision"]["product_completion"] is False
    assert "ROW069_DEPENDENCY_NOT_ACCEPTED" not in payload["blocker_codes"]
    assert payload["row069_admission"]["dependency_satisfied"] is True
    assert "FULL_LIBRARY_RUNTIME_RECORD_ABSENT" in payload["blocker_codes"]
    assert "CANONICAL_DECODER_LIBRARY_RUNTIME_ABSENT" in payload["blocker_codes"]
    assert "NON_WAV_CODEC_COVERAGE_ABSENT" in payload["blocker_codes"]
    assert payload["status"] == "HOLD_FULL_LIBRARY_DECODE_RUNTIME_ABSENT"
    assert payload["decoder_revision"] == MOD.DECODER_REVISION
    assert payload["canonical_pcm_contract"] == MOD.CANONICAL_PCM_CONTRACT
    assert len(payload["fixture_calibration"]["records"]) == 3


def test_library_mode_with_index_strata_runtime_clears_decoder_absent_blocker():
    strata = {
        "authority": "accepted_index_strata_bounded",
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "counts": {
            "sources_attempted": 2,
            "decode_pass": 1,
            "decode_blocked": 1,
            "decode_failed": 0,
        },
        "selection": {
            "wav_roles_selected": ["body"],
            "non_wav_extensions_selected": [".mp3"],
            "locator": {"index_sha256": "a" * 64},
        },
        "summary_path": "runtime_artifacts/audio_decode/example/summary.json",
        "summary_sha256": "b" * 64,
        "summary_bytes": 1,
        "receipt_path": "runtime_artifacts/audio_decode/example/receipt.json",
        "receipt_sha256": "c" * 64,
    }
    payload = MOD.build_library_blocker_packet(ROOT, index_strata_runtime=strata)
    assert "ROW069_DEPENDENCY_NOT_ACCEPTED" not in payload["blocker_codes"]
    assert "CANONICAL_DECODER_LIBRARY_RUNTIME_ABSENT" not in payload["blocker_codes"]
    assert "FULL_LIBRARY_RUNTIME_RECORD_ABSENT" in payload["blocker_codes"]
    assert payload["library_authority"] is False
    assert payload["row_complete"] is False
    assert payload["status"] == "HOLD_FULL_LIBRARY_DECODE_WITH_ACCEPTED_INDEX_STRATA_BOUNDED_RUNTIME"
    assert payload["accepted_index_strata_runtime"]["decode_pass"] == 1
    assert payload["highest_proof_tier_achieved"] == "RUNTIME_PASS_BOUNDED"


def test_active_index_locator_matches_accepted_row069_registry():
    locator = MOD.load_active_index_locator(ROOT)
    assert locator["library_authority"] is True
    assert locator["row069_acceptance"] == "accepted"
    assert locator["record_count"] == 39771
    assert len(locator["index_sha256"]) == 64
    assert locator["index_path"].is_file()


def test_select_accepted_index_strata_uses_synthetic_index(tmp_path: Path, monkeypatch):
    source_root = tmp_path / "audio"
    source_root.mkdir()
    wav_path = source_root / "body_tone.wav"
    # Exceed INDEX_STRATA_WAV_MIN_BYTES so the strata selector admits the candidate.
    _write_pcm16_wav(wav_path, frames=8192)
    mp3_path = source_root / "clip.mp3"
    mp3_path.write_bytes(b"ID3fake-bytes")

    index_path = tmp_path / "index.jsonl"
    records = [
        {
            "relative_path": "body_tone.wav",
            "absolute_path": str(wav_path),
            "extension": ".wav",
            "role": "body",
            "event_type": "body_foley",
            "duration_band": "short",
            "channels": 1,
            "bytes": wav_path.stat().st_size,
            "sha256": MOD.sha256_file(wav_path),
            "sample_rate_hz": 48000,
            "duration_seconds": 256 / 48000,
        },
        {
            "relative_path": "clip.mp3",
            "absolute_path": str(mp3_path),
            "extension": ".mp3",
            "role": "effects",
            "event_type": "action_sfx",
            "duration_band": "short",
            "channels": 1,
            "bytes": mp3_path.stat().st_size,
            "sha256": MOD.sha256_file(mp3_path),
            "sample_rate_hz": 44100,
            "duration_seconds": 1.0,
        },
    ]
    index_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    def fake_locator(_root: Path) -> dict:
        return {
            "registry_path": "Plan/10_REGISTRIES/audio_pack_functional_index_registry.json",
            "runtime_path": str(index_path),
            "index_path": index_path,
            "index_sha256": MOD.sha256_file(index_path),
            "index_bytes": index_path.stat().st_size,
            "source_root": source_root,
            "record_count": 2,
            "row069_acceptance": "accepted",
            "library_authority": True,
        }

    monkeypatch.setattr(MOD, "load_active_index_locator", fake_locator)
    selection = MOD.select_accepted_index_strata(
        ROOT,
        wav_roles=("body",),
        non_wav_extensions=(".mp3",),
    )
    assert selection["selection_complete_for_targets"] is True
    assert selection["wav_roles_selected"] == ["body"]
    assert selection["non_wav_extensions_selected"] == [".mp3"]
    assert len(selection["selected"]) == 2


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
    path = tmp_path / "clip.aac"
    path.write_bytes(b"not-a-real-aac")
    record = MOD.decode_wav_file(ROOT, path, asset_id="fixture:aac")
    MOD.validate_decode_record(ROOT, record)
    assert record["decode_status"] == "blocked"
    assert record["canonical_pcm_sha256"] is None
    assert record["blocker"]["code"] == "UNSUPPORTED_CODEC_OR_CONTAINER"
    assert record["decision"]["library_authority"] is False


def test_corrupt_mp3_fails_closed(tmp_path: Path):
    path = tmp_path / "clip.mp3"
    path.write_bytes(b"ID3fake-not-decodable")
    record = MOD.decode_wav_file(ROOT, path, asset_id="fixture:mp3-corrupt")
    MOD.validate_decode_record(ROOT, record)
    assert record["decode_status"] == "failed"
    assert record["canonical_pcm_sha256"] is None
    assert record["blocker"]["code"] == "DECODE_FAILED_CORRUPT_OR_UNREADABLE"
    assert record["decision"]["library_authority"] is False


def test_mp3_and_pcm24_decode_to_canonical_pcm(tmp_path: Path):
    mp3_path = tmp_path / "tone.mp3"
    wav24_path = tmp_path / "tone24.wav"
    _write_tone_mp3(mp3_path)
    _write_pcm24_wav(wav24_path)
    mp3 = MOD.decode_wav_file(ROOT, mp3_path, asset_id="fixture:mp3")
    wav24 = MOD.decode_wav_file(ROOT, wav24_path, asset_id="fixture:pcm24")
    MOD.validate_decode_record(ROOT, mp3)
    MOD.validate_decode_record(ROOT, wav24)
    assert mp3["decode_status"] == "pass"
    assert wav24["decode_status"] == "pass"
    assert mp3["codec"] == "mp3"
    assert wav24["codec"] == "pcm_s24le"
    assert isinstance(mp3["canonical_pcm_sha256"], str)
    assert len(mp3["canonical_pcm_sha256"]) == 64
    assert isinstance(wav24["canonical_pcm_sha256"], str)
    assert len(wav24["canonical_pcm_sha256"]) == 64


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


def test_frames_to_canonical_pcm_matches_channel_roundtrip():
    frames = struct.pack("<" + "h" * 8, *range(8))
    fast = MOD.frames_to_canonical_pcm_f32le(
        frames, channels=2, sample_width=2, frame_count=4
    )
    channels = MOD._frames_to_channels(
        frames, channels=2, sample_width=2, frame_count=4
    )
    slow = MOD.pack_pcm_f32le(channels)
    assert fast == slow
    assert len(MOD.sha256_bytes(fast)) == 64


def test_retained_index_decode_maps_every_record(tmp_path: Path, monkeypatch):
    source_root = tmp_path / "audio"
    source_root.mkdir()
    wav_path = source_root / "tone.wav"
    _write_pcm16_wav(wav_path, frames=256)
    mp3_path = source_root / "clip.mp3"
    mp3_path.write_bytes(b"ID3fake-bytes")

    index_path = tmp_path / "index.jsonl"
    records = [
        {
            "relative_path": "tone.wav",
            "absolute_path": str(wav_path),
            "extension": ".wav",
            "role": "body",
            "event_type": "body_foley",
            "duration_band": "short",
            "channels": 1,
            "bytes": wav_path.stat().st_size,
            "sha256": MOD.sha256_file(wav_path),
            "sample_rate_hz": 48000,
            "duration_seconds": 256 / 48000,
        },
        {
            "relative_path": "clip.mp3",
            "absolute_path": str(mp3_path),
            "extension": ".mp3",
            "role": "effects",
            "event_type": "action_sfx",
            "duration_band": "short",
            "channels": 1,
            "bytes": mp3_path.stat().st_size,
            "sha256": MOD.sha256_file(mp3_path),
            "sample_rate_hz": 44100,
            "duration_seconds": 1.0,
        },
    ]
    index_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    def fake_locator(_root: Path) -> dict:
        return {
            "registry_path": "Plan/10_REGISTRIES/audio_pack_functional_index_registry.json",
            "runtime_path": str(index_path),
            "index_path": index_path,
            "index_sha256": MOD.sha256_file(index_path),
            "index_bytes": index_path.stat().st_size,
            "source_root": source_root,
            "record_count": 2,
            "row069_acceptance": "accepted",
            "library_authority": True,
        }

    monkeypatch.setattr(MOD, "load_active_index_locator", fake_locator)
    monkeypatch.setattr(
        MOD,
        "evaluate_row069_admission",
        lambda _root, delta_path=None: {
            "dependency_satisfied": True,
            "blocker_codes": [],
            "row_complete": True,
            "status": "PASS_LIBRARY_INDEX_AUTHORITY_ACCEPTED_NO_PRODUCT_COMPLETION",
            "path": "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-069_FULL_AUDIO_LIBRARY_INDEX_CURRENT_DELTA_20260719.json",
            "sha256": "a" * 64,
            "bytes": 1,
        },
    )

    runtime_dir = tmp_path / "retained"
    summary = MOD.run_retained_index_decode(
        ROOT,
        runtime_dir=runtime_dir,
        limit=None,
        resume=False,
        checkpoint_every=1,
    )
    assert summary["coverage_complete"] is True
    assert summary["library_authority"] is False
    assert summary["row_complete"] is False
    assert summary["counts"]["records_processed"] == 2
    assert summary["counts"]["decode_pass"] == 1
    assert summary["counts"]["decode_failed"] == 1
    assert summary["counts"]["non_wav_failed"] == 1
    assert summary["source_immutability_fingerprint"]["fingerprint_complete"] is True

    packet = MOD.build_library_blocker_packet(ROOT, retained_index_runtime=summary)
    assert packet["row_complete"] is False
    assert "FULL_LIBRARY_RUNTIME_RECORD_ABSENT" not in packet["blocker_codes"]
    assert "SOURCE_IMMUTABILITY_FULL_LIBRARY_FINGERPRINT_ABSENT" not in packet["blocker_codes"]
    assert "NON_WAV_CODEC_COVERAGE_ABSENT" in packet["blocker_codes"]
    assert packet["status"] == "HOLD_NON_WAV_CODEC_WITH_RETAINED_INDEX_RECONCILE_RUNTIME"
    assert packet["accepted_index_retained_runtime"]["coverage_complete"] is True


def test_retained_index_with_mp3_clears_non_wav_gap(tmp_path: Path, monkeypatch):
    source_root = tmp_path / "audio"
    source_root.mkdir()
    wav_path = source_root / "tone.wav"
    mp3_path = source_root / "clip.mp3"
    _write_pcm16_wav(wav_path, frames=256)
    _write_tone_mp3(mp3_path)

    index_path = tmp_path / "index.jsonl"
    records = [
        {
            "relative_path": "tone.wav",
            "absolute_path": str(wav_path),
            "extension": ".wav",
            "role": "body",
            "event_type": "body_foley",
            "duration_band": "short",
            "channels": 1,
            "bytes": wav_path.stat().st_size,
            "sha256": MOD.sha256_file(wav_path),
        },
        {
            "relative_path": "clip.mp3",
            "absolute_path": str(mp3_path),
            "extension": ".mp3",
            "role": "effects",
            "event_type": "action_sfx",
            "duration_band": "short",
            "channels": 1,
            "bytes": mp3_path.stat().st_size,
            "sha256": MOD.sha256_file(mp3_path),
        },
    ]
    index_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    def fake_locator(_root: Path) -> dict:
        return {
            "registry_path": "Plan/10_REGISTRIES/audio_pack_functional_index_registry.json",
            "runtime_path": str(index_path),
            "index_path": index_path,
            "index_sha256": MOD.sha256_file(index_path),
            "index_bytes": index_path.stat().st_size,
            "source_root": source_root,
            "record_count": 2,
            "row069_acceptance": "accepted",
            "library_authority": True,
        }

    monkeypatch.setattr(MOD, "load_active_index_locator", fake_locator)
    monkeypatch.setattr(
        MOD,
        "evaluate_row069_admission",
        lambda _root, delta_path=None: {
            "dependency_satisfied": True,
            "blocker_codes": [],
            "row_complete": True,
            "status": "PASS_LIBRARY_INDEX_AUTHORITY_ACCEPTED_NO_PRODUCT_COMPLETION",
            "path": "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-069_FULL_AUDIO_LIBRARY_INDEX_CURRENT_DELTA_20260719.json",
            "sha256": "a" * 64,
            "bytes": 1,
        },
    )

    runtime_dir = tmp_path / "retained_mp3"
    summary = MOD.run_retained_index_decode(
        ROOT,
        runtime_dir=runtime_dir,
        limit=None,
        resume=False,
        checkpoint_every=1,
    )
    assert summary["coverage_complete"] is True
    assert summary["counts"]["decode_pass"] == 2
    assert summary["counts"]["non_wav_pass"] == 1
    assert summary["blocker_histogram"] == {}

    packet = MOD.build_library_blocker_packet(ROOT, retained_index_runtime=summary)
    assert "NON_WAV_CODEC_COVERAGE_ABSENT" not in packet["blocker_codes"]
    assert "UNSUPPORTED_SAMPLE_FORMAT_WAV_COVERAGE_ABSENT" not in packet["blocker_codes"]
    assert packet["blocker_codes"] == []
    assert packet["row_complete"] is True
    assert packet["library_authority"] is True
    assert packet["decision"]["row070_acceptance"] == "accepted"
    assert packet["decision"]["product_completion"] is False
    assert packet["status"] == "PASS_LIBRARY_PCM_AUTHORITY_ACCEPTED_NO_PRODUCT_COMPLETION"


def test_retained_index_respects_limit_without_false_complete(tmp_path: Path, monkeypatch):
    source_root = tmp_path / "audio"
    source_root.mkdir()
    paths = []
    for index in range(3):
        wav_path = source_root / f"tone_{index}.wav"
        _write_pcm16_wav(wav_path, frames=128 + index)
        paths.append(wav_path)

    index_path = tmp_path / "index.jsonl"
    records = []
    for wav_path in paths:
        records.append(
            {
                "relative_path": wav_path.name,
                "absolute_path": str(wav_path),
                "extension": ".wav",
                "role": "effects",
                "event_type": "action_sfx",
                "duration_band": "short",
                "channels": 1,
                "bytes": wav_path.stat().st_size,
                "sha256": MOD.sha256_file(wav_path),
            }
        )
    index_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    def fake_locator(_root: Path) -> dict:
        return {
            "registry_path": "Plan/10_REGISTRIES/audio_pack_functional_index_registry.json",
            "runtime_path": str(index_path),
            "index_path": index_path,
            "index_sha256": MOD.sha256_file(index_path),
            "index_bytes": index_path.stat().st_size,
            "source_root": source_root,
            "record_count": 3,
            "row069_acceptance": "accepted",
            "library_authority": True,
        }

    monkeypatch.setattr(MOD, "load_active_index_locator", fake_locator)
    monkeypatch.setattr(
        MOD,
        "evaluate_row069_admission",
        lambda _root, delta_path=None: {
            "dependency_satisfied": True,
            "blocker_codes": [],
            "row_complete": True,
            "status": "PASS",
            "path": "x",
            "sha256": "b" * 64,
            "bytes": 1,
        },
    )

    runtime_dir = tmp_path / "retained_partial"
    first = MOD.run_retained_index_decode(
        ROOT, runtime_dir=runtime_dir, limit=1, resume=False, checkpoint_every=1
    )
    assert first["coverage_complete"] is False
    assert first["counts"]["records_processed"] == 1
    second = MOD.run_retained_index_decode(
        ROOT, runtime_dir=runtime_dir, limit=None, resume=True, checkpoint_every=1
    )
    assert second["coverage_complete"] is True
    assert second["counts"]["records_processed"] == 3
    assert second["library_authority"] is False
