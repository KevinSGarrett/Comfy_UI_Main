#!/usr/bin/env python3
"""Build immutable prospective audio semantic/alignment calibration fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import struct
import wave
from pathlib import Path


class CalibrationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_plan(path: Path) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("schema_version") != "wave64.aqa.audio_semantic_alignment_calibration_plan.v1":
        raise CalibrationError("calibration plan schema mismatch")
    fixtures = plan.get("fixtures", [])
    if [item.get("fixture_id") for item in fixtures] != ["clean_speech", "tone_only", "silence", "speech_plus_tone"]:
        raise CalibrationError("prospective fixture matrix mismatch")
    if plan.get("authority") != {"prospective": True, "unchanged_rerun_forbidden": True, "operational": False, "product_promotion": False}:
        raise CalibrationError("authority boundary mismatch")
    return plan


def read_source(path: Path, source: dict) -> tuple[wave._wave_params, list[int]]:
    if not path.is_file() or path.stat().st_size != source["bytes"] or sha256_file(path) != source["sha256"]:
        raise CalibrationError("source identity mismatch")
    with wave.open(str(path), "rb") as handle:
        params = handle.getparams()
        raw = handle.readframes(handle.getnframes())
    observed = (params.nchannels, params.sampwidth, params.framerate, params.nframes, params.comptype)
    expected = (source["channels"], source["sample_width_bytes"], source["sample_rate_hz"], source["frame_count"], "NONE")
    if observed != expected:
        raise CalibrationError(f"source PCM geometry mismatch: {observed}")
    return params, list(struct.unpack(f"<{params.nframes}h", raw))


def write_pcm16(path: Path, rate: int, samples: list[int]) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def build(plan_path: Path, repository_root: Path, output_dir: Path) -> dict:
    plan = load_plan(plan_path)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise CalibrationError("immutable output directory is not empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    source_path = repository_root / plan["source"]["relative_path"]
    params, speech = read_source(source_path, plan["source"])
    synth = plan["synthesis"]
    tone = [int(round(32767 * synth["tone_peak"] * math.sin(2 * math.pi * synth["tone_frequency_hz"] * i / params.framerate))) for i in range(params.nframes)]
    silence = [0] * params.nframes
    mixed = [max(-32768, min(32767, int(round(synth["mixed_speech_gain"] * s + synth["mixed_tone_gain"] * t)))) for s, t in zip(speech, tone, strict=True)]
    outputs = {
        "clean_speech": output_dir / "clean_speech.wav",
        "tone_only": output_dir / "tone_only.wav",
        "silence": output_dir / "silence.wav",
        "speech_plus_tone": output_dir / "speech_plus_tone.wav",
    }
    shutil.copyfile(source_path, outputs["clean_speech"])
    write_pcm16(outputs["tone_only"], params.framerate, tone)
    write_pcm16(outputs["silence"], params.framerate, silence)
    write_pcm16(outputs["speech_plus_tone"], params.framerate, mixed)
    by_id = {item["fixture_id"]: item for item in plan["fixtures"]}
    records = []
    for fixture_id, path in outputs.items():
        records.append({**by_id[fixture_id], "path": str(path.resolve()), "sha256": sha256_file(path), "bytes": path.stat().st_size, "sample_rate_hz": params.framerate, "channels": 1, "frame_count": params.nframes})
    manifest = {
        "schema_version": "wave64.aqa.audio_semantic_alignment_calibration_fixture_manifest.v1",
        "classification": "PROSPECTIVE_FIXTURE_MATRIX_BUILT_RUNTIME_MODELS_NOT_EXECUTED",
        "plan_sha256": sha256_file(plan_path),
        "source_sha256": plan["source"]["sha256"],
        "transcript": plan["source"]["transcript"],
        "fixtures": records,
        "authority": {"semantic_calibration": False, "forced_alignment": False, "operational": False, "product_promotion": False},
    }
    manifest_path = output_dir / "fixture_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.plan.resolve(), args.repository_root.resolve(), args.output_dir.resolve())
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"classification": result["classification"], "fixture_count": len(result["fixtures"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
