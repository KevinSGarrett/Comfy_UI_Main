#!/usr/bin/env python3
"""Build a hash-bound, nonpromoting stage-2 image calibration board on RunPod."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ZERO_HASH = "0" * 64
BOARD_SCHEMA = "w64.image_stage2_calibration_board.v1"
SEAL_SCHEMA = "w64.image_stage2_calibration_board_seal.v1"
DEFECTS = ("DETAIL_BLUR", "OVERSATURATION", "SEAM_PASTE")


class BoardError(RuntimeError):
    """Raised when a calibration board cannot be built reproducibly."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_json_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise BoardError(f"immutable output already exists: {path}")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, indent=2, sort_keys=True))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def seal(value: dict[str, Any], field: str) -> dict[str, Any]:
    result = dict(value)
    result[field] = ZERO_HASH
    result[field] = digest(result)
    return result


def verify_seal(value: dict[str, Any], field: str) -> None:
    observed = value.get(field)
    candidate = dict(value)
    candidate[field] = ZERO_HASH
    if not isinstance(observed, str) or digest(candidate) != observed:
        raise BoardError(f"invalid input seal: {field}")


def _safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    normalized = value.replace("\\", "/")
    return not normalized.startswith("/") and ".." not in normalized.split("/")


@dataclass(frozen=True)
class SourceImage:
    path: Path
    sha256: str
    width: int
    height: int
    source_root: str
    relative_path: str


