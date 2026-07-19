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
import os
import struct
import wave
from datetime import datetime, timezone
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
INDEX_REGISTRY = Path("Plan/10_REGISTRIES/audio_pack_functional_index_registry.json")
DECODER_REVISION = "wave64_row070_canonical_pcm_v0.1.0"
TRACKER_ID = "TRK-W64-070"
ITEM_ID = "ITEM-W64-070"
SCHEMA_VERSION = "1.0.0"
INDEX_STRATA_WAV_ROLES = (
    "body",
    "effects",
    "evaluation",
    "clothing",
    "voice",
    "furniture",
)
INDEX_STRATA_NON_WAV_EXTENSIONS = (".mp3", ".flac", ".ogg")
INDEX_STRATA_WAV_MIN_BYTES = 8_000
INDEX_STRATA_WAV_MAX_BYTES = 2_000_000

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


def _io_path(path: Path) -> Path:
    absolute = str(path.absolute())
    if os.name == "nt" and not absolute.startswith("\\\\?\\"):
        return Path("\\\\?\\" + absolute)
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with _io_path(path).open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def path_is_file(path: Path) -> bool:
    return _io_path(path).is_file()


def path_size(path: Path) -> int:
    return _io_path(path).stat().st_size


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
    if not path_is_file(path):
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
    before_bytes = path_size(path)
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
        with wave.open(str(_io_path(path)), "rb") as handle:
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
    source_immutable = after_sha == before_sha and path_size(path) == before_bytes
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


def load_active_index_locator(root: Path) -> dict[str, Any]:
    registry = load_json(resolve_under(root, INDEX_REGISTRY, "index_registry"))
    active = registry.get("active_index")
    if not isinstance(active, dict):
        raise CanonicalDecodeError("active_index_absent")
    runtime_rel = str(active.get("runtime_path") or "")
    if not runtime_rel:
        raise CanonicalDecodeError("active_index_runtime_path_absent")
    index_path = resolve_under(root, Path(runtime_rel), "active_index")
    if not index_path.is_file():
        raise CanonicalDecodeError(f"active_index_missing:{runtime_rel}")
    observed_sha = sha256_file(index_path)
    expected_sha = str(active.get("index_sha256") or "")
    if expected_sha and observed_sha != expected_sha:
        raise CanonicalDecodeError(
            f"active_index_sha256_mismatch:expected={expected_sha}:observed={observed_sha}"
        )
    source_root = Path(str(active.get("source_root") or ""))
    if not source_root:
        raise CanonicalDecodeError("active_index_source_root_absent")
    return {
        "registry_path": str(INDEX_REGISTRY).replace("\\", "/"),
        "runtime_path": runtime_rel.replace("\\", "/"),
        "index_path": index_path,
        "index_sha256": observed_sha,
        "index_bytes": index_path.stat().st_size,
        "source_root": source_root,
        "record_count": int(active.get("audio_file_count") or 0),
        "row069_acceptance": str(active.get("row069_acceptance") or ""),
        "library_authority": active.get("library_authority") is True,
    }


def _peek_wav_fmt_audio_format_and_bits(path: Path) -> tuple[int, int] | None:
    """Best-effort RIFF/WAVE fmt peek; returns (audio_format, bits_per_sample) or None."""
    try:
        with _io_path(path).open("rb") as handle:
            header = handle.read(12)
            if len(header) < 12 or header[0:4] != b"RIFF" or header[8:12] != b"WAVE":
                return None
            while True:
                chunk_header = handle.read(8)
                if len(chunk_header) < 8:
                    return None
                chunk_id = chunk_header[0:4]
                chunk_size = int.from_bytes(chunk_header[4:8], "little")
                if chunk_id == b"fmt ":
                    fmt = handle.read(min(chunk_size, 16))
                    if len(fmt) < 16:
                        return None
                    audio_format = int.from_bytes(fmt[0:2], "little")
                    bits_per_sample = int.from_bytes(fmt[14:16], "little")
                    return audio_format, bits_per_sample
                # Chunks are word-aligned.
                handle.seek(chunk_size + (chunk_size & 1), 1)
    except OSError:
        return None


