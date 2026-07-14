#!/usr/bin/env python3
"""Build a non-Git routing index for the external OpenNSFW SFX library."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


AUDIO_EXTENSIONS = {".flac", ".mp3", ".ogg", ".wav"}
ATTRIBUTION_HINTS = ("attribution", "license", "readme", "terms")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _license_from_path(relative_path: str) -> str:
    lowered = relative_path.lower()
    if "(cc0)" in lowered or "[cc0]" in lowered:
        return "CC0-1.0"
    if "cc4.0 attribution" in lowered or "cc-by-4.0" in lowered:
        return "CC-BY-4.0"
    if "no attribution" in lowered:
        return "pack_claimed_no_attribution"
    return "open_nsfw_sfx_pack_terms"


def _category(parts: tuple[str, ...]) -> str:
    if not parts:
        return "uncategorized"
    start = 1 if parts[0].lower() == "opennsfw sfx" and len(parts) > 1 else 0
    return parts[start]


def _nearest_attribution(relative: Path, documents: list[str]) -> list[str]:
    parent = relative.parent.as_posix().lower()
    candidates = [doc for doc in documents if parent.startswith(Path(doc).parent.as_posix().lower())]
    candidates.sort(key=lambda value: (-len(Path(value).parts), value.casefold()))
    return candidates[:3]


def build_index(source_root: Path, output_dir: Path) -> dict:
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise ValueError(f"source root is not a directory: {source_root}")
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")

    files = sorted(
        (path for path in source_root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(source_root).as_posix().casefold(),
    )
    documents = [
        path.relative_to(source_root).as_posix()
        for path in files
        if any(hint in path.name.lower() for hint in ATTRIBUTION_HINTS)
        and path.suffix.lower() not in AUDIO_EXTENSIONS
    ]
    audio_files = [path for path in files if path.suffix.lower() in AUDIO_EXTENSIONS]
    extension_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    license_counts: Counter[str] = Counter()

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent))
    try:
        index_path = temp_dir / "audio_asset_index.jsonl"
        with index_path.open("w", encoding="utf-8", newline="\n") as handle:
            for path in audio_files:
                relative = path.relative_to(source_root)
                relative_text = relative.as_posix()
                license_name = _license_from_path(relative_text)
                category = _category(relative.parts)
                extension = path.suffix.lower()
                extension_counts[extension] += 1
                category_counts[category] += 1
                license_counts[license_name] += 1
                record = {
                    "relative_path": relative_text,
                    "absolute_path": str(path),
                    "extension": extension,
                    "bytes": path.stat().st_size,
                    "category": category,
                    "license_classification": license_name,
                    "attribution_documents": _nearest_attribution(relative, documents),
                    "content_based_suppression": False,
                }
                handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")

        summary = {
            "schema_version": "1.0",
            "artifact_type": "open_nsfw_sfx_non_git_routing_index",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_root": str(source_root),
            "source_files_modified": False,
            "content_based_suppression": False,
            "audio_file_count": len(audio_files),
            "audio_bytes": sum(path.stat().st_size for path in audio_files),
            "extension_counts": dict(sorted(extension_counts.items())),
            "category_counts": dict(sorted(category_counts.items())),
            "license_classification_counts": dict(sorted(license_counts.items())),
            "attribution_document_count": len(documents),
            "index": {
                "path": "audio_asset_index.jsonl",
                "sha256": _sha256(index_path),
                "bytes": index_path.stat().st_size,
            },
            "hashing_policy": "index_hash_only_selected_media_hashed_at_use",
        }
        (temp_dir / "index_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temp_dir, output_dir)
        return summary
    except Exception:
        for path in sorted(temp_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        temp_dir.rmdir()
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        summary = build_index(Path(args.source_root), Path(args.output_dir))
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "pass", **summary["index"], "audio_file_count": summary["audio_file_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
