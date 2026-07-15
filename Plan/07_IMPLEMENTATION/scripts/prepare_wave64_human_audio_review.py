#!/usr/bin/env python3
"""Prepare a hash-bound human listening request after automated gates pass."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = PROJECT_ROOT / "Plan/08_SCHEMAS/wave64_human_audio_review_request.schema.json"
DEFAULT_SECTIONS = ["beginning", "middle", "end", "loud", "quiet", "transitions"]
DEFAULT_CATEGORIES = [
    "exact_spoken_content", "intelligibility", "character_voice_match", "voice_continuity",
    "delivery_style", "intensity", "pacing_timing", "pronunciation", "naturalness",
    "technical_cleanliness", "mix_balance", "av_sync",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _binding(path: Path) -> dict:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"artifact does not exist: {resolved}")
    return {"path": str(resolved), "sha256": _sha256(resolved), "bytes": resolved.stat().st_size}


def build_request(args: argparse.Namespace) -> dict:
    artifact = {**_binding(Path(args.artifact)), "media_type": args.media_type}
    evidence = [_binding(Path(path)) for path in args.automated_evidence]
    payload = {
        "schema_name": "wave64_human_audio_review_request",
        "request_version": 1,
        "review_id": args.review_id,
        "artifact_binding": artifact,
        "expected": {
            "transcript": args.expected_transcript,
            "character_id": args.character_id,
            "voice_profile_id": args.voice_profile_id,
            "emotion_class": args.emotion_class,
            "delivery_style": args.delivery_style,
            "intensity": args.intensity,
            "pace_wpm": args.pace_wpm,
            "duration_target_seconds": args.duration_target_seconds,
            "sync_required": args.sync_required,
        },
        "automated_evidence_bindings": evidence,
        "required_sections": DEFAULT_SECTIONS,
        "required_categories": DEFAULT_CATEGORIES,
        "minimum_score": 4.0,
        "blinding": {"engine_identity_hidden_initial_pass": True},
    }
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    if errors:
        raise ValueError(errors[0].message)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--media-type", choices=("audio", "audio_video"), default="audio")
    parser.add_argument("--review-id", required=True)
    parser.add_argument("--expected-transcript", default="")
    parser.add_argument("--character-id", required=True)
    parser.add_argument("--voice-profile-id", required=True)
    parser.add_argument("--emotion-class")
    parser.add_argument("--delivery-style", required=True)
    parser.add_argument("--intensity", required=True)
    parser.add_argument("--pace-wpm", type=float)
    parser.add_argument("--duration-target-seconds", type=float, required=True)
    parser.add_argument("--sync-required", action="store_true")
    parser.add_argument("--automated-evidence", action="append", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        output = Path(args.output).resolve()
        if output.exists():
            raise ValueError(f"output already exists: {output}")
        payload = build_request(args)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "PASS", "request_sha256": _sha256(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