def wav_is_supported_pcm(path: Path) -> bool:
    """Return True when stdlib wave can decode this path as 16-bit or float32 PCM."""
    if not path_is_file(path):
        return False
    peeked = _peek_wav_fmt_audio_format_and_bits(path)
    if peeked is not None:
        audio_format, bits_per_sample = peeked
        # 1=PCM, 3=IEEE float. Reject obvious unsupported bit depths early.
        if audio_format == 1 and bits_per_sample not in {16}:
            return False
        if audio_format == 3 and bits_per_sample not in {32}:
            return False
        if audio_format not in {1, 3}:
            return False
    try:
        with wave.open(str(_io_path(path)), "rb") as handle:
            if handle.getcomptype() != "NONE":
                return False
            if handle.getsampwidth() not in {2, 4}:
                return False
            if handle.getnframes() < 1 or handle.getnchannels() < 1:
                return False
    except wave.Error:
        return False
    return True


def select_accepted_index_strata(
    root: Path,
    *,
    wav_roles: tuple[str, ...] = INDEX_STRATA_WAV_ROLES,
    non_wav_extensions: tuple[str, ...] = INDEX_STRATA_NON_WAV_EXTENSIONS,
    wav_min_bytes: int = INDEX_STRATA_WAV_MIN_BYTES,
    wav_max_bytes: int = INDEX_STRATA_WAV_MAX_BYTES,
) -> dict[str, Any]:
    locator = load_active_index_locator(root)
    selected: list[dict[str, Any]] = []
    selected_paths: set[str] = set()
    role_hits: dict[str, dict[str, Any]] = {}
    non_wav_hits: dict[str, dict[str, Any]] = {}
    scanned = 0
    wav_probe_rejects = 0

    with locator["index_path"].open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            scanned += 1
            record = json.loads(line)
            relative_path = str(record.get("relative_path") or "").replace("\\", "/")
            if not relative_path or relative_path in selected_paths:
                continue
            extension = str(record.get("extension") or Path(relative_path).suffix).lower()
            absolute = Path(str(record.get("absolute_path") or ""))
            if not absolute:
                absolute = locator["source_root"] / relative_path
            bytes_count = int(record.get("bytes") or 0)
            role = str(record.get("role") or "")
            candidate = {
                "relative_path": relative_path,
                "absolute_path": str(absolute),
                "extension": extension,
                "role": role,
                "event_type": str(record.get("event_type") or ""),
                "duration_band": str(record.get("duration_band") or ""),
                "channels": record.get("channels"),
                "bytes": bytes_count,
                "sha256": str(record.get("sha256") or ""),
                "sample_rate_hz": record.get("sample_rate_hz"),
                "duration_seconds": record.get("duration_seconds"),
            }

            if extension == ".wav" and role in wav_roles and role not in role_hits:
                if wav_min_bytes <= bytes_count <= wav_max_bytes and path_is_file(absolute):
                    if not wav_is_supported_pcm(absolute):
                        wav_probe_rejects += 1
                        continue
                    role_hits[role] = candidate
                    selected.append(candidate)
                    selected_paths.add(relative_path)
            elif (
                extension in non_wav_extensions
                and extension not in non_wav_hits
                and path_is_file(absolute)
            ):
                non_wav_hits[extension] = candidate
                selected.append(candidate)
                selected_paths.add(relative_path)

            if len(role_hits) == len(wav_roles) and len(non_wav_hits) == len(non_wav_extensions):
                break

    return {
        "locator": {
            "registry_path": locator["registry_path"],
            "runtime_path": locator["runtime_path"],
            "index_sha256": locator["index_sha256"],
            "index_bytes": locator["index_bytes"],
            "source_root": str(locator["source_root"]),
            "record_count": locator["record_count"],
            "row069_acceptance": locator["row069_acceptance"],
            "library_authority": locator["library_authority"],
        },
        "scanned_records": scanned,
        "wav_probe_rejects": wav_probe_rejects,
        "selected": selected,
        "wav_roles_selected": sorted(role_hits),
        "non_wav_extensions_selected": sorted(non_wav_hits),
        "selection_complete_for_targets": (
            len(role_hits) == len(wav_roles) and len(non_wav_hits) == len(non_wav_extensions)
        ),
    }


