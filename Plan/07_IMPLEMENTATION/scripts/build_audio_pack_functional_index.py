#!/usr/bin/env python3
"""Build a resumable, hash-bound functional index for external audio assets.

Row069 authority slice: emit a durable exact failure manifest and before/after
source inventory fingerprints, plus retained-index byte-hash reconciliation and
full-library resume-replay scaffolding. Library acceptance remains fail-closed
until full-library reconcile/resume proofs pass; prerequisite Rows067/068 must
be accepted as dependency authority only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator
from mutagen import File as MutagenFile


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = PROJECT_ROOT / "Plan/08_SCHEMAS/audio_pack_functional_index_record.schema.json"
FAILURE_MANIFEST_SCHEMA_PATH = (
    PROJECT_ROOT / "Plan/08_SCHEMAS/audio_library_index_failure_manifest.schema.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-069_full_audio_library_index.json"
)
DEFAULT_SOURCE_ROOT = Path("F:/Len_Transfer/Audio_Downloads")
DEFAULT_RETAINED_INDEX_DIR = Path(
    "runtime_artifacts/audio_asset_indexes/audio_downloads_functional_20260715T095712-0500"
)
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg"}
INDEX_REVISION = "wave64_row069_audio_library_index_v0.1.0"
SCHEMA_VERSION = "1.0.0"
TRACKER_ID = "TRK-W64-069"
ITEM_ID = "ITEM-W64-069"
BYTE_HASH_SAMPLE_DEFAULT = 48


def _io_path(path: Path) -> Path:
    absolute = str(path.absolute())
    if os.name == "nt" and not absolute.startswith("\\\\?\\"):
        return Path("\\\\?\\" + absolute)
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with _io_path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _contains(text: str, values: tuple[str, ...]) -> bool:
    return any(value in text for value in values)


def _classify_event(relative_path: str) -> str:
    text = relative_path.lower().replace("_", " ").replace("-", " ")
    text = text.replace("opennsfw sfx", " ").replace("open nsfw sfx", " ")
    if "cv3 eval" in text or "dataset" in text or "librispeech" in text:
        return "evaluation_reference"
    if _contains(text, ("dialogue", "speech", "voice line", "narration")):
        return "dialogue"
    if _contains(text, ("moan", "gasp", "groan", "vocal", "reaction", "whisper", "scream", "laugh", "cry")):
        return "voice_reaction"
    if _contains(text, ("breath", "breathing", "exhale", "inhale")):
        return "breath"
    if _contains(text, ("cloth", "clothes", "clothing", "fabric", "leather", "latex", "zipper")):
        return "clothing_foley"
    if _contains(text, ("bed", "chair", "couch", "sofa", "mattress", "furniture", "table", "floorboard")):
        return "furniture_foley"
    if _contains(
        text,
        (
            "footstep", "step", "walk", "run", "body", "skin", "slap", "kiss", "rub", "squish",
            "cum", "wet", "suction", "penetration", "masturbation", "oral", "vaginal", "anal",
            "fapping", "boobs", "breast", "ass", "butt", "pussy", "cock", "dick",
        ),
    ):
        return "body_foley"
    if _contains(text, ("prop", "door", "glass", "metal", "wood", "plastic", "toy", "weapon", "tool")):
        return "prop_foley"
    if _contains(text, ("impact", "hit", "punch", "thud", "bang", "crash", "collision")):
        return "impact"
    if _contains(text, ("transition", "whoosh", "swoosh", "riser", "stinger")):
        return "transition_sfx"
    if _contains(text, ("ambience", "ambient", "atmosphere", "outdoor", "city", "forest", "rain", "wind")):
        return "ambience"
    if _contains(text, ("room tone", "roomtone")):
        return "room_tone"
    if _contains(text, ("music", "song", "bgm", "soundtrack", "melody")):
        return "music"
    if _contains(text, ("action", "movement", "motion", "sfx", "effect")):
        return "action_sfx"
    return "unclassified"


def _classify_material(relative_path: str) -> str:
    text = relative_path.lower()
    material_terms = (
        "skin", "fabric", "cloth", "leather", "latex", "metal", "wood", "glass",
        "plastic", "rubber", "water", "liquid", "fluid", "paper", "ceramic", "stone", "sand",
    )
    for term in material_terms:
        if term in text:
            return term
    return "unspecified"


def _role_for(event_type: str) -> str:
    return {
        "body_foley": "body",
        "clothing_foley": "clothing",
        "prop_foley": "prop",
        "furniture_foley": "furniture",
        "ambience": "ambience",
        "room_tone": "ambience",
        "music": "music",
        "dialogue": "voice",
        "voice_reaction": "voice",
        "breath": "voice",
        "evaluation_reference": "evaluation",
    }.get(event_type, "effects")


def _intensity(relative_path: str) -> str:
    text = relative_path.lower()
    if _contains(text, ("silent", "silence")):
        return "silent"
    if _contains(text, ("very soft", "very quiet", "tiny", "subtle")):
        return "very_low"
    if _contains(text, ("soft", "quiet", "light", "gentle", "slow")):
        return "low"
    if _contains(text, ("hard", "loud", "heavy", "strong", "intense", "fast")):
        return "high"
    if _contains(text, ("medium", "normal", "moderate")):
        return "medium"
    return "unknown"


def _duration_band(duration: float | None) -> str:
    if duration is None:
        return "unknown"
    if duration < 0.35:
        return "instant"
    if duration < 2.0:
        return "short"
    if duration < 10.0:
        return "medium"
    return "sustained"


def _attack(relative_path: str, event_type: str) -> str:
    text = relative_path.lower()
    if event_type in {"impact", "transition_sfx"} or _contains(text, ("snap", "click", "pop", "crack", "hit")):
        return "sharp_transient"
    if _contains(text, ("soft", "gentle", "rub", "brush", "rustle")):
        return "soft_transient"
    if event_type in {"ambience", "room_tone", "music", "evaluation_reference"}:
        return "sustained"
    if _contains(text, ("rise", "fade", "build")):
        return "gradual"
    return "unknown"


def _sync_class(event_type: str) -> str:
    if event_type == "evaluation_reference":
        return "evaluation_only"
    if event_type in {"impact", "body_foley", "prop_foley", "furniture_foley"}:
        return "frame_exact"
    if event_type in {"dialogue", "voice_reaction", "breath", "clothing_foley", "action_sfx", "transition_sfx"}:
        return "windowed"
    if event_type == "music":
        return "music_scene_phase"
    return "ambient_free"


def _room_suitability(relative_path: str, event_type: str) -> list[str]:
    text = relative_path.lower()
    rooms = [term for term in ("bedroom", "bathroom", "kitchen", "office", "hall", "outdoor", "studio") if term in text]
    if rooms:
        return rooms
    if event_type in {"ambience", "room_tone"}:
        return ["environment_specific_unspecified"]
    return ["dry_or_unspecified"]


def _license(relative_path: str) -> tuple[str, str]:
    text = relative_path.lower()
    if "open nsfw sfx" in text or "opennsfw sfx" in text:
        if "(cc0)" in text or "[cc0]" in text:
            return "CC0-1.0", "OpenNSFW Sound Pack | joao-janz"
        if "cc4.0 attribution" in text or "cc-by-4.0" in text:
            return "CC-BY-4.0", "OpenNSFW Sound Pack | joao-janz"
        return "open_nsfw_sfx_pack_terms", "OpenNSFW Sound Pack | joao-janz"
    if "cv3-eval" in text:
        return "dataset_specific_rights_preserved", "CV3-Eval upstream corpus metadata"
    return "source_package_license_requires_resolution", "Preserve source package attribution metadata"


def _audio_metadata(path: Path) -> tuple[float | None, str, int | None, int | None, list[str]]:
    defects: list[str] = []
    try:
        payload = MutagenFile(_io_path(path))
        if payload is None or not hasattr(payload, "info"):
            raise ValueError("unsupported_or_unrecognized_audio_container")
        info = payload.info
        duration = float(info.length) if getattr(info, "length", None) is not None else None
        sample_rate = int(info.sample_rate) if getattr(info, "sample_rate", None) else None
        channels = int(info.channels) if getattr(info, "channels", None) else None
        format_name = path.suffix.lower().lstrip(".")
        if duration is None or duration <= 0:
            defects.append("non_positive_or_missing_duration")
        if sample_rate is None:
            defects.append("missing_sample_rate")
        if channels is None:
            defects.append("missing_channel_count")
        elif channels > 2:
            defects.append("multichannel_requires_mix_policy")
        return duration, format_name, sample_rate, channels, defects
    except Exception as exc:
        defects.append(f"metadata_parse_failed:{type(exc).__name__}")
        return None, path.suffix.lower().lstrip(".") or "unknown", None, None, defects


def _record_for(path: Path, source_root: Path) -> dict[str, Any]:
    relative = path.relative_to(source_root).as_posix()
    duration, format_name, sample_rate, channels, defects = _audio_metadata(path)
    event_type = _classify_event(relative)
    license_name, attribution = _license(relative)
    lowered = relative.lower()
    if sample_rate is not None and sample_rate not in {16000, 22050, 24000, 32000, 44100, 48000, 88200, 96000, 192000}:
        defects.append("nonstandard_sample_rate")
    return {
        "relative_path": relative,
        "absolute_path": str(path.absolute()),
        "sha256": _sha256(path),
        "bytes": _io_path(path).stat().st_size,
        "extension": path.suffix.lower(),
        "duration_seconds": round(duration, 9) if duration is not None else None,
        "format": format_name,
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "event_type": event_type,
        "material": _classify_material(relative),
        "role": _role_for(event_type),
        "intensity_band": _intensity(relative),
        "duration_band": _duration_band(duration),
        "attack_characteristic": _attack(relative, event_type),
        "sync_class": _sync_class(event_type),
        "room_environment_suitability": _room_suitability(relative, event_type),
        "loopability": "declared_loop" if "loop" in lowered else ("candidate" if event_type in {"ambience", "room_tone", "music"} else "not_indicated"),
        "quality_defects": sorted(set(defects)),
        "license_classification": license_name,
        "attribution": attribution,
        "content_based_suppression": False,
    }


def _refresh_routing(record: dict[str, Any]) -> dict[str, Any]:
    relative = record["relative_path"]
    event_type = _classify_event(relative)
    license_name, attribution = _license(relative)
    record.update(
        {
            "event_type": event_type,
            "material": _classify_material(relative),
            "role": _role_for(event_type),
            "intensity_band": _intensity(relative),
            "duration_band": _duration_band(record.get("duration_seconds")),
            "attack_characteristic": _attack(relative, event_type),
            "sync_class": _sync_class(event_type),
            "room_environment_suitability": _room_suitability(relative, event_type),
            "loopability": "declared_loop" if "loop" in relative.lower() else ("candidate" if event_type in {"ambience", "room_tone", "music"} else "not_indicated"),
            "license_classification": license_name,
            "attribution": attribution,
            "content_based_suppression": False,
        }
    )
    return record


def _open_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS records ("
        "relative_path TEXT PRIMARY KEY, size INTEGER NOT NULL, "
        "mtime_ns INTEGER NOT NULL, payload TEXT NOT NULL)"
    )
    return connection


def _literal_audio_files(source_root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory, _, filenames in os.walk(source_root):
        base = Path(directory)
        for filename in filenames:
            path = base / filename
            if path.suffix.lower() in AUDIO_EXTENSIONS:
                paths.append(path)
    return sorted(paths, key=lambda path: path.relative_to(source_root).as_posix().casefold())


def build_source_inventory_fingerprint(source_root: Path, audio_files: list[Path] | None = None) -> dict[str, Any]:
    files = audio_files if audio_files is not None else _literal_audio_files(source_root)
    lines: list[str] = []
    extension_counts: Counter[str] = Counter()
    for path in files:
        relative = path.relative_to(source_root).as_posix()
        stat = _io_path(path).stat()
        lines.append(f"{relative}\t{stat.st_size}\t{stat.st_mtime_ns}")
        extension_counts[path.suffix.lower().lstrip(".")] += 1
    canonical = "\n".join(lines) + ("\n" if lines else "")
    return {
        "algorithm": "sha256_of_sorted_relative_path_size_mtime_ns_tsv",
        "discovered_audio_count": len(files),
        "extension_counts": dict(sorted(extension_counts.items())),
        "fingerprint_sha256": _sha256_text(canonical),
        "inventory_bytes": len(canonical.encode("utf-8")),
    }


def observe_source_inventory(source_root: Path) -> dict[str, Any]:
    if not source_root.is_dir():
        return {
            "source_root": str(source_root),
            "source_root_exists": False,
            "discovered_audio_count": None,
            "extension_counts": {},
            "inventory_fingerprint_sha256": None,
            "observation": "SOURCE_ROOT_ABSENT",
        }
    fingerprint = build_source_inventory_fingerprint(source_root)
    return {
        "source_root": str(source_root.resolve()),
        "source_root_exists": True,
        "discovered_audio_count": fingerprint["discovered_audio_count"],
        "extension_counts": fingerprint["extension_counts"],
        "inventory_fingerprint_sha256": fingerprint["fingerprint_sha256"],
        "observation": "COUNT_AND_PATH_SIZE_MTIME_FINGERPRINT_ONLY",
        "note": (
            "Walk-only inventory observation. Does not re-hash audio bytes or "
            "rebuild the retained production index."
        ),
    }


def _blocker_entry(
    *,
    relative_path: str,
    code: str,
    detail: str,
    size: int | None = None,
    mtime_ns: int | None = None,
) -> dict[str, Any]:
    return {
        "relative_path": relative_path,
        "code": code,
        "detail": detail,
        "bytes": size,
        "mtime_ns": mtime_ns,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def _validate_failure_manifest(manifest: dict[str, Any]) -> None:
    if not FAILURE_MANIFEST_SCHEMA_PATH.is_file():
        return
    schema = json.loads(FAILURE_MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda err: list(err.absolute_path))
    if errors:
        raise ValueError(f"failure manifest schema failed: {errors[0].message}")


def build_index(source_root: Path, output_dir: Path, *, resume: bool = False) -> dict[str, Any]:
    source_root = source_root.resolve()
    output_dir = output_dir.resolve()
    if not source_root.is_dir():
        raise ValueError(f"source root is not a directory: {source_root}")
    if output_dir.exists() and not resume:
        raise ValueError(f"output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "functional_index_state.sqlite3"
    connection = _open_database(state_path)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    audio_files = _literal_audio_files(source_root)
    fingerprint_before = build_source_inventory_fingerprint(source_root, audio_files)
    blockers: list[dict[str, Any]] = []
    try:
        for index, path in enumerate(audio_files, start=1):
            relative = path.relative_to(source_root).as_posix()
            try:
                stat = _io_path(path).stat()
            except OSError as exc:
                blockers.append(
                    _blocker_entry(
                        relative_path=relative,
                        code="INDEX_SOURCE_UNREADABLE",
                        detail=f"stat_failed:{type(exc).__name__}:{exc}",
                    )
                )
                continue
            if stat.st_size < 1:
                blockers.append(
                    _blocker_entry(
                        relative_path=relative,
                        code="INDEX_EMPTY_OR_UNREADABLE",
                        detail="audio file has zero bytes and cannot enter the functional index",
                        size=stat.st_size,
                        mtime_ns=stat.st_mtime_ns,
                    )
                )
                connection.execute("DELETE FROM records WHERE relative_path = ?", (relative,))
                continue
            cached = connection.execute(
                "SELECT size, mtime_ns FROM records WHERE relative_path = ?",
                (relative,),
            ).fetchone()
            if cached == (stat.st_size, stat.st_mtime_ns):
                if index % 100 == 0:
                    connection.commit()
                continue
            try:
                record = _record_for(path, source_root)
                errors = list(validator.iter_errors(record))
                if errors:
                    blockers.append(
                        _blocker_entry(
                            relative_path=relative,
                            code="INDEX_SCHEMA_FAILED",
                            detail=errors[0].message,
                            size=stat.st_size,
                            mtime_ns=stat.st_mtime_ns,
                        )
                    )
                    connection.execute("DELETE FROM records WHERE relative_path = ?", (relative,))
                    continue
                connection.execute(
                    "INSERT OR REPLACE INTO records(relative_path, size, mtime_ns, payload) VALUES (?, ?, ?, ?)",
                    (relative, stat.st_size, stat.st_mtime_ns, json.dumps(record, ensure_ascii=True, sort_keys=True)),
                )
            except OSError as exc:
                blockers.append(
                    _blocker_entry(
                        relative_path=relative,
                        code="INDEX_SOURCE_UNREADABLE",
                        detail=f"read_failed:{type(exc).__name__}:{exc}",
                        size=stat.st_size,
                        mtime_ns=stat.st_mtime_ns,
                    )
                )
                connection.execute("DELETE FROM records WHERE relative_path = ?", (relative,))
            except Exception as exc:
                blockers.append(
                    _blocker_entry(
                        relative_path=relative,
                        code="INDEX_RECORD_BUILD_FAILED",
                        detail=f"{type(exc).__name__}:{exc}",
                        size=stat.st_size,
                        mtime_ns=stat.st_mtime_ns,
                    )
                )
                connection.execute("DELETE FROM records WHERE relative_path = ?", (relative,))
            if index % 100 == 0:
                connection.commit()
        connection.commit()

        present = {path.relative_to(source_root).as_posix() for path in audio_files}
        for (relative,) in connection.execute("SELECT relative_path FROM records").fetchall():
            if relative not in present:
                connection.execute("DELETE FROM records WHERE relative_path = ?", (relative,))
        connection.commit()

        temp_handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=output_dir, delete=False)
        temp_path = Path(temp_handle.name)
        counters: dict[str, Counter[str]] = {
            key: Counter()
            for key in (
                "extension",
                "event_type",
                "material",
                "role",
                "intensity_band",
                "sync_class",
                "license_classification",
            )
        }
        hashes: Counter[str] = Counter()
        defects = 0
        total_bytes = 0
        indexed_count = 0
        try:
            with temp_handle:
                for (payload_text,) in connection.execute(
                    "SELECT payload FROM records ORDER BY relative_path COLLATE NOCASE"
                ):
                    payload = _refresh_routing(json.loads(payload_text))
                    errors = list(validator.iter_errors(payload))
                    if errors:
                        relative = str(payload.get("relative_path") or "unknown")
                        blockers.append(
                            _blocker_entry(
                                relative_path=relative,
                                code="INDEX_SCHEMA_FAILED",
                                detail=f"cached_record:{errors[0].message}",
                                size=payload.get("bytes"),
                            )
                        )
                        connection.execute("DELETE FROM records WHERE relative_path = ?", (relative,))
                        continue
                    temp_handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
                    indexed_count += 1
                    total_bytes += payload["bytes"]
                    hashes[payload["sha256"]] += 1
                    if payload["quality_defects"]:
                        defects += 1
                    for key, counter in counters.items():
                        counter[payload[key]] += 1
            connection.commit()
            index_path = output_dir / "audio_pack_functional_index.jsonl"
            os.replace(temp_path, index_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

        # Deduplicate blockers by relative_path (last write wins for detail freshness).
        blocker_by_path = {item["relative_path"]: item for item in blockers}
        ordered_blockers = [blocker_by_path[key] for key in sorted(blocker_by_path, key=str.casefold)]
        code_counts = Counter(item["code"] for item in ordered_blockers)
        failure_manifest = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "audio_library_index_failure_manifest",
            "index_revision": INDEX_REVISION,
            "tracker_id": TRACKER_ID,
            "item_id": ITEM_ID,
            "source_root": str(source_root),
            "discovered_audio_count": len(audio_files),
            "indexed_count": indexed_count,
            "exact_blocker_count": len(ordered_blockers),
            "indexed_plus_blockers_equals_discovered": indexed_count + len(ordered_blockers) == len(audio_files),
            "blocker_code_counts": dict(sorted(code_counts.items())),
            "blockers": ordered_blockers,
        }
        _validate_failure_manifest(failure_manifest)
        failure_manifest_path = output_dir / "failure_manifest.json"
        _write_json(failure_manifest_path, failure_manifest)

        fingerprint_after = build_source_inventory_fingerprint(source_root)
        source_files_modified = (
            fingerprint_before["fingerprint_sha256"] != fingerprint_after["fingerprint_sha256"]
        )
        summary = {
            "schema_version": "1.0",
            "artifact_type": "audio_pack_functional_index",
            "index_revision": INDEX_REVISION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_root": str(source_root),
            "source_files_modified": source_files_modified,
            "content_based_suppression": False,
            "audio_file_count": len(audio_files),
            "indexed_count": indexed_count,
            "exact_blocker_count": len(ordered_blockers),
            "indexed_plus_blockers_equals_discovered": indexed_count + len(ordered_blockers) == len(audio_files),
            "audio_bytes": total_bytes,
            "unique_audio_sha256_count": len(hashes),
            "duplicate_audio_file_count": sum(count - 1 for count in hashes.values()),
            "records_with_quality_defects": defects,
            "classification_counts": {key: dict(sorted(counter.items())) for key, counter in counters.items()},
            "index": {"path": index_path.name, "sha256": _sha256(index_path), "bytes": index_path.stat().st_size},
            "failure_manifest": {
                "path": failure_manifest_path.name,
                "sha256": _sha256(failure_manifest_path),
                "bytes": failure_manifest_path.stat().st_size,
            },
            "source_inventory_fingerprint": {
                "before": fingerprint_before,
                "after": fingerprint_after,
                "unchanged": not source_files_modified,
            },
            "state_database": {"path": state_path.name, "bytes": state_path.stat().st_size},
            "resume_policy": "reuse records only when relative path, byte size, and mtime_ns are unchanged",
        }
        summary_path = output_dir / "index_summary.json"
        _write_json(summary_path, summary)
        return summary
    finally:
        connection.close()


def _resolve_under_root(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path)


def iter_retained_index_records(index_path: Path) -> Iterator[dict[str, Any]]:
    with index_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"retained index JSONL parse failed at line {line_number}: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"retained index JSONL line {line_number} is not an object")
            yield payload


def _select_reconcile_sample(
    records: list[dict[str, Any]],
    *,
    sample_limit: int | None,
) -> list[dict[str, Any]]:
    if sample_limit is None or sample_limit >= len(records):
        return records
    if sample_limit < 1:
        raise ValueError("sample_limit must be >= 1 when provided")
    by_extension: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        extension = str(record.get("extension") or Path(str(record.get("relative_path") or "")).suffix or "unknown")
        by_extension[extension].append(record)
    selected: list[dict[str, Any]] = []
    extensions = sorted(by_extension)
    # Round-robin across extensions so mp3/flac/ogg are not starved by wav dominance.
    indexes = {extension: 0 for extension in extensions}
    while len(selected) < sample_limit and any(
        indexes[extension] < len(by_extension[extension]) for extension in extensions
    ):
        for extension in extensions:
            cursor = indexes[extension]
            bucket = by_extension[extension]
            if cursor >= len(bucket):
                continue
            selected.append(bucket[cursor])
            indexes[extension] = cursor + 1
            if len(selected) >= sample_limit:
                break
    return selected


def reconcile_retained_index_byte_hashes(
    source_root: Path,
    retained_index_path: Path,
    *,
    sample_limit: int | None = BYTE_HASH_SAMPLE_DEFAULT,
) -> dict[str, Any]:
    """Compare retained JSONL sha256/bytes against live source files.

    sample_limit=None checks every retained record (full-library gate).
    A finite sample advances scaffolding only and must not claim completion.
    """
    source_root = source_root.resolve()
    retained_index_path = retained_index_path.resolve()
    if not retained_index_path.is_file():
        return {
            "mode": "absent_retained_index",
            "retained_index_path": str(retained_index_path),
            "source_root": str(source_root),
            "complete": False,
            "scaffold_only": True,
            "checked_count": 0,
            "match_count": 0,
            "mismatch_count": 0,
            "missing_count": 0,
            "mismatches": [],
            "status": "RETAINED_INDEX_ABSENT",
        }
    if not source_root.is_dir():
        return {
            "mode": "absent_source_root",
            "retained_index_path": str(retained_index_path),
            "source_root": str(source_root),
            "complete": False,
            "scaffold_only": True,
            "checked_count": 0,
            "match_count": 0,
            "mismatch_count": 0,
            "missing_count": 0,
            "mismatches": [],
            "status": "SOURCE_ROOT_ABSENT",
        }

    records = list(iter_retained_index_records(retained_index_path))
    selected = _select_reconcile_sample(records, sample_limit=sample_limit)
    # A finite sample_limit never grants full-library completion, even if the
    # retained corpus is smaller than the requested sample.
    scaffold_only = sample_limit is not None
    mismatches: list[dict[str, Any]] = []
    match_count = 0
    missing_count = 0
    mismatch_count = 0
    extension_checked: Counter[str] = Counter()

    for record in selected:
        relative = str(record.get("relative_path") or "")
        expected_sha = str(record.get("sha256") or "")
        expected_bytes = record.get("bytes")
        extension = str(record.get("extension") or Path(relative).suffix or "unknown")
        extension_checked[extension] += 1
        live_path = source_root / relative
        if not live_path.is_file():
            missing_count += 1
            mismatch_count += 1
            mismatches.append(
                {
                    "relative_path": relative,
                    "code": "LIVE_SOURCE_MISSING",
                    "expected_sha256": expected_sha,
                    "expected_bytes": expected_bytes,
                }
            )
            continue
        try:
            live_stat = _io_path(live_path).stat()
            live_sha = _sha256(live_path)
        except OSError as exc:
            mismatch_count += 1
            mismatches.append(
                {
                    "relative_path": relative,
                    "code": "LIVE_SOURCE_UNREADABLE",
                    "detail": f"{type(exc).__name__}:{exc}",
                    "expected_sha256": expected_sha,
                    "expected_bytes": expected_bytes,
                }
            )
            continue
        if live_stat.st_size != expected_bytes or live_sha != expected_sha:
            mismatch_count += 1
            mismatches.append(
                {
                    "relative_path": relative,
                    "code": "BYTE_HASH_MISMATCH",
                    "expected_sha256": expected_sha,
                    "expected_bytes": expected_bytes,
                    "observed_sha256": live_sha,
                    "observed_bytes": live_stat.st_size,
                }
            )
            continue
        match_count += 1

    complete = (
        sample_limit is None
        and mismatch_count == 0
        and len(selected) == len(records)
        and len(records) > 0
    )
    if complete:
        status = "FULL_LIBRARY_BYTE_HASH_RECONCILED"
    elif scaffold_only and mismatch_count == 0 and match_count == len(selected) and selected:
        status = "SCAFFOLD_SAMPLE_BYTE_HASH_RECONCILED"
    elif mismatch_count:
        status = "BYTE_HASH_RECONCILIATION_MISMATCHES_PRESENT"
    else:
        status = "BYTE_HASH_RECONCILIATION_INCOMPLETE"

    return {
        "mode": "sample" if scaffold_only else "full_library",
        "retained_index_path": str(retained_index_path),
        "retained_index_sha256": _sha256(retained_index_path),
        "retained_index_bytes": retained_index_path.stat().st_size,
        "source_root": str(source_root),
        "retained_record_count": len(records),
        "sample_limit": sample_limit,
        "checked_count": len(selected),
        "match_count": match_count,
        "mismatch_count": mismatch_count,
        "missing_count": missing_count,
        "extension_checked_counts": dict(sorted(extension_checked.items())),
        "mismatches": mismatches[:32],
        "mismatch_truncated": max(0, len(mismatches) - 32),
        "complete": complete,
        "scaffold_only": scaffold_only,
        "does_not_grant_row069_acceptance": True,
        "status": status,
    }


def build_resume_replay_scaffold(
    retained_dir: Path,
    *,
    source_root: Path | None = None,
    prove_fixture: bool = True,
) -> dict[str, Any]:
    """Inspect retained artifacts and prove resume hash stability on a fixture only.

    Full-library resume replay against the retained 39771-record runtime directory
    remains intentionally unexecuted here so this slice cannot falsely claim
    library acceptance.
    """
    retained_dir = retained_dir.resolve()
    index_path = retained_dir / "audio_pack_functional_index.jsonl"
    summary_path = retained_dir / "index_summary.json"
    state_path = retained_dir / "functional_index_state.sqlite3"
    failure_path = retained_dir / "failure_manifest.json"

    artifacts: dict[str, Any] = {}
    for label, path in (
        ("index", index_path),
        ("summary", summary_path),
        ("state_database", state_path),
        ("failure_manifest", failure_path),
    ):
        if path.is_file():
            artifacts[label] = {
                "path": str(path),
                "exists": True,
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        else:
            artifacts[label] = {"path": str(path), "exists": False, "sha256": None, "bytes": None}

    retained_summary = None
    if summary_path.is_file():
        retained_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    state_record_count = None
    if state_path.is_file():
        connection = sqlite3.connect(state_path)
        try:
            row = connection.execute("SELECT COUNT(*) FROM records").fetchone()
            state_record_count = int(row[0]) if row else 0
        finally:
            connection.close()

    expected_index_sha = None
    expected_count = None
    if isinstance(retained_summary, dict):
        expected_index_sha = ((retained_summary.get("index") or {}).get("sha256"))
        expected_count = retained_summary.get("indexed_count") or retained_summary.get("audio_file_count")

    index_sha_matches_summary = bool(
        artifacts["index"]["exists"]
        and expected_index_sha
        and artifacts["index"]["sha256"] == expected_index_sha
    )
    state_count_matches = (
        state_record_count is not None
        and expected_count is not None
        and state_record_count == expected_count
    )

    fixture_proof: dict[str, Any] | None = None
    if prove_fixture:
        with tempfile.TemporaryDirectory(prefix="row069_resume_scaffold_") as temporary:
            base = Path(temporary)
            fixture_source = base / "source"
            fixture_source.mkdir()
            import struct
            import wave

            def _wav(path: Path, seconds: float) -> None:
                frames = int(16000 * seconds)
                with wave.open(str(path), "wb") as handle:
                    handle.setnchannels(1)
                    handle.setsampwidth(2)
                    handle.setframerate(16000)
                    handle.writeframes(struct.pack("<h", 0) * frames)

            first = fixture_source / "Fabric soft loop (CC0).wav"
            second = fixture_source / "Fabric soft duplicate (CC0).wav"
            _wav(first, 0.2)
            second.write_bytes(first.read_bytes())
            output = base / "index"
            initial = build_index(fixture_source, output)
            # Clone artifacts into a replay workdir so the scaffold mirrors the
            # eventual full-library copy-then-resume procedure without mutating
            # the retained production directory.
            replay_dir = base / "replay"
            shutil.copytree(output, replay_dir)
            before_hashes = {
                "index": _sha256(replay_dir / "audio_pack_functional_index.jsonl"),
                "summary": _sha256(replay_dir / "index_summary.json"),
                "failure_manifest": _sha256(replay_dir / "failure_manifest.json"),
                "state_database": _sha256(replay_dir / "functional_index_state.sqlite3"),
            }
            resumed = build_index(fixture_source, replay_dir, resume=True)
            after_hashes = {
                "index": resumed["index"]["sha256"],
                "summary": _sha256(replay_dir / "index_summary.json"),
                "failure_manifest": resumed["failure_manifest"]["sha256"],
                "state_database": _sha256(replay_dir / "functional_index_state.sqlite3"),
            }
            fixture_proof = {
                "authority": "synthetic_non_library",
                "initial_index_sha256": initial["index"]["sha256"],
                "before_hashes": before_hashes,
                "after_hashes": after_hashes,
                "index_sha256_stable": before_hashes["index"] == after_hashes["index"],
                "failure_manifest_sha256_stable": (
                    before_hashes["failure_manifest"] == after_hashes["failure_manifest"]
                ),
                "state_database_sha256_stable": (
                    before_hashes["state_database"] == after_hashes["state_database"]
                ),
                # Summary embeds generated_at, so byte identity is not required;
                # resume must still preserve index/failure-manifest/state hashes.
                "summary_generated_at_may_change": True,
                "does_not_grant_row069_acceptance": True,
            }

    full_library_ready = bool(
        artifacts["index"]["exists"]
        and artifacts["summary"]["exists"]
        and artifacts["state_database"]["exists"]
        and index_sha_matches_summary
        and state_count_matches
        and (fixture_proof is None or fixture_proof.get("index_sha256_stable"))
    )
    return {
        "retained_dir": str(retained_dir),
        "source_root": str(source_root.resolve()) if source_root else None,
        "artifacts": artifacts,
        "retained_summary_index_sha256": expected_index_sha,
        "retained_summary_indexed_count": expected_count,
        "state_record_count": state_record_count,
        "index_sha_matches_summary": index_sha_matches_summary,
        "state_count_matches_summary": state_count_matches,
        "failure_manifest_present_on_retained": artifacts["failure_manifest"]["exists"],
        "fixture_copy_resume_proof": fixture_proof,
        "full_library_resume_executed": False,
        "full_library_resume_replay_complete": False,
        "scaffold_ready_for_full_library_execution": full_library_ready,
        "does_not_grant_row069_acceptance": True,
        "status": (
            "RESUME_REPLAY_SCAFFOLD_READY_FULL_LIBRARY_ABSENT"
            if full_library_ready
            else "RESUME_REPLAY_SCAFFOLD_INCOMPLETE"
        ),
        "required_full_library_proof": [
            "copy retained index/summary/state into an isolated replay workdir",
            "run build_index(source_root, replay_workdir, resume=True) without mutating retained paths",
            "require stable audio_pack_functional_index.jsonl sha256",
            "require stable functional_index_state.sqlite3 sha256 when source path/size/mtime unchanged",
            "emit/refresh failure_manifest.json and bind its sha256 into the acceptance packet",
            "bind live inventory fingerprint before and after the resume replay",
        ],
    }


def evaluate_dependency_holds(root: Path) -> dict[str, Any]:
    holds: list[dict[str, Any]] = []
    for tracker_id, relative in (
        ("TRK-W64-067", "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-067_PLANNING_AUTHORITY_CURRENT_DELTA_20260719.json"),
        ("TRK-W64-068", "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-068_RIGHTS_PROVENANCE_CURRENT_DELTA_20260719.json"),
    ):
        path = root / relative
        if not path.is_file():
            holds.append(
                {
                    "tracker_id": tracker_id,
                    "path": relative,
                    "row_complete": False,
                    "dependency_satisfied": False,
                    "reason": "current_delta_absent",
                }
            )
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        row_complete = payload.get("row_complete") is True
        acceptance_key = "row067_acceptance" if tracker_id == "TRK-W64-067" else "row068_acceptance"
        acceptance = str(payload.get("decision", {}).get(acceptance_key) or "").lower()
        satisfied = row_complete and acceptance in {"accepted", "pass", "passed"}
        holds.append(
            {
                "tracker_id": tracker_id,
                "path": relative,
                "row_complete": row_complete,
                "dependency_satisfied": satisfied,
                "status": payload.get("status"),
                "acceptance": acceptance or None,
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return {
        "dependencies": holds,
        "all_satisfied": all(item["dependency_satisfied"] for item in holds),
    }


def build_authority_packet(
    root: Path,
    *,
    source_root: Path | None = None,
    retained_dir: Path | None = None,
    byte_hash_sample_limit: int | None = BYTE_HASH_SAMPLE_DEFAULT,
) -> dict[str, Any]:
    root = root.resolve()
    dependency = evaluate_dependency_holds(root)
    source = source_root or DEFAULT_SOURCE_ROOT
    retained = _resolve_under_root(root, retained_dir or DEFAULT_RETAINED_INDEX_DIR)
    source_observation = observe_source_inventory(source)
    byte_hash_reconcile = reconcile_retained_index_byte_hashes(
        source,
        retained / "audio_pack_functional_index.jsonl",
        sample_limit=byte_hash_sample_limit,
    )
    resume_scaffold = build_resume_replay_scaffold(
        retained,
        source_root=source,
        prove_fixture=True,
    )

    with tempfile.TemporaryDirectory(prefix="row069_authority_") as temporary:
        base = Path(temporary)
        fixture_source = base / "source"
        fixture_source.mkdir()
        import struct
        import wave

        def _wav(path: Path, seconds: float) -> None:
            frames = int(16000 * seconds)
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(struct.pack("<h", 0) * frames)

        good = fixture_source / "Fabric soft loop (CC0).wav"
        duplicate = fixture_source / "Fabric soft duplicate (CC0).wav"
        empty_blocker = fixture_source / "empty_blocker.wav"
        _wav(good, 0.25)
        duplicate.write_bytes(good.read_bytes())
        empty_blocker.write_bytes(b"")
        output = base / "index"
        summary = build_index(fixture_source, output)
        resumed = build_index(fixture_source, output, resume=True)
        failure_manifest = json.loads((output / "failure_manifest.json").read_text(encoding="utf-8"))
        fixture_calibration = {
            "authority": "synthetic_non_library",
            "determinism_note": (
                "Fixture proves durable failure-manifest emission, indexed+blocker "
                "reconciliation, source fingerprint immutability binding, resume "
                "hash stability, and copy-then-resume scaffold only; it does not "
                "accept Row069 library completion."
            ),
            "summary": {
                "audio_file_count": summary["audio_file_count"],
                "indexed_count": summary["indexed_count"],
                "exact_blocker_count": summary["exact_blocker_count"],
                "indexed_plus_blockers_equals_discovered": summary[
                    "indexed_plus_blockers_equals_discovered"
                ],
                "unique_audio_sha256_count": summary["unique_audio_sha256_count"],
                "duplicate_audio_file_count": summary["duplicate_audio_file_count"],
                "index_sha256": summary["index"]["sha256"],
                "failure_manifest_sha256": summary["failure_manifest"]["sha256"],
                "source_fingerprint_before": summary["source_inventory_fingerprint"]["before"][
                    "fingerprint_sha256"
                ],
                "source_fingerprint_after": summary["source_inventory_fingerprint"]["after"][
                    "fingerprint_sha256"
                ],
                "source_fingerprint_unchanged": summary["source_inventory_fingerprint"]["unchanged"],
                "resume_index_sha256_match": resumed["index"]["sha256"] == summary["index"]["sha256"],
                "resume_failure_manifest_sha256_match": (
                    resumed["failure_manifest"]["sha256"] == summary["failure_manifest"]["sha256"]
                ),
            },
            "failure_manifest": failure_manifest,
        }

    retained_count = 39771
    current_count = source_observation.get("discovered_audio_count")
    current_count_matches = isinstance(current_count, int) and current_count == retained_count
    blocker_codes: list[str] = []
    unsatisfied = [dep for dep in dependency["dependencies"] if not dep["dependency_satisfied"]]
    for dep in unsatisfied:
        blocker_codes.append(f"{dep['tracker_id'].replace('-', '_')}_DEPENDENCY_NOT_ACCEPTED")
    if len(unsatisfied) == 2:
        blocker_codes.append("ROW067_AND_ROW068_DEPENDENCIES_NOT_ACCEPTED")
    elif len(unsatisfied) == 1:
        blocker_codes.append("ROW069_PREREQUISITE_DEPENDENCY_NOT_ACCEPTED")
    if not current_count_matches:
        blocker_codes.append("CURRENT_EXTERNAL_INVENTORY_NOT_RECONCILED")
    if not byte_hash_reconcile.get("complete"):
        if byte_hash_reconcile.get("status") == "SCAFFOLD_SAMPLE_BYTE_HASH_RECONCILED":
            blocker_codes.append("RETAINED_INDEX_BYTE_HASH_RECONCILIATION_SAMPLE_ONLY")
        else:
            blocker_codes.append("RETAINED_INDEX_BYTE_HASH_RECONCILIATION_ABSENT")
    if source_observation.get("inventory_fingerprint_sha256") is None:
        blocker_codes.append("SOURCE_INVENTORY_FINGERPRINT_UNAVAILABLE")
    if not resume_scaffold.get("full_library_resume_replay_complete"):
        blocker_codes.append("FULL_LIBRARY_RESUME_REPLAY_ABSENT")
    blocker_codes.append("ROW069_LIBRARY_RUNTIME_AUTHORITY_NOT_GRANTED")

    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered_codes: list[str] = []
    for code in blocker_codes:
        if code not in seen:
            seen.add(code)
            ordered_codes.append(code)

    if dependency["all_satisfied"] and byte_hash_reconcile.get("status") == "SCAFFOLD_SAMPLE_BYTE_HASH_RECONCILED":
        status = "HOLD_ROW068_UNLOCKED_BYTE_HASH_SAMPLE_AND_RESUME_SCAFFOLD_LIBRARY_AUTHORITY_INCOMPLETE"
    else:
        status = "HOLD_FAIL_CLOSED_INDEX_CONTRACT_ADVANCED_LIBRARY_AUTHORITY_INCOMPLETE"

    safe_next = (
        "Execute full retained-index byte-hash reconciliation (sample_limit=None) against the "
        "live inventory fingerprint, then run isolated full-library copy-then-resume replay "
        "with stable index/state/failure-manifest hashes before granting Row069 library acceptance."
    )
    if unsatisfied:
        safe_next = (
            "Accept remaining prerequisite dependency authority, then "
            + safe_next[0].lower()
            + safe_next[1:]
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-069_full_audio_library_index",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "index_revision": INDEX_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": status,
        "frozen_behavior": [
            "one deterministic index across all supported audio files",
            "preserve source bytes",
            "resume by relative path, byte size, and mtime_ns",
            "hash every indexed asset",
            "record exact parse/index failures in a durable failure manifest",
            "bind before/after source inventory fingerprints",
            "deduplicate container hashes",
            "reproduce index hash, record count, unique hash count, and failure-manifest hash",
            "reconcile retained index byte hashes against live source before acceptance",
            "prove full-library resume replay in an isolated workdir before acceptance",
        ],
        "dependency_authority": dependency,
        "current_source_observation": source_observation,
        "byte_hash_reconciliation": byte_hash_reconcile,
        "resume_replay_scaffold": {
            "status": resume_scaffold.get("status"),
            "scaffold_ready_for_full_library_execution": resume_scaffold.get(
                "scaffold_ready_for_full_library_execution"
            ),
            "full_library_resume_executed": resume_scaffold.get("full_library_resume_executed"),
            "full_library_resume_replay_complete": resume_scaffold.get(
                "full_library_resume_replay_complete"
            ),
            "failure_manifest_present_on_retained": resume_scaffold.get(
                "failure_manifest_present_on_retained"
            ),
            "index_sha_matches_summary": resume_scaffold.get("index_sha_matches_summary"),
            "state_count_matches_summary": resume_scaffold.get("state_count_matches_summary"),
            "state_record_count": resume_scaffold.get("state_record_count"),
            "retained_summary_indexed_count": resume_scaffold.get("retained_summary_indexed_count"),
            "fixture_copy_resume_proof": resume_scaffold.get("fixture_copy_resume_proof"),
            "required_full_library_proof": resume_scaffold.get("required_full_library_proof"),
            "does_not_grant_row069_acceptance": True,
        },
        "retained_index_reference": {
            "runtime_index_path": (
                "runtime_artifacts/audio_asset_indexes/"
                "audio_downloads_functional_20260715T095712-0500/audio_pack_functional_index.jsonl"
            ),
            "runtime_dir": (
                str(retained.relative_to(root))
                if str(retained).lower().startswith(str(root).lower())
                else str(retained)
            ),
            "retained_discovered_audio_count": retained_count,
            "current_count_matches_retained": current_count_matches,
            "current_inventory_fingerprint_bound": bool(
                source_observation.get("inventory_fingerprint_sha256")
            ),
            "byte_hash_reconciliation_complete": bool(byte_hash_reconcile.get("complete")),
            "byte_hash_sample_status": byte_hash_reconcile.get("status"),
            "byte_hash_sample_checked_count": byte_hash_reconcile.get("checked_count"),
            "technical_reuse_allowed": True,
            "does_not_grant_row069_acceptance": True,
        },
        "fixture_calibration": fixture_calibration,
        "blocker_codes": ordered_codes,
        "decision": {
            "status": "blocked",
            "row069_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": safe_next,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(PROJECT_ROOT))
    parser.add_argument("--source-root", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--emit-authority",
        action="store_true",
        help="Emit fail-closed Row069 direct evidence (library acceptance remains held).",
    )
    parser.add_argument(
        "--retained-dir",
        default=str(DEFAULT_RETAINED_INDEX_DIR),
        help="Retained runtime index directory used for reconcile/resume scaffolding.",
    )
    parser.add_argument(
        "--byte-hash-sample-limit",
        type=int,
        default=BYTE_HASH_SAMPLE_DEFAULT,
        help="Finite sample for byte-hash scaffolding; use 0 to request full-library reconcile.",
    )
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.emit_authority:
        source_root = Path(args.source_root) if args.source_root else DEFAULT_SOURCE_ROOT
        sample_limit = None if args.byte_hash_sample_limit == 0 else args.byte_hash_sample_limit
        payload = build_authority_packet(
            root,
            source_root=source_root,
            retained_dir=Path(args.retained_dir),
            byte_hash_sample_limit=sample_limit,
        )
        if payload["decision"]["status"] != "blocked":
            raise SystemExit("authority emission must remain fail-closed until acceptance gates pass")
        if payload.get("row_complete") is True:
            raise SystemExit("authority emission must not claim row_complete")
        if payload.get("library_authority") is True:
            raise SystemExit("authority emission must not claim library_authority")
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        _write_json(output, payload)
        print(
            json.dumps(
                {
                    "output": str(output),
                    "status": payload["status"],
                    "row069_acceptance": payload["decision"]["row069_acceptance"],
                    "library_authority": payload["library_authority"],
                    "dependency_all_satisfied": payload["dependency_authority"]["all_satisfied"],
                    "byte_hash_status": payload["byte_hash_reconciliation"]["status"],
                    "resume_scaffold_status": payload["resume_replay_scaffold"]["status"],
                },
                sort_keys=True,
            )
        )
        return 0

    if not args.source_root or not args.output_dir:
        parser.error("--source-root and --output-dir are required unless --emit-authority is set")
    try:
        summary = build_index(Path(args.source_root), Path(args.output_dir), resume=args.resume)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(
        json.dumps(
            {
                "status": "PASS",
                **summary["index"],
                "audio_file_count": summary["audio_file_count"],
                "indexed_count": summary["indexed_count"],
                "exact_blocker_count": summary["exact_blocker_count"],
                "failure_manifest_sha256": summary["failure_manifest"]["sha256"],
                "source_fingerprint_unchanged": summary["source_inventory_fingerprint"]["unchanged"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
