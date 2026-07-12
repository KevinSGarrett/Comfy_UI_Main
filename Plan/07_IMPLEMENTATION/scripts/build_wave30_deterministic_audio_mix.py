#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import uuid
import wave
from array import array
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON: {value}")))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _pcm16_mono(path: Path) -> tuple[int, list[int]]:
    try:
        with wave.open(str(path), "rb") as wav:
            if wav.getcomptype() != "NONE" or wav.getsampwidth() != 2 or not 1 <= wav.getnchannels() <= 16:
                raise ValueError("source WAV must be uncompressed 1-16 channel PCM16")
            rate, channels, frames = wav.getframerate(), wav.getnchannels(), wav.getnframes()
            raw = wav.readframes(frames)
    except wave.Error as exc:
        raise ValueError(f"invalid PCM WAV {path}: {exc}") from exc
    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    if len(samples) != frames * channels:
        raise ValueError(f"decoded sample count mismatch: {path}")
    mono = [int(round(sum(samples[i : i + channels]) / float(channels))) for i in range(0, len(samples), channels)]
    return rate, mono


def _dbfs(value: float, *, floor: float) -> float:
    if value <= 0:
        return floor
    return max(floor, min(0.0, 20.0 * math.log10(value / 32767.0)))


def _build(event_path: Path, root: Path, temp_dir: Path, final_dir: Path, mix_id: str | None) -> dict[str, Any]:
    event_schema = _load(root / "Plan/08_SCHEMAS/wave30_audio_event_manifest.schema.json")
    mix_schema = _load(root / "Plan/08_SCHEMAS/wave30_audio_mix_manifest.schema.json")
    registry_path = root / "Plan/10_REGISTRIES/wave30_deterministic_pcm_mixer.json"
    registry = _load(registry_path)
    event = _load(event_path)
    Draft202012Validator(event_schema).validate(event)
    if event.get("production_proof", {}).get("certified_for_release"):
        raise ValueError("builder cannot consume an already certified event manifest")
    events = sorted(event["audio_events"], key=lambda item: (item["start_seconds"], item["audio_event_id"]))
    sample_rate: int | None = None
    decoded: list[tuple[dict[str, Any], list[int]]] = []
    max_end = 0
    for source in events:
        artifact = source["artifact"]
        source_path = Path(artifact["path"]).resolve()
        if not source_path.is_file() or source_path.stat().st_size != artifact["bytes"] or _sha(source_path) != artifact["sha256"]:
            raise ValueError(f"source artifact binding mismatch: {source['audio_event_id']}")
        rate, samples = _pcm16_mono(source_path)
        if rate != artifact["sample_rate_hz"] or len(samples) != artifact["frame_count"]:
            raise ValueError(f"source PCM metadata mismatch: {source['audio_event_id']}")
        if sample_rate is None:
            sample_rate = rate
        elif rate != sample_rate:
            raise ValueError("all source events must share one sample rate; resampling is not implicit")
        start = int(round(float(source["start_seconds"]) * rate))
        expected = int(round((float(source["end_seconds"]) - float(source["start_seconds"])) * rate))
        if abs(expected - len(samples)) > 1:
            raise ValueError(f"source timing mismatch: {source['audio_event_id']}")
        max_end = max(max_end, start + len(samples))
        decoded.append((source, samples))
    if sample_rate is None or max_end <= 0:
        raise ValueError("event manifest has no decodable samples")

    accumulator = [0.0] * max_end
    metadata: list[dict[str, Any]] = []
    gains = registry["layer_gain_db"]
    for source, samples in decoded:
        gain_db = float(gains.get(source["layer"], gains.get(source["event_type"], registry["default_gain_db"])))
        gain = 10.0 ** (gain_db / 20.0)
        start = int(round(float(source["start_seconds"]) * sample_rate))
        for index, sample in enumerate(samples):
            accumulator[start + index] += sample * gain
        metadata.append({
            "audio_event_id": source["audio_event_id"], "gain_db": gain_db, "pan": 0.0,
            "spatial_position": {"x": 0.0, "y": 0.0, "z": 1.0}, "distance_meters": 1.0,
        })
    peak_before = max(abs(value) for value in accumulator)
    clipping = peak_before > 32767.0
    if clipping and not registry["allow_clipped_candidate"]:
        raise ValueError("deterministic mix would clip; adjust explicit registry gains")
    output_samples = array("h", [max(-32768, min(32767, int(round(value)))) for value in accumulator])
    rms = math.sqrt(sum(float(value) ** 2 for value in output_samples) / len(output_samples))
    peak = max(abs(value) for value in output_samples)
    if sys.byteorder != "little":
        output_samples.byteswap()
    mix_path = temp_dir / "mixdown.wav"
    with wave.open(str(mix_path), "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(sample_rate); wav.writeframes(output_samples.tobytes())
    frame_rate = float(event["av_sync_binding"]["frame_rate"])
    duration = len(output_samples) / float(sample_rate)
    pending_runtime = temp_dir / "runtime_proof_pending.json"
    pending_review = temp_dir / "audio_review_pending.json"
    pending = {"status": "pending", "verified": False, "production_proof": False}
    _write_json(pending_runtime, {**pending, "proof_kind": "runtime"})
    _write_json(pending_review, {**pending, "proof_kind": "audio_review"})
    manifest = {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "schema_name": "wave30_audio_mix_manifest",
        "mix_manifest_version": 1, "run_id": event["run_id"], "mix_id": mix_id or f"{event['run_id']}_deterministic_mix",
        "scene_id": event["scene_id"], "shot_id": event["shot_id"], "is_synthetic": bool(event["is_synthetic"]),
        "event_manifest_bindings": [{"path": str(event_path), "sha256": _sha(event_path)}],
        "mixdown_artifact": {"path": str(final_dir / "mixdown.wav"), "sha256": _sha(mix_path), "bytes": mix_path.stat().st_size},
        "mix_technical": {"duration_seconds": round(duration, 6), "sample_rate_hz": sample_rate, "channels": 1,
                          "channel_layout": "mono", "sample_width_bytes": 2, "frame_count": len(output_samples)},
        "mix_event_metadata": metadata,
        "mix_loudness": {"integrated_lufs": round(_dbfs(rms, floor=-70.0), 6),
                         "true_peak_dbtp": round(max(-20.0, _dbfs(float(peak), floor=-20.0)), 6),
                         "clipping_detected": clipping},
        "measurement_methods": {
            "integrated_loudness": registry["loudness_metric"],
            "true_peak": registry["true_peak_metric"],
            "certification_authority": False
        },
        "dialogue_ducking": {"enabled": False, "duck_db": 0.0, "recovery_ms": 0},
        "av_sync_evidence": {"frame_rate": frame_rate, "start_frame": 0,
                             "end_frame": int(round(duration * frame_rate)), "frame_offset": 0},
        "runtime_proof": {"proof_kind": "runtime", "path": str(final_dir / pending_runtime.name), "sha256": _sha(pending_runtime)},
        "audio_review": {"proof_kind": "audio_review", "path": str(final_dir / pending_review.name), "sha256": _sha(pending_review)},
        "production_state": {"runtime_proof_present": False, "audio_review_present": False, "certified_for_release": False},
        "promotion_decision": "block",
    }
    manifest_path = temp_dir / "mix_manifest.json"
    _write_json(manifest_path, manifest)
    Draft202012Validator(mix_schema).validate(manifest)
    build_record = {"schema_version": 1, "status": "technical_candidate_built", "production_evidence": False,
                    "mixer_registry": {"path": str(registry_path), "sha256": _sha(registry_path)},
                    "event_manifest_sha256": _sha(event_path), "mixdown_sha256": _sha(mix_path),
                    "mix_manifest_sha256": _sha(manifest_path), "clipping_detected": clipping,
                    "loudness_values_are_technical_proxies": True, "promotion_claimed": False}
    _write_json(temp_dir / "build_record.json", build_record)
    return {"frame_count": len(output_samples), "sample_rate_hz": sample_rate, "mixdown_sha256": _sha(mix_path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--mix-id")
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    temp = output.parent / f".{output.name}.tmp-{uuid.uuid4().hex}"
    try:
        if output.exists():
            raise ValueError(f"output directory already exists: {output}")
        temp.mkdir(parents=True)
        result = _build(Path(args.event_manifest).resolve(), Path(args.root).resolve(), temp, output, args.mix_id)
        os.replace(temp, output)
    except Exception as exc:
        shutil.rmtree(temp, ignore_errors=True)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "pass", "output_dir": str(output), **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
