#!/usr/bin/env python3
"""Fail-closed Wave64 Row070 canonical audio decode authority slice.

Fixture mode may decode bounded PCM WAV inputs into the frozen f32le PCM
hash domain. Library mode refuses authority until Row069 acceptance exists
and a full-library reconcile runtime is present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import wave
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/canonical_audio_decode_record.schema.json")
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-070_canonical_audio_decode.json"
)
ROW069_DELTA = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-069_FULL_AUDIO_LIBRARY_INDEX_CURRENT_DELTA_20260719.json"
)
DECODER_REVISION = "wave64_row070_canonical_pcm_v0.1.0"
TRACKER_ID = "TRK-W64-070"
ITEM_ID = "ITEM-W64-070"
SCHEMA_VERSION = "1.0.0"

CANONICAL_PCM_CONTRACT: dict[str, str] = {
    "sample_format": "ieee_float32",
    "endianness": "little",
    "interleaving": "frame_interleaved",
    "channel_order_policy": "preserve_source_order",
    "sample_rate_policy": "preserve_source_rate",
    "trim_policy": "no_trim",
    "normalization_policy": "none_full_scale_integer_to_float",
    "hash_domain": "raw_interleaved_f32le_bytes",
}

CHANNEL_LAYOUTS = {
    1: "mono",
    2: "stereo",
}


class CanonicalDecodeError(RuntimeError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_under(root: Path, relative: Path, label: str) -> Path:
    if relative.is_absolute():
        return relative.resolve()
    path = (root / relative).resolve()
    root_resolved = root.resolve()
    if root_resolved not in path.parents and path != root_resolved:
        raise CanonicalDecodeError(f"path_escapes_root:{label}")
    return path


def pack_pcm_f32le(channels: list[list[float]]) -> bytes:
    if not channels or not channels[0]:
        raise CanonicalDecodeError("empty_pcm")
    frame_count = len(channels[0])
    if any(len(channel) != frame_count for channel in channels):
        raise CanonicalDecodeError("channel_length_mismatch")
    parts: list[bytes] = []
    for index in range(frame_count):
        for channel in channels:
            parts.append(struct.pack("<f", float(channel[index])))
    return b"".join(parts)


def channel_layout_for(channels: int) -> str:
    return CHANNEL_LAYOUTS.get(channels, f"discrete_{channels}ch")


def evaluate_row069_admission(root: Path, delta_path: Path | None = None) -> dict[str, Any]:
    path = resolve_under(root, delta_path or ROW069_DELTA, "row069_delta")
    if not path.is_file():
        return {
            "dependency_satisfied": False,
            "blocker_codes": ["ROW069_DELTA_ABSENT"],
            "row_complete": False,
            "path": str(path.relative_to(root)).replace("\\", "/"),
        }
    payload = load_json(path)
    row_complete = payload.get("row_complete") is True
    acceptance = str(
        payload.get("decision", {}).get("row069_acceptance")
        or payload.get("qa_decision")
        or ""
    ).lower()
    dependency_satisfied = row_complete and acceptance in {
        "accepted",
        "pass",
        "passed",
        "row069_acceptance_pass",
    }
    blocker_codes: list[str] = []
    if not dependency_satisfied:
        blocker_codes.append("ROW069_DEPENDENCY_NOT_ACCEPTED")
    return {
        "dependency_satisfied": dependency_satisfied,
        "blocker_codes": blocker_codes,
        "row_complete": row_complete,
        "status": str(payload.get("status", "")),
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def validate_decode_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    semantic = semantic_errors(record)
    if errors or semantic:
        if errors:
            first = errors[0]
            location = ".".join(str(part) for part in first.absolute_path) or "$"
            raise CanonicalDecodeError(f"schema_validation_failed:{location}:{first.message}")
        raise CanonicalDecodeError(f"semantic_validation_failed:{semantic[0]}")


def semantic_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    decode_status = record.get("decode_status")
    decision = record.get("decision") if isinstance(record.get("decision"), dict) else {}
    blocker = record.get("blocker")
    pcm_hash = record.get("canonical_pcm_sha256")
    contract = record.get("canonical_pcm_contract")
    if contract != CANONICAL_PCM_CONTRACT:
        errors.append("canonical_pcm_contract must match frozen Row070 contract constants")
    if decode_status == "pass":
        if not isinstance(pcm_hash, str):
            errors.append("pass requires canonical_pcm_sha256 string")
        if blocker is not None:
            errors.append("pass requires blocker == null")
        if record.get("source_immutable") is not True:
            errors.append("pass requires source_immutable == true")
        if record.get("frame_count", 0) < 1:
            errors.append("pass requires frame_count >= 1")
        if decision.get("status") not in {"pass", "blocked"}:
            errors.append("pass decode_status requires decision.status pass or blocked")
        if decision.get("status") == "pass" and decision.get("library_authority") is not True:
            errors.append("decision.status pass requires library_authority == true")
        if decision.get("status") == "blocked":
            if decision.get("library_authority") is True:
                errors.append("technical decode pass with blocked decision cannot claim library_authority")
            if "LIBRARY_AUTHORITY_NOT_GRANTED" not in decision.get("blocker_codes", []):
                errors.append(
                    "technical decode pass with blocked decision requires LIBRARY_AUTHORITY_NOT_GRANTED"
                )
        if decision.get("library_authority") is True and decision.get("blocker_codes"):
            errors.append("library pass cannot retain blocker_codes")
    elif decode_status in {"blocked", "failed"}:
        if not isinstance(blocker, dict) or not blocker.get("code") or not blocker.get("detail"):
            errors.append("blocked/failed requires typed blocker code and detail")
        if pcm_hash is not None:
            errors.append("blocked/failed requires canonical_pcm_sha256 == null")
        if decision.get("status") not in {"blocked", "failed"}:
            errors.append("blocked/failed decode_status requires matching decision.status")
        if decision.get("library_authority") is True:
            errors.append("blocked/failed cannot claim library_authority")
        if not decision.get("blocker_codes"):
            errors.append("blocked/failed requires nonempty decision.blocker_codes")
    duration = record.get("duration_seconds")
    sample_rate = record.get("sample_rate_hz")
    frame_count = record.get("frame_count")
    if (
        decode_status == "pass"
        and isinstance(duration, (int, float))
        and isinstance(sample_rate, int)
        and isinstance(frame_count, int)
        and sample_rate > 0
    ):
        expected = frame_count / sample_rate
        if not math.isclose(float(duration), expected, rel_tol=0.0, abs_tol=1e-9):
            errors.append("duration_seconds must equal frame_count / sample_rate_hz for pass")
    return errors


def build_record(
    *,
    asset_id: str,
    source_path: str,
    source_sha256: str,
    source_bytes: int,
    codec: str,
    duration_seconds: float,
    sample_rate_hz: int,
    channels: int,
    bit_depth: int,
    channel_layout: str,
    decode_status: str,
    canonical_pcm_sha256: str | None,
    frame_count: int,
    source_immutable: bool,
    blocker: dict[str, str] | None,
    library_authority: bool,
    blocker_codes: list[str],
) -> dict[str, Any]:
    decision_status = decode_status
    return {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "decoder_revision": DECODER_REVISION,
        "asset_id": asset_id,
        "source_path": source_path,
        "source_sha256": source_sha256,
        "source_bytes": source_bytes,
        "codec": codec,
        "duration_seconds": duration_seconds,
        "sample_rate_hz": sample_rate_hz,
        "channels": channels,
        "bit_depth": bit_depth,
        "channel_layout": channel_layout,
        "decode_status": decode_status,
        "canonical_pcm_sha256": canonical_pcm_sha256,
        "canonical_pcm_contract": dict(CANONICAL_PCM_CONTRACT),
        "frame_count": frame_count,
        "source_immutable": source_immutable,
        "blocker": blocker,
        "decision": {
            "status": decision_status,
            "blocker_codes": list(blocker_codes),
            "library_authority": library_authority,
        },
    }


def _frames_to_channels(
    frames: bytes,
    *,
    channels: int,
    sample_width: int,
    frame_count: int,
) -> list[list[float]]:
    if sample_width == 2:
        count = frame_count * channels
        values = struct.unpack("<" + "h" * count, frames)
        scale = 32768.0
        channel_samples = [[] for _ in range(channels)]
        for index, value in enumerate(values):
            channel_samples[index % channels].append(value / scale)
        return channel_samples
    if sample_width == 4:
        count = frame_count * channels
        # Prefer IEEE float32 WAV; integer 32-bit PCM is unsupported in this slice.
        floats = struct.unpack("<" + "f" * count, frames)
        channel_samples = [[] for _ in range(channels)]
        for index, value in enumerate(floats):
            channel_samples[index % channels].append(float(value))
        return channel_samples
    raise CanonicalDecodeError(f"unsupported_sample_width:{sample_width}")


def decode_wav_file(root: Path, source: Path, *, asset_id: str | None = None) -> dict[str, Any]:
    path = source if source.is_absolute() else resolve_under(root, source, "source")
    if not path.is_file():
        return build_record(
            asset_id=asset_id or path.name,
            source_path=str(path),
            source_sha256=sha256_bytes(b""),
            source_bytes=0,
            codec="missing",
            duration_seconds=0.0,
            sample_rate_hz=1,
            channels=1,
            bit_depth=1,
            channel_layout="mono",
            decode_status="failed",
            canonical_pcm_sha256=None,
            frame_count=0,
            source_immutable=True,
            blocker={
                "code": "SOURCE_MISSING",
                "detail": f"Source path does not exist: {path}",
            },
            library_authority=False,
            blocker_codes=["SOURCE_MISSING"],
        )

    before_sha = sha256_file(path)
    before_bytes = path.stat().st_size
    suffix = path.suffix.lower()
    if suffix != ".wav":
        return build_record(
            asset_id=asset_id or path.name,
            source_path=str(path.relative_to(root)).replace("\\", "/")
            if root.resolve() in path.resolve().parents
            else str(path),
            source_sha256=before_sha,
            source_bytes=before_bytes,
            codec=suffix.lstrip(".") or "unknown",
            duration_seconds=0.0,
            sample_rate_hz=1,
            channels=1,
            bit_depth=1,
            channel_layout="mono",
            decode_status="blocked",
            canonical_pcm_sha256=None,
            frame_count=0,
            source_immutable=True,
            blocker={
                "code": "UNSUPPORTED_CODEC_OR_CONTAINER",
                "detail": (
                    "This Row070 slice only decodes PCM WAV via the stdlib wave reader; "
                    f"extension '{suffix}' is unsupported."
                ),
            },
            library_authority=False,
            blocker_codes=["UNSUPPORTED_CODEC_OR_CONTAINER"],
        )

    try:
        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate_hz = handle.getframerate()
            frame_count = handle.getnframes()
            comp_type = handle.getcomptype()
            frames = handle.readframes(frame_count)
    except wave.Error as exc:
        after_sha = sha256_file(path)
        return build_record(
            asset_id=asset_id or path.name,
            source_path=str(path.relative_to(root)).replace("\\", "/")
            if root.resolve() in path.resolve().parents
            else str(path),
            source_sha256=before_sha,
            source_bytes=before_bytes,
            codec="wav",
            duration_seconds=0.0,
            sample_rate_hz=1,
            channels=1,
            bit_depth=1,
            channel_layout="mono",
            decode_status="failed",
            canonical_pcm_sha256=None,
            frame_count=0,
            source_immutable=after_sha == before_sha,
            blocker={
                "code": "DECODE_FAILED_CORRUPT_OR_UNREADABLE",
                "detail": f"wave.open failed: {exc}",
            },
            library_authority=False,
            blocker_codes=["DECODE_FAILED_CORRUPT_OR_UNREADABLE"],
        )

    after_sha = sha256_file(path)
    source_immutable = after_sha == before_sha and path.stat().st_size == before_bytes
    rel_path = (
        str(path.relative_to(root)).replace("\\", "/")
        if root.resolve() in path.resolve().parents
        else str(path)
    )

    if comp_type != "NONE":
        return build_record(
            asset_id=asset_id or path.name,
            source_path=rel_path,
            source_sha256=before_sha,
            source_bytes=before_bytes,
            codec=str(comp_type),
            duration_seconds=0.0,
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            bit_depth=sample_width * 8,
            channel_layout=channel_layout_for(channels),
            decode_status="blocked",
            canonical_pcm_sha256=None,
            frame_count=0,
            source_immutable=source_immutable,
            blocker={
                "code": "UNSUPPORTED_CODEC_OR_CONTAINER",
                "detail": f"Compressed WAV comptype '{comp_type}' is unsupported in this slice.",
            },
            library_authority=False,
            blocker_codes=["UNSUPPORTED_CODEC_OR_CONTAINER"],
        )

    if sample_width not in {2, 4}:
        return build_record(
            asset_id=asset_id or path.name,
            source_path=rel_path,
            source_sha256=before_sha,
            source_bytes=before_bytes,
            codec="pcm_wav",
            duration_seconds=0.0,
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            bit_depth=sample_width * 8,
            channel_layout=channel_layout_for(channels),
            decode_status="blocked",
            canonical_pcm_sha256=None,
            frame_count=0,
            source_immutable=source_immutable,
            blocker={
                "code": "UNSUPPORTED_SAMPLE_FORMAT",
                "detail": f"Sample width {sample_width} bytes is unsupported; need 16-bit PCM or float32.",
            },
            library_authority=False,
            blocker_codes=["UNSUPPORTED_SAMPLE_FORMAT"],
        )

    expected_bytes = frame_count * channels * sample_width
    if len(frames) != expected_bytes:
        return build_record(
            asset_id=asset_id or path.name,
            source_path=rel_path,
            source_sha256=before_sha,
            source_bytes=before_bytes,
            codec="pcm_wav",
            duration_seconds=0.0,
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            bit_depth=sample_width * 8,
            channel_layout=channel_layout_for(channels),
            decode_status="failed",
            canonical_pcm_sha256=None,
            frame_count=0,
            source_immutable=source_immutable,
            blocker={
                "code": "DECODE_FAILED_CORRUPT_OR_UNREADABLE",
                "detail": (
                    f"Frame byte length mismatch: expected {expected_bytes}, got {len(frames)}."
                ),
            },
            library_authority=False,
            blocker_codes=["DECODE_FAILED_CORRUPT_OR_UNREADABLE"],
        )

    try:
        channel_samples = _frames_to_channels(
            frames,
            channels=channels,
            sample_width=sample_width,
            frame_count=frame_count,
        )
        pcm = pack_pcm_f32le(channel_samples)
    except (CanonicalDecodeError, struct.error) as exc:
        return build_record(
            asset_id=asset_id or path.name,
            source_path=rel_path,
            source_sha256=before_sha,
            source_bytes=before_bytes,
            codec="pcm_wav",
            duration_seconds=0.0,
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            bit_depth=sample_width * 8,
            channel_layout=channel_layout_for(channels),
            decode_status="failed",
            canonical_pcm_sha256=None,
            frame_count=0,
            source_immutable=source_immutable,
            blocker={
                "code": "DECODE_FAILED_CORRUPT_OR_UNREADABLE",
                "detail": f"PCM reshape failed: {exc}",
            },
            library_authority=False,
            blocker_codes=["DECODE_FAILED_CORRUPT_OR_UNREADABLE"],
        )

    duration = frame_count / float(sample_rate_hz) if sample_rate_hz else 0.0
    record = build_record(
        asset_id=asset_id or path.name,
        source_path=rel_path,
        source_sha256=before_sha,
        source_bytes=before_bytes,
        codec="pcm_s16le" if sample_width == 2 else "pcm_f32le",
        duration_seconds=duration,
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        bit_depth=sample_width * 8,
        channel_layout=channel_layout_for(channels),
        decode_status="pass",
        canonical_pcm_sha256=sha256_bytes(pcm),
        frame_count=frame_count,
        source_immutable=source_immutable,
        blocker=None,
        library_authority=False,
        blocker_codes=["LIBRARY_AUTHORITY_NOT_GRANTED"],
    )
    # Fixture/single-file pass proves decode integrity but never grants library authority.
    record["decision"]["status"] = "blocked"
    record["decode_status"] = "pass"
    return record


def synthesize_fixture_wav(path: Path, *, frames: int = 256, sample_rate_hz: int = 48000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate_hz)
        payload = bytearray()
        for index in range(frames):
            # Deterministic stereo ramp.
            left = int(max(-32767, min(32767, (index * 97) % 20000 - 10000)))
            right = int(max(-32767, min(32767, (index * 53) % 20000 - 10000)))
            payload.extend(struct.pack("<hh", left, right))
        handle.writeframes(bytes(payload))


def decode_fixture_record(root: Path, fixture_dir: Path) -> dict[str, Any]:
    wav_path = fixture_dir / "row070_tone_ramp.wav"
    if not wav_path.is_file():
        synthesize_fixture_wav(wav_path)
    record = decode_wav_file(root, wav_path, asset_id="fixture:row070_tone_ramp")
    validate_decode_record(root, record)
    return record


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admission = evaluate_row069_admission(root)
    blocker_codes = list(admission["blocker_codes"])
    for code in (
        "CANONICAL_DECODER_LIBRARY_RUNTIME_ABSENT",
        "FULL_LIBRARY_RUNTIME_RECORD_ABSENT",
        "SOURCE_IMMUTABILITY_FULL_LIBRARY_FINGERPRINT_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_dir = resolve_under(
        root,
        Path("Plan/Instructions/QA/Evidence/Wave64/fixtures/row070_canonical_decode"),
        "fixture_dir",
    )
    fixture_record = decode_fixture_record(root, fixture_dir)
    unsupported = build_record(
        asset_id="fixture:unsupported.mp3",
        source_path="Plan/Instructions/QA/Evidence/Wave64/fixtures/row070_canonical_decode/unsupported.mp3",
        source_sha256=sha256_bytes(b"not-a-real-mp3"),
        source_bytes=13,
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
        blocker={
            "code": "UNSUPPORTED_CODEC_OR_CONTAINER",
            "detail": "MP3 is unsupported in the stdlib WAV Row070 slice.",
        },
        library_authority=False,
        blocker_codes=["UNSUPPORTED_CODEC_OR_CONTAINER"],
    )
    validate_decode_record(root, unsupported)

    corrupt = build_record(
        asset_id="fixture:corrupt.wav",
        source_path="Plan/Instructions/QA/Evidence/Wave64/fixtures/row070_canonical_decode/corrupt.wav",
        source_sha256=sha256_bytes(b"RIFF....WAVEfmt "),
        source_bytes=16,
        codec="wav",
        duration_seconds=0.0,
        sample_rate_hz=1,
        channels=1,
        bit_depth=1,
        channel_layout="mono",
        decode_status="failed",
        canonical_pcm_sha256=None,
        frame_count=0,
        source_immutable=True,
        blocker={
            "code": "DECODE_FAILED_CORRUPT_OR_UNREADABLE",
            "detail": "Corrupt WAV fixture fails closed without canonical PCM hash.",
        },
        library_authority=False,
        blocker_codes=["DECODE_FAILED_CORRUPT_OR_UNREADABLE"],
    )
    validate_decode_record(root, corrupt)

    packet = {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-070_canonical_audio_decode",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "decoder_revision": DECODER_REVISION,
        "canonical_pcm_contract": dict(CANONICAL_PCM_CONTRACT),
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_ROW069_DEPENDENCY_AND_FULL_LIBRARY_DECODE_RUNTIME_ABSENT",
        "row069_admission": admission,
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "determinism_note": (
                "Fixture WAV decode proves frozen f32le hash identity and fail-closed "
                "unsupported/corrupt blockers only; it does not accept Row070 library completion."
            ),
            "records": [fixture_record, unsupported, corrupt],
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row070_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Row069 index authority, extend decode coverage beyond PCM WAV, "
                "reconcile every accepted index record to decode PASS or an exact blocker with "
                "output/failure-manifest hashes, and prove full-library source immutability."
            ),
        },
    }
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mode", choices=("library", "fixture", "file"), default="library")
    parser.add_argument("--input", default="")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    output = resolve_under(root, Path(args.output), "output")

    if args.mode == "file":
        if not args.input:
            raise CanonicalDecodeError("file_mode_requires_input")
        payload = decode_wav_file(root, Path(args.input))
        validate_decode_record(root, payload)
    elif args.mode == "fixture":
        fixture_dir = resolve_under(
            root,
            Path("Plan/Instructions/QA/Evidence/Wave64/fixtures/row070_canonical_decode"),
            "fixture_dir",
        )
        payload = decode_fixture_record(root, fixture_dir)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise CanonicalDecodeError("library_mode_must_remain_fail_closed_until_dependencies_pass")
        if payload.get("row_complete") is True:
            raise CanonicalDecodeError("library_mode_must_not_claim_row_complete")

    write_json(output, payload)
    status = payload.get("status") or payload.get("decode_status") or payload["decision"]["status"]
    print(json.dumps({"output": str(output), "status": status}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
