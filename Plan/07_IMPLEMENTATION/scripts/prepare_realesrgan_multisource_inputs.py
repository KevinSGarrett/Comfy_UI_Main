#!/usr/bin/env python3
"""Prepare two tracked, non-duplicate sources for RealESRGAN robustness QA."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = ROOT / "Plan/Instructions/Operations/Prepared_Input_Assets/realesrgan_multisource_w70_v1"
INPUT_DIR = ROOT / "ComfyUI/input"
SOURCES = {
    "normal_fullbody": {
        "source": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/normal_v4_full_body_standing_seed711670301_20260711T035900-0500/images/normal_v4_fullbody_standing_711670301_00001_.png",
        "filename": "upscale_source_normal_fullbody_w70_v1.png",
        "source_class": "fullbody_portrait_normal_control_output",
    },
    "two_character_contact": {
        "source": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/realvisxl_two_character_hand_to_body_w69_seed7152026252_20260707T113434-0500/images/codex_realvisxl_two_character_hand_to_body_seed7152026252_00001_.png",
        "filename": "upscale_source_two_character_contact_w70_v1.png",
        "source_class": "square_two_character_contact_output",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install-inputs", action="store_true")
    args = parser.parse_args()
    missing = [str(entry["source"]) for entry in SOURCES.values() if not entry["source"].is_file()]
    if missing:
        raise FileNotFoundError(f"Tracked RealESRGAN source missing: {missing}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for source_id, entry in SOURCES.items():
        source = entry["source"]
        prepared = OUTPUT_DIR / entry["filename"]
        shutil.copyfile(source, prepared)
        active_input = INPUT_DIR / entry["filename"]
        if args.install_inputs:
            shutil.copyfile(prepared, active_input)
        with Image.open(source) as image:
            width, height = image.size
            mode = image.mode
        source_hash = sha256(source)
        prepared_hash = sha256(prepared)
        records.append(
            {
                "source_id": source_id,
                "source_class": entry["source_class"],
                "source": rel(source),
                "source_sha256": source_hash,
                "prepared": rel(prepared),
                "prepared_sha256": prepared_hash,
                "active_input": rel(active_input),
                "active_input_installed": args.install_inputs,
                "active_input_sha256": sha256(active_input) if args.install_inputs else None,
                "width": width,
                "height": height,
                "mode": mode,
                "source_prepared_hash_match": source_hash == prepared_hash,
            }
        )

    checks = {
        "exactly_two_sources": len(records) == 2,
        "distinct_source_classes": len({record["source_class"] for record in records}) == 2,
        "all_source_prepared_hashes_match": all(record["source_prepared_hash_match"] for record in records),
        "all_inputs_installed": args.install_inputs and all(record["active_input_installed"] for record in records),
        "all_active_input_hashes_match": args.install_inputs and all(record["active_input_sha256"] == record["prepared_sha256"] for record in records),
        "no_mask_source_consumed": True,
    }
    passed = all(checks.values())
    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "result": "pass_realesrgan_multisource_inputs_prepared" if passed else "blocked_realesrgan_multisource_input_gap",
        "pass": passed,
        "scope": "two_existing_tracked_output_classes_for_upscale_robustness",
        "sources": records,
        "checks": checks,
        "boundaries": {
            "source_lanes_regenerated": False,
            "source_lane_evidence_reclassified": False,
            "gold_masks_consumed": False,
            "aws_contacted": False,
            "ec2_started": False,
        },
    }
    manifest_path = OUTPUT_DIR / "PREPARATION_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