def run_bounded_index_strata_decode(root: Path) -> dict[str, Any]:
    admission = evaluate_row069_admission(root)
    if not admission.get("dependency_satisfied"):
        raise CanonicalDecodeError("index_strata_requires_row069_admission")

    selection = select_accepted_index_strata(root)
    decode_records: list[dict[str, Any]] = []
    for candidate in selection["selected"]:
        absolute = Path(candidate["absolute_path"])
        asset_id = f"index:{candidate['relative_path']}"
        record = decode_wav_file(root, absolute, asset_id=asset_id)
        validate_decode_record(root, record)
        # Bind retained-index identity; never claim library authority from a strata sample.
        record["index_binding"] = {
            "relative_path": candidate["relative_path"],
            "retained_sha256": candidate["sha256"],
            "retained_bytes": candidate["bytes"],
            "role": candidate["role"],
            "event_type": candidate["event_type"],
            "duration_band": candidate["duration_band"],
            "source_sha256_matches_index": record.get("source_sha256") == candidate["sha256"],
            "source_bytes_match_index": record.get("source_bytes") == candidate["bytes"],
        }
        decode_records.append(record)

    decode_pass = sum(1 for record in decode_records if record["decode_status"] == "pass")
    decode_blocked = sum(1 for record in decode_records if record["decode_status"] == "blocked")
    decode_failed = sum(1 for record in decode_records if record["decode_status"] == "failed")
    immutable_pass = all(
        record.get("source_immutable") is True for record in decode_records
    )
    identity_pass = all(
        (record.get("index_binding") or {}).get("source_sha256_matches_index") is True
        and (record.get("index_binding") or {}).get("source_bytes_match_index") is True
        for record in decode_records
    )

    return {
        "schema_version": 1,
        "evidence_id": "W64-ROW070-ACCEPTED-INDEX-STRATA-BOUNDED-DECODE-20260719",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "authority": "accepted_index_strata_bounded",
        "library_authority": False,
        "row_complete": False,
        "proof_tier": "RUNTIME_PASS_BOUNDED",
        "row069_admission": admission,
        "selection": {
            "scanned_records": selection["scanned_records"],
            "wav_probe_rejects": selection.get("wav_probe_rejects", 0),
            "selected_count": len(selection["selected"]),
            "wav_roles_selected": selection["wav_roles_selected"],
            "non_wav_extensions_selected": selection["non_wav_extensions_selected"],
            "selection_complete_for_targets": selection["selection_complete_for_targets"],
            "locator": selection["locator"],
            "selected_compact": [
                {
                    "relative_path": item["relative_path"],
                    "extension": item["extension"],
                    "role": item["role"],
                    "event_type": item["event_type"],
                    "duration_band": item["duration_band"],
                    "channels": item["channels"],
                    "bytes": item["bytes"],
                    "sha256": item["sha256"],
                }
                for item in selection["selected"]
            ],
        },
        "counts": {
            "sources_attempted": len(decode_records),
            "decode_pass": decode_pass,
            "decode_blocked": decode_blocked,
            "decode_failed": decode_failed,
            "source_immutable_all": immutable_pass,
            "index_identity_all": identity_pass,
        },
        "decode_records": decode_records,
        "decode_pass_records_compact": [
            {
                "asset_id": record["asset_id"],
                "decode_status": record["decode_status"],
                "codec": record["codec"],
                "canonical_pcm_sha256": record["canonical_pcm_sha256"],
                "source_sha256": record["source_sha256"],
                "source_bytes": record["source_bytes"],
                "source_immutable": record["source_immutable"],
                "channels": record["channels"],
                "sample_rate_hz": record["sample_rate_hz"],
                "duration_seconds": record["duration_seconds"],
                "role": (record.get("index_binding") or {}).get("role"),
                "event_type": (record.get("index_binding") or {}).get("event_type"),
            }
            for record in decode_records
            if record["decode_status"] == "pass"
        ],
        "exact_blockers_compact": [
            {
                "asset_id": record["asset_id"],
                "decode_status": record["decode_status"],
                "blocker": record.get("blocker"),
                "role": (record.get("index_binding") or {}).get("role"),
                "extension": Path(str((record.get("index_binding") or {}).get("relative_path") or "")).suffix.lower(),
            }
            for record in decode_records
            if record["decode_status"] != "pass"
        ],
        "explicit_non_claims": [
            "COMPLETE",
            "library_authority",
            "full_library_decode",
            "product_completion",
            "row070_acceptance",
        ],
    }


