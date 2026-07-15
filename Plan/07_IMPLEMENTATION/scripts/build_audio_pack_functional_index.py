#!/usr/bin/env python3
"""Build a resumable, hash-bound functional index for external audio assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from mutagen import File as MutagenFile


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = PROJECT_ROOT / "Plan/08_SCHEMAS/audio_pack_functional_index_record.schema.json"
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg"}


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
    connection.execute("CREATE TABLE IF NOT EXISTS records (relative_path TEXT PRIMARY KEY, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, payload TEXT NOT NULL)")
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
    try:
        for index, path in enumerate(audio_files, start=1):
            relative = path.relative_to(source_root).as_posix()
            stat = _io_path(path).stat()
            cached = connection.execute("SELECT size, mtime_ns FROM records WHERE relative_path = ?", (relative,)).fetchone()
            if cached != (stat.st_size, stat.st_mtime_ns):
                record = _record_for(path, source_root)
                errors = list(validator.iter_errors(record))
                if errors:
                    raise ValueError(f"record schema failed for {relative}: {errors[0].message}")
                connection.execute(
                    "INSERT OR REPLACE INTO records(relative_path, size, mtime_ns, payload) VALUES (?, ?, ?, ?)",
                    (relative, stat.st_size, stat.st_mtime_ns, json.dumps(record, ensure_ascii=True, sort_keys=True)),
                )
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
        counters: dict[str, Counter[str]] = {key: Counter() for key in ("extension", "event_type", "material", "role", "intensity_band", "sync_class", "license_classification")}
        hashes: Counter[str] = Counter()
        defects = 0
        total_bytes = 0
        try:
            with temp_handle:
                for (payload_text,) in connection.execute("SELECT payload FROM records ORDER BY relative_path COLLATE NOCASE"):
                    payload = _refresh_routing(json.loads(payload_text))
                    errors = list(validator.iter_errors(payload))
                    if errors:
                        raise ValueError(f"cached record schema failed for {payload.get('relative_path')}: {errors[0].message}")
                    temp_handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
                    total_bytes += payload["bytes"]
                    hashes[payload["sha256"]] += 1
                    if payload["quality_defects"]:
                        defects += 1
                    for key, counter in counters.items():
                        counter[payload[key]] += 1
            index_path = output_dir / "audio_pack_functional_index.jsonl"
            os.replace(temp_path, index_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

        summary = {
            "schema_version": "1.0",
            "artifact_type": "audio_pack_functional_index",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_root": str(source_root),
            "source_files_modified": False,
            "content_based_suppression": False,
            "audio_file_count": len(audio_files),
            "audio_bytes": total_bytes,
            "unique_audio_sha256_count": len(hashes),
            "duplicate_audio_file_count": sum(count - 1 for count in hashes.values()),
            "records_with_quality_defects": defects,
            "classification_counts": {key: dict(sorted(counter.items())) for key, counter in counters.items()},
            "index": {"path": index_path.name, "sha256": _sha256(index_path), "bytes": index_path.stat().st_size},
            "state_database": {"path": state_path.name, "bytes": state_path.stat().st_size},
            "resume_policy": "reuse records only when relative path, byte size, and mtime_ns are unchanged",
        }
        summary_path = output_dir / "index_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
        return summary
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    try:
        summary = build_index(Path(args.source_root), Path(args.output_dir), resume=args.resume)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "PASS", **summary["index"], "audio_file_count": summary["audio_file_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
