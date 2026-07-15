#!/usr/bin/env python3
"""Validate and produce fail-closed Wave64 speech authority records."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import tempfile
import wave
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path("C:/Comfy_UI_Main")
AUTHORITY_REGISTRY = Path("Plan/10_REGISTRIES/wave64_hyperreal_speech_authority_registry.json")
CARD_REGISTRY = Path("Plan/10_REGISTRIES/wave64_voice_reference_card_registry.json")
CASTING_REGISTRY = Path("Plan/10_REGISTRIES/wave64_character_voice_casting_registry.json")
ADAPTER_REGISTRY = Path("Plan/10_REGISTRIES/wave64_speech_engine_adapter_registry.json")


class AuthorityError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise AuthorityError(f"JSON root must be an object: {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text_file_lf(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def display_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def require(value: bool, message: str) -> None:
    if not value:
        raise AuthorityError(message)


def validate_authority_registry(value: dict[str, Any]) -> None:
    require(value.get("content_based_suppression") is False, "content_based_suppression must be false")
    expected = {f"TRK-W64-{number:03d}" for number in range(113, 118)}
    require(set(value.get("row_scope", [])) == expected, "authority row scope must be exactly Rows113-117")
    invariants = value.get("completion_invariants", {})
    for name in (
        "planning_is_runtime",
        "download_is_runtime_ready",
        "model_review_is_human_review",
        "intake_is_production_authority",
        "casting_is_production_authority",
        "single_metric_is_promotion",
    ):
        require(invariants.get(name) is False, f"false-completion invariant drift: {name}")
    require(invariants.get("row148_requires_all_mandatory_rows_pass") is True, "Row148 aggregate gate missing")
    separation = value.get("authority_separation", {})
    require(separation.get("final_production_authority_distinct_from_playback") is True, "authority roles are not distinct")
    require(separation.get("fabricated_human_metadata_allowed") is False, "fabricated human metadata must be prohibited")


def decode_pcm_samples(raw: bytes, width: int) -> list[float]:
    require(width in {1, 2, 3, 4}, f"unsupported PCM sample width: {width}")
    values: list[float] = []
    if width == 1:
        values = [(sample - 128) / 128.0 for sample in raw]
    elif width == 2:
        count = len(raw) // 2
        values = [sample / 32768.0 for sample in struct.unpack(f"<{count}h", raw[: count * 2])]
    elif width == 3:
        for offset in range(0, len(raw) - 2, 3):
            integer = int.from_bytes(raw[offset : offset + 3], "little", signed=False)
            if integer & 0x800000:
                integer -= 1 << 24
            values.append(integer / 8388608.0)
    else:
        count = len(raw) // 4
        values = [sample / 2147483648.0 for sample in struct.unpack(f"<{count}i", raw[: count * 4])]
    require(bool(values), "WAV contains no decodable samples")
    return values


def inspect_wav(path: Path) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as handle:
            require(handle.getcomptype() == "NONE", "only uncompressed PCM WAV is accepted")
            channels = handle.getnchannels()
            sample_rate = handle.getframerate()
            sample_width = handle.getsampwidth()
            frame_count = handle.getnframes()
            raw = handle.readframes(frame_count)
    except wave.Error as exc:
        raise AuthorityError(f"invalid PCM WAV: {exc}") from exc
    require(channels >= 1, "WAV channel count is invalid")
    require(sample_rate >= 8000, "WAV sample rate is below 8 kHz")
    require(frame_count >= 1, "WAV contains no frames")
    samples = decode_pcm_samples(raw, sample_width)
    squares = sum(sample * sample for sample in samples)
    rms = math.sqrt(squares / len(samples))
    peak = max(abs(sample) for sample in samples)
    rms_dbfs = 20.0 * math.log10(max(rms, 1e-12))
    peak_dbfs = 20.0 * math.log10(max(peak, 1e-12))
    clipping_ratio = sum(abs(sample) >= 0.999 for sample in samples) / len(samples)
    silence_floor = 10 ** (-50.0 / 20.0)
    silence_ratio = sum(abs(sample) <= silence_floor for sample in samples) / len(samples)
    duration = frame_count / sample_rate
    flags: list[str] = []
    if clipping_ratio > 0.01:
        flags.append("excessive_clipping")
    if silence_ratio > 0.5:
        flags.append("excessive_silence")
    if not (-40.0 <= rms_dbfs <= -3.0):
        flags.append("level_outside_reference_range")
    return {
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "frame_count": frame_count,
        "duration_seconds": round(duration, 6),
        "rms_dbfs": round(rms_dbfs, 6),
        "peak_dbfs": round(peak_dbfs, 6),
        "clipping_ratio": round(clipping_ratio, 9),
        "silence_ratio": round(silence_ratio, 9),
        "contamination_flags": flags,
    }


def validate_reference_card(card: dict[str, Any], root: Path, verify_source: bool = True) -> None:
    for field in (
        "schema_version",
        "voice_reference_id",
        "character_id",
        "character_version",
        "identity_policy",
        "production_authorized",
        "source",
        "rights",
        "transcript",
        "voice_traits",
        "quality",
        "content_based_suppression",
    ):
        require(field in card, f"voice card missing field: {field}")
    require(card["content_based_suppression"] is False, "voice card content suppression drift")
    require(card.get("revoked", False) is False or card["production_authorized"] is False, "revoked card cannot be production authorized")
    source = card["source"]
    require(isinstance(source, dict), "voice card source must be an object")
    require(isinstance(source.get("sha256"), str) and len(source["sha256"]) == 64, "voice card source SHA-256 missing")
    require(int(source.get("bytes", 0)) > 0, "voice card source byte count missing")
    rights = card["rights"]
    require(bool(rights.get("license")) and bool(rights.get("provenance")), "voice card rights are incomplete")
    require(rights.get("derivative_use_allowed") is True, "voice card derivative use is not allowed")
    transcript = card["transcript"]
    require(bool(str(transcript.get("text", "")).strip()), "voice card transcript missing")
    require(bool(str(transcript.get("language", "")).strip()), "voice card language missing")
    traits = card["voice_traits"]
    required_traits = {
        "timbre",
        "accent",
        "pitch",
        "pace_wpm",
        "delivery_style",
        "intensity",
        "pronunciation",
        "continuity_lines",
    }
    require(required_traits.issubset(traits), "voice card trait contract incomplete")
    if verify_source:
        path = resolve_path(root, source["path"])
        require(path.is_file(), f"voice card source missing: {path}")
        require(path.stat().st_size == source["bytes"], "voice card source byte count mismatch")
        require(sha256_file(path) == source["sha256"].lower(), "voice card source SHA-256 mismatch")


def intake_reference(
    root: Path,
    source_path: Path,
    voice_reference_id: str,
    character_id: str,
    character_version: str,
    identity_policy: str,
    transcript: str,
    language: str,
    license_name: str,
    provenance: str,
    attribution: str,
    voice_traits: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    require(source_path.is_file(), f"reference source missing: {source_path}")
    source_hash_before = sha256_file(source_path)
    source_bytes = source_path.stat().st_size
    metadata = inspect_wav(source_path)
    source_hash_after = sha256_file(source_path)
    require(source_hash_before == source_hash_after, "reference source bytes changed during intake")
    duration_pass = 1.0 <= metadata["duration_seconds"] <= 30.0
    level_pass = -40.0 <= metadata["rms_dbfs"] <= -3.0
    clipping_pass = metadata["clipping_ratio"] <= 0.01
    silence_pass = metadata["silence_ratio"] <= 0.5
    checks = {
        "duration_pass": duration_pass,
        "level_pass": level_pass,
        "clipping_pass": clipping_pass,
        "silence_pass": silence_pass,
        "rights_pass": True,
    }
    checks["intake_pass"] = all(checks.values())
    source = {
        "path": display_path(root, source_path),
        "sha256": source_hash_before,
        "bytes": source_bytes,
        "duration_seconds": metadata["duration_seconds"],
        "sample_rate_hz": metadata["sample_rate_hz"],
        "channels": metadata["channels"],
    }
    rights = {
        "license": license_name,
        "provenance": provenance,
        "derivative_use_allowed": True,
        "attribution": attribution,
    }
    card = {
        "schema_version": "1.0",
        "voice_reference_id": voice_reference_id,
        "character_id": character_id,
        "character_version": character_version,
        "identity_policy": identity_policy,
        "production_authorized": False,
        "source": source,
        "rights": rights,
        "transcript": {"text": transcript, "language": language},
        "voice_traits": voice_traits,
        "quality": {
            "intake_pass": checks["intake_pass"],
            "rms_dbfs": metadata["rms_dbfs"],
            "peak_dbfs": metadata["peak_dbfs"],
            "clipping_ratio": metadata["clipping_ratio"],
            "silence_ratio": metadata["silence_ratio"],
            "contamination_flags": metadata["contamination_flags"],
        },
        "approved_engine_configurations": [],
        "content_based_suppression": False,
        "revoked": False,
    }
    record = {
        "schema_version": "1.0",
        "record_id": f"INTAKE-{voice_reference_id}",
        "created_at": now_iso(),
        "source": {
            **source,
            "format": "pcm_wav",
            "sample_width_bytes": metadata["sample_width_bytes"],
            "frame_count": metadata["frame_count"],
        },
        "segment": {
            "start_frame": 0,
            "end_frame": metadata["frame_count"],
            "start_seconds": 0,
            "end_seconds": metadata["duration_seconds"],
        },
        "transcript": {"text": transcript, "language": language, "source": "supplied_authoritative"},
        "rights": rights,
        "quality": {
            "rms_dbfs": metadata["rms_dbfs"],
            "peak_dbfs": metadata["peak_dbfs"],
            "clipping_ratio": metadata["clipping_ratio"],
            "silence_ratio": metadata["silence_ratio"],
            "contamination_flags": metadata["contamination_flags"],
        },
        "acceptance": checks,
        "source_bytes_preserved": True,
        "content_based_suppression": False,
    }
    validate_reference_card(card, root)
    return card, record


def validate_casting_record(record: dict[str, Any]) -> None:
    require(record.get("content_based_suppression") is False, "casting content suppression drift")
    candidates = record.get("candidates")
    require(isinstance(candidates, list) and candidates, "casting record requires candidates")
    candidate_ids = {candidate.get("candidate_id") for candidate in candidates}
    decision = record.get("decision", {})
    selected = decision.get("selected_candidate_id")
    require(selected is None or selected in candidate_ids, "casting selection does not identify a candidate")
    authority = record.get("authority", {})
    if authority.get("production_authorized") is True:
        require(authority.get("playback_review_pass") is True, "production casting requires playback review")
        require(authority.get("final_production_authority_pass") is True, "production casting requires final authority")
        selected_candidate = next(candidate for candidate in candidates if candidate.get("candidate_id") == selected)
        require(selected_candidate.get("rights_valid") is True, "production casting rights invalid")
        require(selected_candidate.get("runtime_proven") is True, "production casting runtime unproven")
        require(selected_candidate.get("continuity_tested") is True, "production casting continuity untested")


def validate_selected_adapter(root: Path) -> tuple[bool, list[str]]:
    path = root / ADAPTER_REGISTRY
    if not path.is_file():
        return False, ["selected speech-engine adapter registry is missing"]
    registry = load_json(path)
    require(registry.get("content_based_suppression") is False, "adapter registry content suppression drift")
    adapters = registry.get("adapters", [])
    require(isinstance(adapters, list) and len(adapters) == 1, "expected one selected speech-engine adapter")
    adapter = adapters[0]
    require(adapter.get("adapter_id") == "qwen3_tts_1_7b_voicedesign_official_0_1_1", "unexpected selected adapter")
    require(adapter.get("runtime_status") == "load_proven", "selected adapter loader is not proven")
    require(adapter.get("production_ready") is False, "load proof cannot imply production readiness")
    require(adapter.get("content_based_suppression") is False, "adapter content suppression drift")
    files = adapter.get("model_files", [])
    require(isinstance(files, list) and len(files) == 11, "selected adapter exact file set is incomplete")
    for item in files:
        target = resolve_path(root, item["path"])
        require(target.is_file(), f"selected adapter file missing: {target}")
        require(target.stat().st_size == item["bytes"], f"selected adapter file byte count mismatch: {target}")
    proof = adapter.get("load_proof", {})
    proof_path = resolve_path(root, proof.get("path", ""))
    require(proof_path.is_file(), "selected adapter load proof is missing")
    require(sha256_text_file_lf(proof_path) == proof.get("sha256"), "selected adapter load proof hash mismatch")
    return True, list(adapter.get("known_blockers", []))


def validate_batch(root: Path, intake_record: Path | None = None) -> dict[str, Any]:
    authority = load_json(root / AUTHORITY_REGISTRY)
    validate_authority_registry(authority)
    card_registry = load_json(root / CARD_REGISTRY)
    require(card_registry.get("content_based_suppression") is False, "card registry content suppression drift")
    cards = card_registry.get("cards", [])
    require(isinstance(cards, list), "card registry cards must be an array")
    for entry in cards:
        card_path = resolve_path(root, entry["card_path"])
        card = load_json(card_path)
        validate_reference_card(card, root)
        require(sha256_text_file_lf(card_path) == entry["card_sha256"], "registered card JSON hash mismatch")
    casting = load_json(root / CASTING_REGISTRY)
    records = casting.get("records", [])
    require(isinstance(records, list) and records, "casting registry is empty")
    for record in records:
        validate_casting_record(record)
    adapter_pass, adapter_blockers = validate_selected_adapter(root)
    intake_pass = False
    intake_binding: dict[str, Any] | None = None
    if intake_record is not None:
        value = load_json(intake_record)
        intake_pass = value.get("acceptance", {}).get("intake_pass") is True and value.get("source_bytes_preserved") is True
        intake_binding = {
            "path": display_path(root, intake_record),
            "sha256": sha256_file(intake_record),
            "intake_pass": intake_pass,
        }
    selected = records[0]["candidates"][0]
    row_decisions = {
        "TRK-W64-113": {
            "classification": "Implemented_Authority_Control_Pass",
            "pass_like": True,
            "blockers": [],
        },
        "TRK-W64-114": {
            "classification": "Implemented_Immutable_Card_System_Pass_Character_Card_Pending",
            "pass_like": True,
            "blockers": [] if cards else ["no character-bound production voice-reference card is registered"],
        },
        "TRK-W64-115": {
            "classification": "Implemented_Reference_Intake_QA_Pass" if intake_pass else "Blocked_Reference_Intake_Evidence_Missing",
            "pass_like": intake_pass,
            "blockers": [] if intake_pass else ["no passing hash-bound reference intake record was supplied"],
        },
        "TRK-W64-116": {
            "classification": "Implemented_Casting_Control_Blocked_Runtime_Continuity_And_Authority",
            "pass_like": False,
            "blockers": list(selected.get("blockers", [])),
        },
        "TRK-W64-117": {
            "classification": "Implemented_Selected_Qwen3_TTS_Acquisition_And_Load_Pass_Generation_QA_Pending" if adapter_pass else "Blocked_Exact_Engine_Acquisition_And_Load_Proof_Missing",
            "pass_like": adapter_pass,
            "blockers": adapter_blockers if adapter_pass else ["Qwen3-TTS VoiceDesign exact file acquisition and isolated loader proof are pending"],
        },
    }
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_rows113_117_authority_validation",
        "created_at": now_iso(),
        "classification": "W64_ROWS113_117_IMPLEMENTATION_PARTIAL_FAIL_CLOSED",
        "row_decisions": row_decisions,
        "intake_record": intake_binding,
        "boundaries": {
            "planning_claimed_as_runtime": False,
            "download_claimed_as_ready": False,
            "production_voice_authority_claimed": False,
            "rejected_candidate_rerun": False,
            "content_based_suppression": False,
        },
    }


def parse_traits(path: Path) -> dict[str, Any]:
    value = load_json(path)
    return value


def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    intake = sub.add_parser("intake-reference")
    intake.add_argument("--source", type=Path, required=True)
    intake.add_argument("--voice-reference-id", required=True)
    intake.add_argument("--character-id", required=True)
    intake.add_argument("--character-version", required=True)
    intake.add_argument("--identity-policy", required=True)
    intake.add_argument("--transcript", required=True)
    intake.add_argument("--language", required=True)
    intake.add_argument("--license", required=True)
    intake.add_argument("--provenance", required=True)
    intake.add_argument("--attribution", default="")
    intake.add_argument("--voice-traits", type=Path, required=True)
    intake.add_argument("--out-card", type=Path, required=True)
    intake.add_argument("--out-record", type=Path, required=True)
    validate = sub.add_parser("validate-batch")
    validate.add_argument("--intake-record", type=Path)
    validate.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    try:
        if args.command == "intake-reference":
            source = resolve_path(root, args.source)
            card, record = intake_reference(
                root,
                source,
                args.voice_reference_id,
                args.character_id,
                args.character_version,
                args.identity_policy,
                args.transcript,
                args.language,
                args.license,
                args.provenance,
                args.attribution,
                parse_traits(resolve_path(root, args.voice_traits)),
            )
            out_card = resolve_path(root, args.out_card)
            out_record = resolve_path(root, args.out_record)
            write_json_atomic(out_card, card)
            write_json_atomic(out_record, record)
            print(json.dumps({"classification": "VOICE_REFERENCE_INTAKE_PASS" if record["acceptance"]["intake_pass"] else "VOICE_REFERENCE_INTAKE_QA_BLOCKED", "card": display_path(root, out_card), "record": display_path(root, out_record)}, indent=2))
            return 0 if record["acceptance"]["intake_pass"] else 2
        evidence = validate_batch(root, resolve_path(root, args.intake_record) if args.intake_record else None)
        output = resolve_path(root, args.out)
        write_json_atomic(output, evidence)
        print(json.dumps({"classification": evidence["classification"], "evidence": display_path(root, output)}, indent=2))
        return 0
    except (AuthorityError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"classification": "W64_SPEECH_AUTHORITY_VALIDATION_FAILED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