def load_sources(panel_path: Path, panel_seal_path: Path) -> tuple[dict[str, Any], list[SourceImage]]:
    try:
        panel = json.loads(panel_path.read_text(encoding="utf-8"))
        panel_seal = json.loads(panel_seal_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BoardError("input panel or seal is invalid JSON") from exc
    verify_seal(panel_seal, "final_sha256")
    if panel.get("schema") != "w64.reference_image_semantic_review_panel.v1":
        raise BoardError("unexpected input panel schema")
    if (
        "contract_sha256" in panel_seal
        and panel.get("contract_sha256") != panel_seal.get("contract_sha256")
    ):
        raise BoardError("input panel seal contract mismatch")
    artifact_root = panel_path.parent.parent.resolve()
    items = panel.get("items")
    if not isinstance(items, list) or not items:
        raise BoardError("input panel has no items")
    sources: list[SourceImage] = []
    for item in items:
        if not isinstance(item, dict) or not _safe_relative(item.get("source_root")) or not _safe_relative(item.get("path")):
            raise BoardError("input panel contains unsafe path")
        source = (artifact_root / item["source_root"] / item["path"]).resolve()
        try:
            source.relative_to(artifact_root)
        except ValueError as exc:
            raise BoardError("input panel source path escapes artifact root") from exc
        if not source.is_file() or source.stat().st_size != item.get("bytes"):
            raise BoardError("input panel source is missing or changed")
        if sha256_file(source) != item.get("sha256"):
            raise BoardError("input panel source hash mismatch")
        if not isinstance(item.get("width"), int) or not isinstance(item.get("height"), int):
            raise BoardError("input panel dimensions are invalid")
        sources.append(
            SourceImage(
                path=source,
                sha256=item["sha256"],
                width=item["width"],
                height=item["height"],
                source_root=item["source_root"],
                relative_path=item["path"],
            )
        )
    return panel, sorted(sources, key=lambda item: (item.sha256, item.relative_path))


def _seeded_image(source: SourceImage, defect_id: str, ordinal: int):
    from PIL import Image, ImageEnhance, ImageFilter

    with Image.open(source.path) as opened:
        image = opened.convert("RGB")
    width, height = image.size
    if width < 4 or height < 4:
        raise BoardError("source image is too small for deterministic defect injection")
    if defect_id == "DETAIL_BLUR":
        return image.filter(ImageFilter.GaussianBlur(radius=3 + ordinal % 3))
    if defect_id == "OVERSATURATION":
        return ImageEnhance.Color(image).enhance(2.5 + (ordinal % 3) * 0.25)
    if defect_id == "SEAM_PASTE":
        patch_width = max(2, width // 4)
        patch_height = max(2, height // 4)
        left = (ordinal * 17) % (width - patch_width + 1)
        top = (ordinal * 29) % (height - patch_height + 1)
        patch = image.crop((left, top, left + patch_width, top + patch_height))
        destination_left = (left + width // 2) % (width - patch_width + 1)
        destination_top = (top + height // 3) % (height - patch_height + 1)
        image.paste(patch, (destination_left, destination_top))
        return image
    raise BoardError(f"unsupported seeded defect: {defect_id}")


def _write_png_new(path: Path, image: Any) -> None:
    if path.exists():
        raise BoardError(f"immutable generated image already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        image.save(temporary, format="PNG", optimize=False)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_board(
    *,
    panel_path: Path,
    panel_seal_path: Path,
    output_root: Path,
    source_count: int = 40,
    negative_count: int = 60,
) -> dict[str, Any]:
    """Build an immutable calibration draft; it cannot qualify or promote a role."""

    if source_count < 1 or negative_count < 1:
        raise BoardError("board requires positive source and seeded-defect counts")
    panel_path = panel_path.resolve()
    panel_seal_path = panel_seal_path.resolve()
    root = output_root.resolve()
    if root.exists():
        raise BoardError("output root already exists")
    panel, sources = load_sources(panel_path, panel_seal_path)
    selected = sources[:source_count]
    if len(selected) != source_count:
        raise BoardError("input panel has fewer sources than requested")
    root.mkdir(parents=True)
    generated_root = root / "seeded_defects"
    entries: list[dict[str, Any]] = []
    try:
        for index, source in enumerate(selected, start=1):
            entries.append(
                {
                    "item_id": f"BASELINE-{index:03d}",
                    "kind": "BASELINE_REFERENCE",
                    "source": {
                        "source_root": source.source_root,
                        "relative_path": source.relative_path,
                        "sha256": source.sha256,
                        "path": str(source.path),
                    },
                    "expected_defects": [],
                    "authority": "NONPROMOTING_CALIBRATION_DRAFT_ONLY",
                }
            )
        for ordinal in range(negative_count):
            source = selected[ordinal % len(selected)]
            defect_id = DEFECTS[ordinal % len(DEFECTS)]
            output = generated_root / f"{ordinal + 1:03d}_{defect_id.lower()}.png"
            generated = _seeded_image(source, defect_id, ordinal)
            _write_png_new(output, generated)
            entries.append(
                {
                    "item_id": f"SEEDED-{ordinal + 1:03d}",
                    "kind": "SEEDED_DEFECT",
                    "source": {
                        "source_root": source.source_root,
                        "relative_path": source.relative_path,
                        "sha256": source.sha256,
                        "path": str(source.path),
                    },
                    "generated": {
                        "relative_path": output.relative_to(root).as_posix(),
                        "sha256": sha256_file(output),
                        "bytes": output.stat().st_size,
                    },
                    "expected_defects": [defect_id],
                    "severity": "SERIOUS",
                    "authority": "NONPROMOTING_CALIBRATION_DRAFT_ONLY",
                }
            )
        board = seal(
            {
                "schema_version": BOARD_SCHEMA,
                "board_sha256": ZERO_HASH,
                "state": "CALIBRATION_BOARD_DRAFT_UNQUALIFIED",
                "authority": "NONPROMOTING_CALIBRATION_DRAFT_ONLY",
                "input_panel": {
                    "path": str(panel_path),
                    "sha256": sha256_file(panel_path),
                    "contract_sha256": panel["contract_sha256"],
                },
                "counts": {"baseline_reference": source_count, "seeded_defect": negative_count, "total": len(entries)},
                "entries": entries,
            },
            field="board_sha256",
        )
        board_path = root / "stage2_image_calibration_board.json"
        write_json_new(board_path, board)
        seal_record = seal(
            {
                "schema_version": SEAL_SCHEMA,
                "final_sha256": ZERO_HASH,
                "board_sha256": board["board_sha256"],
                "generated_tree_sha256": digest(
                    [
                        {
                            "relative_path": entry["generated"]["relative_path"],
                            "sha256": entry["generated"]["sha256"],
                            "bytes": entry["generated"]["bytes"],
                        }
                        for entry in entries
                        if entry["kind"] == "SEEDED_DEFECT"
                    ]
                ),
                "authority": "NONPROMOTING_CALIBRATION_DRAFT_ONLY",
            },
            field="final_sha256",
        )
        write_json_new(root / "stage2_image_calibration_board_seal.json", seal_record)
        return board
    except Exception:
        shutil.rmtree(root)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--panel-seal", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--source-count", type=int, default=40)
    parser.add_argument("--negative-count", type=int, default=60)
    args = parser.parse_args()
    try:
        board = build_board(
            panel_path=args.panel,
            panel_seal_path=args.panel_seal,
            output_root=args.output_root,
            source_count=args.source_count,
            negative_count=args.negative_count,
        )
    except BoardError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1
    print(json.dumps({"status": board["state"], "board_sha256": board["board_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
