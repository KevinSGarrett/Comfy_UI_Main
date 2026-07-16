#!/usr/bin/env python3
"""Inspect Wave64 speech cache keys and local control-plane telemetry."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_bridge(root: Path):
    path = root / "Plan/07_IMPLEMENTATION/comfyui_custom_nodes/wave64_speech_bridge/__init__.py"
    spec = importlib.util.spec_from_file_location("wave64_speech_bridge_cache", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"unable to load bridge: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_request(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("request root must be an object")
    return value


def report(cache_root: Path) -> dict:
    records = []
    for path in sorted((cache_root / "telemetry").glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("schema_version") == "1.0":
            records.append(value)
    hits = sum(record.get("cache_hit") is True for record in records)
    wall = sum(float(record.get("wall_clock_seconds") or 0.0) for record in records)
    return {
        "classification": "W64_SPEECH_RUNTIME_CACHE_COST_REPORT",
        "telemetry_record_count": len(records),
        "cache_hit_count": hits,
        "cache_hit_rate": round(hits / len(records), 9) if records else None,
        "total_wall_clock_seconds": round(wall, 9),
        "estimated_cost_usd": None,
        "boundaries": {
            "local_control_plane_only": True,
            "fabricated_dollar_cost": False,
            "production_runtime_authority": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    subparsers = parser.add_subparsers(dest="command", required=True)
    key_parser = subparsers.add_parser("key")
    key_parser.add_argument("--request", type=Path, required=True)
    subparsers.add_parser("report")
    args = parser.parse_args()
    root = args.project_root.resolve()
    try:
        if args.command == "key":
            bridge = load_bridge(root)
            request = bridge.validate_request(load_request(args.request.resolve()))
            result = {
                "classification": "W64_SPEECH_RUNTIME_CACHE_KEY_VALID",
                "cache_key": bridge.compute_cache_key(request),
                "cache_key_payload": bridge.cache_key_payload(request),
            }
        else:
            result = report(root / "runtime_artifacts/audio_speech_cache")
    except Exception as exc:
        print(json.dumps({"classification": "W64_SPEECH_RUNTIME_CACHE_COST_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
