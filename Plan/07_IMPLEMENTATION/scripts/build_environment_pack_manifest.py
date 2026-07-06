#!/usr/bin/env python3
"""Build a hash manifest for a Wave09 environment reference pack folder."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def infer_role(relative_path: Path) -> str:
    parts = [p.lower() for p in relative_path.parts]
    if "lighting" in parts:
        return "lighting_reference"
    if "materials" in parts:
        return "material_reference"
    if "props" in parts:
        return "prop_reference"
    if "camera" in parts:
        return "camera_reference"
    if "masks" in parts:
        return "mask_reference"
    if "video" in parts:
        return "video_environment_reference"
    if "audio" in parts:
        return "audio_environment_reference"
    if "room" in parts:
        return "room_reference"
    return "environment_pack_file"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-root", required=True, type=Path)
    parser.add_argument("--environment-id", required=True)
    parser.add_argument("--environment-version", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    if not args.pack_root.exists():
        print(f"FAIL: pack root does not exist: {args.pack_root}")
        return 1

    files: list[dict[str, Any]] = []
    for path in sorted(args.pack_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(args.pack_root)
        if relative.as_posix() == args.out.name:
            continue
        files.append({
            "relative_path": relative.as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "role": infer_role(relative),
        })

    manifest = {
        "environment_id": args.environment_id,
        "environment_version": args.environment_version,
        "pack_root": str(args.pack_root),
        "file_count": len(files),
        "files": files,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"PASS: wrote {args.out} with {len(files)} files")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
