#!/usr/bin/env python3
"""Build a newline-free semantic review packet from an exact committed scope."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_PATHS = (
    "Plan/07_IMPLEMENTATION/scripts/run_wave64_qwen3_tts_voice_clone.py",
    "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_qwen3_tts_voice_clone.py",
    "Plan/07_IMPLEMENTATION/scripts/finalize_wave64_speech_rows124_127.py",
    "Plan/Instructions/QA/Scripts/test_run_wave64_qwen3_tts_voice_clone.py",
    "Plan/Instructions/QA/Scripts/test_evaluate_wave64_qwen3_tts_voice_clone.py",
    "Plan/Instructions/QA/Scripts/test_finalize_wave64_speech_rows124_127.py",
    "Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW124.json",
    "Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW125.json",
    "Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW126.json",
    "Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW127.json",
    "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv",
    "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv",
)


class PacketError(RuntimeError):
    pass


def git_bytes(root: Path, revision: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        raise PacketError(f"unable to read committed scope file {relative}: {result.stderr.decode(errors='replace')}")
    return result.stdout


def build(root: Path, revision: str, paths: tuple[str, ...]) -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", revision], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    files = []
    for relative in paths:
        payload = git_bytes(root, commit, relative)
        try:
            content = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise PacketError(f"semantic scope file is not UTF-8 text: {relative}") from exc
        files.append(
            {
                "path": relative,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "content": content,
            }
        )
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_rows124_127_semantic_review_packet",
        "base_commit": commit,
        "review_contract": {
            "facts": [
                "one genuine immutable Qwen Base ICL clone exists",
                "WER and calibrated chain-specific identity pass",
                "raw 3.000+/-0.080 second timing fails",
                "production reference authority, multi-reference continuity, listening, style, and intensity remain blocked",
            ],
            "inspect_for": [
                "false promotion or evidence contradiction",
                "lineage or fail-closed defects",
                "unsupported metric or speaker identity claims",
                "focused or controlled force-mapped into emotion classes",
            ],
            "mutation_boundary": "read_only_worker; Codex final authority",
        },
        "files": files,
    }


def write_packet(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if b"\r" in payload or b"\n" in payload:
        raise PacketError("review packet must not contain physical newline bytes")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    output = args.output.resolve() if args.output.is_absolute() else (root / args.output).resolve()
    try:
        packet = build(root, args.revision, DEFAULT_PATHS)
        write_packet(output, packet)
    except Exception as exc:
        print(json.dumps({"classification": "W64_SEMANTIC_REVIEW_PACKET_FAILED", "error": str(exc)}))
        return 2
    print(json.dumps({"classification": "W64_SEMANTIC_REVIEW_PACKET_READY", "output": str(output), "bytes": output.stat().st_size, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "file_count": len(packet["files"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
