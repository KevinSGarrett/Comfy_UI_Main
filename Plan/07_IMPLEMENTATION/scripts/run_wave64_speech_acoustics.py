#!/usr/bin/env python3
"""Render bounded Wave64 nonverbal, virtual-mic, and restoration candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


EXPECTED_DRY_SHA256 = "ff8325a1c2f8613d599af69284f5c4693d996a581230ccbbbb1aeba7affa9815"
EXPECTED_INDEX_SHA256 = "7301243a364025dbd23907aee20ee8593d5897caa83d38391026ad42da6d17ec"
EXPECTED_TEXT = "We hold the frame steady and move on the beat."


class AcousticsError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise AcousticsError(f"required file is missing: {path}")
    observed = sha256_file(path)
    if expected_sha256 and observed != expected_sha256.lower():
        raise AcousticsError(f"SHA-256 mismatch for {path}: {observed}")
    return {"path": str(path), "sha256": observed, "bytes": path.stat().st_size}


def find_index_record(index_path: Path, source_sha256: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    with index_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AcousticsError(f"functional index line {line_number} is invalid JSON") from exc
            if isinstance(record, dict) and record.get("sha256") == source_sha256:
                matches.append(record)
    if len(matches) != 1:
        raise AcousticsError(f"expected one functional-index record for {source_sha256}, found {len(matches)}")
    record = matches[0]
    required = {
        "absolute_path", "relative_path", "bytes", "duration_seconds", "format",
        "sample_rate_hz", "channels", "event_type", "role", "intensity_band",
        "sync_class", "license_classification", "attribution", "quality_defects",
        "content_based_suppression",
    }
    missing = sorted(required - record.keys())
    if missing:
        raise AcousticsError(f"functional-index record is incomplete: {','.join(missing)}")
    if record["quality_defects"] or record["content_based_suppression"] is not False:
        raise AcousticsError("functional-index source is defect-marked or suppressed")
    return record


def read_mono(path: Path):
    import numpy as np
    import soundfile as sf

    audio, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
    if audio.size == 0 or sample_rate <= 0 or not np.isfinite(audio).all():
        raise AcousticsError(f"invalid audio payload: {path}")
    return audio.mean(axis=1).astype(np.float64), int(sample_rate)


def resample(audio, source_rate: int, target_rate: int):
    from scipy.signal import resample_poly

    if source_rate == target_rate:
        return audio.copy()
    divisor = math.gcd(source_rate, target_rate)
    return resample_poly(audio, target_rate // divisor, source_rate // divisor)


def peak_limit(audio, ceiling: float = 0.95):
    import numpy as np

    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > ceiling:
        return audio * (ceiling / peak), ceiling / peak
    return audio, 1.0


def fade_edges(audio, sample_rate: int, milliseconds: float = 10.0):
    import numpy as np

    count = min(audio.size // 2, max(1, int(round(sample_rate * milliseconds / 1000.0))))
    if count:
        fade = np.linspace(0.0, 1.0, count, endpoint=False)
        audio = audio.copy()
        audio[:count] *= fade
        audio[-count:] *= fade[::-1]
    return audio


def render_nonverbal(audio, sample_rate: int, target_rate: int = 24000):
    import numpy as np

    output = resample(audio, sample_rate, target_rate)
    output = fade_edges(output, target_rate)
    peak = float(np.max(np.abs(output)))
    gain = min(1.0, 0.72 / max(peak, 1e-9))
    output = output * gain
    return output, {"target_rate_hz": target_rate, "edge_fade_ms": 10.0, "peak_ceiling": 0.72, "linear_gain": gain}


def _compress_static(audio, threshold_db: float = -18.0, ratio: float = 2.0):
    import numpy as np

    threshold = 10.0 ** (threshold_db / 20.0)
    magnitude = np.abs(audio)
    compressed = magnitude.copy()
    above = magnitude > threshold
    compressed[above] = threshold * np.power(magnitude[above] / threshold, 1.0 / ratio)
    return np.sign(audio) * compressed


def render_virtual_microphone(audio, sample_rate: int):
    import numpy as np
    from scipy.signal import butter, sosfiltfilt

    high_pass = butter(2, 68.0, btype="highpass", fs=sample_rate, output="sos")
    low_band = butter(2, 220.0, btype="lowpass", fs=sample_rate, output="sos")
    filtered = sosfiltfilt(high_pass, audio)
    proximity = sosfiltfilt(low_band, filtered)
    close_mic = filtered + 0.08 * proximity
    compressed = _compress_static(close_mic, -18.0, 2.0)
    saturated = np.tanh(1.08 * compressed) / np.tanh(1.08)
    output, limiter_gain = peak_limit(saturated, 0.95)
    return output, {
        "recipe_id": "wave64_close_condenser_v1",
        "high_pass_hz": 68.0,
        "proximity_low_band_hz": 220.0,
        "proximity_mix": 0.08,
        "compressor_threshold_dbfs": -18.0,
        "compressor_ratio": 2.0,
        "soft_saturation_drive": 1.08,
        "peak_ceiling": 0.95,
        "limiter_linear_gain": limiter_gain,
        "nondestructive_source_retained": True,
    }


def restore_speech(audio, sample_rate: int):
    import numpy as np
    from scipy.signal import butter, medfilt, sosfiltfilt

    output = audio.astype(np.float64, copy=True)
    output -= float(np.mean(output))
    local_median = medfilt(output, kernel_size=5)
    residual = np.abs(output - local_median)
    median = float(np.median(residual))
    mad = float(np.median(np.abs(residual - median)))
    threshold = max(0.20, median + 60.0 * max(mad, 1e-8))
    candidate = residual > threshold
    isolated = candidate & ~np.roll(candidate, 1) & ~np.roll(candidate, -1)
    isolated[0] = False
    isolated[-1] = False
    clicks = np.flatnonzero(isolated)
    repair_ratio = clicks.size / max(1, output.size)
    if repair_ratio > 0.001:
        raise AcousticsError(f"de-click repair ratio is not bounded: {repair_ratio:.9f}")
    for index in clicks:
        output[index] = local_median[index]

    high_pass = butter(2, 62.0, btype="highpass", fs=sample_rate, output="sos")
    output = sosfiltfilt(high_pass, output)
    low_pass = butter(4, 5500.0, btype="lowpass", fs=sample_rate, output="sos")
    low = sosfiltfilt(low_pass, output)
    high = output - low
    total_rms = float(np.sqrt(np.mean(np.square(output))))
    high_rms = float(np.sqrt(np.mean(np.square(high))))
    high_ratio = high_rms / max(total_rms, 1e-9)
    deess_mix = 0.12 if high_ratio > 0.22 else 0.0
    output = output - deess_mix * high
    output, limiter_gain = peak_limit(output, 0.95)
    return output, {
        "recipe_id": "wave64_bounded_speech_restoration_v1",
        "dc_removed": True,
        "declick_detector": "isolated_five_sample_median_residual_v1",
        "declick_threshold_floor": 0.20,
        "declick_threshold_median_plus_mad": 60.0,
        "declick_samples_repaired": int(clicks.size),
        "declick_repair_sample_ratio": round(repair_ratio, 9),
        "declick_max_repair_sample_ratio": 0.001,
        "deplosive_high_pass_hz": 62.0,
        "deess_crossover_hz": 5500.0,
        "pre_deess_high_band_rms_ratio": round(high_ratio, 9),
        "deess_mix": deess_mix,
        "peak_ceiling": 0.95,
        "limiter_linear_gain": limiter_gain,
        "source_and_intermediate_retained": True,
    }


def audio_metrics(audio, sample_rate: int) -> dict[str, Any]:
    import numpy as np

    return {
        "sample_rate_hz": int(sample_rate),
        "samples": int(audio.size),
        "channels": 1,
        "duration_seconds": round(audio.size / sample_rate, 9),
        "peak_absolute": round(float(np.max(np.abs(audio))), 9),
        "rms": round(float(np.sqrt(np.mean(np.square(audio)))), 9),
        "clipping_ratio": round(float(np.mean(np.abs(audio) >= 0.999)), 9),
        "finite": bool(np.isfinite(audio).all()),
    }


def write_wav_new(path: Path, audio, sample_rate: int) -> dict[str, Any]:
    import soundfile as sf

    if path.exists():
        raise AcousticsError(f"immutable output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sample_rate, subtype="PCM_16")
    return bind(path)


def write_json_new(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        raise AcousticsError(f"immutable output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)
    return bind(path)


def run(args: argparse.Namespace) -> dict[str, Any]:
    import numpy
    import scipy
    import soundfile

    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise AcousticsError(f"immutable output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    dry_binding = bind(args.dry_speech, EXPECTED_DRY_SHA256)
    index_binding = bind(args.functional_index, EXPECTED_INDEX_SHA256)
    source_binding = bind(args.nonverbal_source, args.nonverbal_source_sha256)
    record = find_index_record(args.functional_index.resolve(), source_binding["sha256"])
    if Path(record["absolute_path"]).resolve() != args.nonverbal_source.resolve():
        raise AcousticsError("functional-index absolute path does not match the requested source")
    if record["event_type"] not in {"breath", "voice_reaction"} or record["role"] != "voice":
        raise AcousticsError("selected source is not an indexed nonverbal voice event")

    nonverbal_source, nonverbal_rate = read_mono(args.nonverbal_source)
    dry, dry_rate = read_mono(args.dry_speech)
    nonverbal, nonverbal_recipe = render_nonverbal(nonverbal_source, nonverbal_rate)
    virtual_mic, mic_recipe = render_virtual_microphone(dry, dry_rate)
    restored, restoration_recipe = restore_speech(virtual_mic, dry_rate)

    nonverbal_path = output_dir / "indexed_nonverbal_voice_candidate.wav"
    mic_path = output_dir / "qwen3_clone_virtual_microphone.wav"
    restored_path = output_dir / "qwen3_clone_restored.wav"
    outputs = {
        "nonverbal_candidate": write_wav_new(nonverbal_path, nonverbal, 24000),
        "virtual_microphone_candidate": write_wav_new(mic_path, virtual_mic, dry_rate),
        "restored_candidate": write_wav_new(restored_path, restored, dry_rate),
    }
    outputs["nonverbal_candidate"]["audio"] = audio_metrics(nonverbal, 24000)
    outputs["virtual_microphone_candidate"]["audio"] = audio_metrics(virtual_mic, dry_rate)
    outputs["restored_candidate"]["audio"] = audio_metrics(restored, dry_rate)
    manifest = {
        "schema_version": "1.0",
        "artifact_type": "wave64_speech_rows128_130_runtime_manifest",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "classification": "WAVE64_ROWS128_130_RUNTIME_RENDERED_AUTOMATED_QA_PENDING",
        "dry_speech": {**dry_binding, "expected_text": EXPECTED_TEXT, "media_mutated": False},
        "nonverbal_source": {
            **source_binding,
            "functional_index": index_binding,
            "record": record,
            "character_identity": "unassigned_reference_voice",
            "production_character_authority": False,
        },
        "recipes": {"nonverbal": nonverbal_recipe, "virtual_microphone": mic_recipe, "restoration": restoration_recipe},
        "outputs": outputs,
        "runtime": {
            "python": platform.python_version(),
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "soundfile": soundfile.__version__,
        },
        "boundaries": {
            "source_bytes_modified": False,
            "dry_speech_modified_in_place": False,
            "subjective_playback_review_complete": False,
            "nonverbal_character_identity_authorized": False,
            "production_promotion_claimed": False,
            "content_based_suppression": False,
            "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False,
        },
    }
    manifest_path = output_dir / "wave64_speech_rows128_130_runtime_manifest.json"
    manifest_binding = write_json_new(manifest_path, manifest)
    return {"classification": manifest["classification"], "manifest": manifest_binding, "outputs": outputs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-speech", type=Path, required=True)
    parser.add_argument("--functional-index", type=Path, required=True)
    parser.add_argument("--nonverbal-source", type=Path, required=True)
    parser.add_argument("--nonverbal-source-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        print(json.dumps({"classification": "WAVE64_ROWS128_130_RUNTIME_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