def build_library_blocker_packet(
    root: Path,
    *,
    bounded_live_pcm_runtime: dict[str, Any] | None = None,
    index_strata_runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    admission = evaluate_row069_admission(root)
    blocker_codes = list(admission["blocker_codes"])
    for code in (
        "FULL_LIBRARY_RUNTIME_RECORD_ABSENT",
        "SOURCE_IMMUTABILITY_FULL_LIBRARY_FINGERPRINT_ABSENT",
        "NON_WAV_CODEC_COVERAGE_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)
    if not (
        index_strata_runtime
        and int((index_strata_runtime.get("counts") or {}).get("decode_pass") or 0) > 0
    ):
        if "CANONICAL_DECODER_LIBRARY_RUNTIME_ABSENT" not in blocker_codes:
            blocker_codes.append("CANONICAL_DECODER_LIBRARY_RUNTIME_ABSENT")

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

    strata = index_strata_runtime
    bounded = bounded_live_pcm_runtime
    strata_pass = int((strata or {}).get("counts", {}).get("decode_pass") or 0)
    bounded_pass = int((bounded or {}).get("decode_pass") or 0)

    if admission.get("dependency_satisfied") and strata_pass > 0:
        status = "HOLD_FULL_LIBRARY_DECODE_WITH_ACCEPTED_INDEX_STRATA_BOUNDED_RUNTIME"
        bounded_runtime_label = "RUNTIME_PASS_BOUNDED"
        safe_next = (
            "Expand accepted-index decode from strata sample toward full retained-index "
            "coverage (decode PASS or exact blocker per record), add non-WAV decoder "
            "coverage beyond exact blockers, and prove full-library source immutability "
            "before Row070 acceptance. Do not claim COMPLETE without full-library runtime."
        )
    elif admission.get("dependency_satisfied"):
        status = "HOLD_FULL_LIBRARY_DECODE_RUNTIME_ABSENT"
        bounded_runtime_label = "RUNTIME_PASS_BOUNDED" if bounded_pass > 0 else "STATIC_PASS"
        safe_next = (
            "Extend decode coverage across accepted Row069 index strata, reconcile every "
            "accepted index record to decode PASS or an exact blocker with "
            "output/failure-manifest hashes, and prove full-library source immutability "
            "before Row070 acceptance."
        )
    else:
        status = "HOLD_ROW069_DEPENDENCY_AND_FULL_LIBRARY_DECODE_RUNTIME_ABSENT"
        bounded_runtime_label = "RUNTIME_PASS_BOUNDED" if bounded_pass > 0 else "STATIC_PASS"
        safe_next = (
            "Accept Row069 index authority, extend decode coverage beyond PCM WAV, "
            "reconcile every accepted index record to decode PASS or an exact blocker with "
            "output/failure-manifest hashes, and prove full-library source immutability."
        )

    packet: dict[str, Any] = {
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
        "highest_proof_tier_achieved": "RUNTIME_PASS_BOUNDED"
        if (strata_pass > 0 or bounded_pass > 0)
        else "STATIC_PASS",
        "status": status,
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
            "bounded_runtime": bounded_runtime_label,
            "safe_next_action": safe_next,
        },
    }
    if bounded is not None:
        packet["bounded_live_pcm_runtime"] = bounded
    if strata is not None:
        packet["accepted_index_strata_runtime"] = {
            "authority": strata.get("authority"),
            "proof_tier": strata.get("proof_tier"),
            "library_authority": False,
            "sources_attempted": (strata.get("counts") or {}).get("sources_attempted"),
            "decode_pass": (strata.get("counts") or {}).get("decode_pass"),
            "decode_blocked": (strata.get("counts") or {}).get("decode_blocked"),
            "decode_failed": (strata.get("counts") or {}).get("decode_failed"),
            "wav_roles_selected": (strata.get("selection") or {}).get("wav_roles_selected"),
            "non_wav_extensions_selected": (strata.get("selection") or {}).get(
                "non_wav_extensions_selected"
            ),
            "index_sha256": ((strata.get("selection") or {}).get("locator") or {}).get(
                "index_sha256"
            ),
            "summary_path": strata.get("summary_path"),
            "summary_sha256": strata.get("summary_sha256"),
            "summary_bytes": strata.get("summary_bytes"),
            "receipt_path": strata.get("receipt_path"),
            "receipt_sha256": strata.get("receipt_sha256"),
        }
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument(
        "--mode",
        choices=("library", "fixture", "file", "index-strata"),
        default="library",
    )
    parser.add_argument("--input", default="")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    parser.add_argument(
        "--bounded-live-summary",
        default="",
        help="Optional prior bounded live PCM summary JSON to embed in library evidence.",
    )
    parser.add_argument(
        "--index-strata-receipt",
        default="",
        help="Optional index-strata runtime receipt JSON to embed in library evidence.",
    )
    parser.add_argument(
        "--write-index-strata-receipt",
        default="",
        help="When mode=index-strata, write full receipt JSON to this path.",
    )
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
    elif args.mode == "index-strata":
        payload = run_bounded_index_strata_decode(root)
        if args.write_index_strata_receipt:
            receipt_path = resolve_under(
                root, Path(args.write_index_strata_receipt), "index_strata_receipt"
            )
            write_json(receipt_path, payload)
            # Hash/path metadata live on the caller-facing payload only (not self-hashed).
            payload = dict(payload)
            payload["receipt_path"] = str(receipt_path.relative_to(root)).replace("\\", "/")
            payload["receipt_sha256"] = sha256_file(receipt_path)
            payload["receipt_bytes"] = receipt_path.stat().st_size
    else:
        bounded = None
        strata = None
        if args.bounded_live_summary:
            bounded_path = resolve_under(
                root, Path(args.bounded_live_summary), "bounded_live_summary"
            )
            bounded_payload = load_json(bounded_path)
            bounded = {
                "authority": "bounded_non_library",
                "decode_non_pass": int((bounded_payload.get("counts") or {}).get("decode_non_pass") or 0),
                "decode_pass": int((bounded_payload.get("counts") or {}).get("decode_pass") or 0),
                "library_authority": False,
                "proof_tier": "RUNTIME_PASS_BOUNDED",
                "sources_attempted": int(
                    (bounded_payload.get("counts") or {}).get("sources_attempted") or 0
                ),
                "summary_path": str(bounded_path.relative_to(root)).replace("\\", "/"),
                "summary_sha256": sha256_file(bounded_path),
                "summary_bytes": bounded_path.stat().st_size,
            }
        if args.index_strata_receipt:
            strata_path = resolve_under(
                root, Path(args.index_strata_receipt), "index_strata_receipt"
            )
            strata = load_json(strata_path)
            strata["receipt_path"] = str(strata_path.relative_to(root)).replace("\\", "/")
            strata["receipt_sha256"] = sha256_file(strata_path)
            strata["receipt_bytes"] = strata_path.stat().st_size
        payload = build_library_blocker_packet(
            root,
            bounded_live_pcm_runtime=bounded,
            index_strata_runtime=strata,
        )
        if payload["decision"]["status"] != "blocked":
            raise CanonicalDecodeError("library_mode_must_remain_fail_closed_until_dependencies_pass")
        if payload.get("row_complete") is True:
            raise CanonicalDecodeError("library_mode_must_not_claim_row_complete")
        if "ROW069_DEPENDENCY_NOT_ACCEPTED" in payload.get("blocker_codes", []):
            # Library mode may still emit when admission is held; never silently drop it.
            pass

    write_json(output, payload)
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    status = (
        payload.get("status")
        or payload.get("decode_status")
        or decision.get("status")
        or payload.get("proof_tier")
        or "ok"
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "status": status,
                "counts": payload.get("counts"),
                "proof_tier": payload.get("proof_tier") or payload.get("highest_proof_tier_achieved"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
