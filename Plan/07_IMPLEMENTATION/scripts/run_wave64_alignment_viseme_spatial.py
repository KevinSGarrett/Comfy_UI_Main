#!/usr/bin/env python3
"""Run the bounded Wave64 Rows135, 136, and 138 local runtime packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SOURCE_SHA256 = "ff8325a1c2f8613d599af69284f5c4693d996a581230ccbbbb1aeba7affa9815"
MMS_MODEL_SHA256 = "20ef12963ab4924bef49ac4fc7f58ad5da2ee43b2c11bc8c853c9b90ecdbc680"
TRANSCRIPT = "We hold the frame steady and move on the beat."
MMS_MODEL_URL = "https://dl.fbaipublicfiles.com/mms/torchaudio/ctc_alignment_mling_uroman/model.pt"
MMS_LICENSE = "CC-BY-NC-4.0"
FPS = 24


class RuntimePacketError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind(path: Path, expected_sha256: str | None = None, label: str = "artifact") -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise RuntimePacketError(f"{label} is missing: {path}")
    observed = sha256_file(path)
    if expected_sha256 and observed != expected_sha256.lower():
        raise RuntimePacketError(f"{label} SHA-256 mismatch: {observed}")
    return {"path": str(path), "sha256": observed, "bytes": path.stat().st_size}


def write_json_new(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        raise RuntimePacketError(f"immutable output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)
    return bind(path)


def normalized_words(transcript: str) -> list[str]:
    words = re.findall(r"[a-z']+", transcript.casefold())
    if not words:
        raise RuntimePacketError("transcript has no alignable words")
    return words


def validate_intervals(intervals: Iterable[dict[str, Any]], sample_count: int, label: str) -> None:
    previous_end = 0
    observed = 0
    for interval in intervals:
        start = int(interval["start_sample"])
        end = int(interval["end_sample"])
        confidence = float(interval["confidence"])
        if start < previous_end or end <= start or end > sample_count:
            raise RuntimePacketError(f"{label} intervals are not monotonic and bounded")
        if not 0.0 <= confidence <= 1.0:
            raise RuntimePacketError(f"{label} confidence is outside [0, 1]")
        previous_end = end
        observed += 1
    if observed == 0:
        raise RuntimePacketError(f"{label} intervals are empty")


def align_words(source: Path, transcript: str, model_path: Path, device: str) -> tuple[dict[str, Any], Any, int]:
    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio
    from scipy.signal import resample_poly

    audio, source_rate = sf.read(str(source), dtype="float32", always_2d=True)
    if audio.size == 0 or source_rate <= 0 or not np.isfinite(audio).all():
        raise RuntimePacketError("source audio is empty, non-finite, or has an invalid sample rate")
    mono = audio.mean(axis=1).astype(np.float32, copy=False)
    common = math.gcd(int(source_rate), 16000)
    aligned_audio = resample_poly(mono, 16000 // common, int(source_rate) // common).astype(np.float32)
    waveform = torch.from_numpy(aligned_audio).unsqueeze(0).to(device)

    bundle = torchaudio.pipelines.MMS_FA
    if bundle._path != MMS_MODEL_URL:
        raise RuntimePacketError(f"unexpected MMS_FA model URL: {bundle._path}")
    model = bundle.get_model(dl_kwargs={"model_dir": str(model_path.parent)}).to(device).eval()
    words = normalized_words(transcript)
    tokenized = bundle.get_tokenizer()(words)
    with torch.inference_mode():
        emissions, _ = model(waveform)
    spans = bundle.get_aligner()(emissions[0], tokenized)
    if len(spans) != len(words):
        raise RuntimePacketError("MMS_FA did not return exactly one token-span group per word")

    emission_frames = int(emissions.shape[1])
    source_samples = int(mono.size)
    intervals: list[dict[str, Any]] = []
    for word, word_spans in zip(words, spans):
        if not word_spans:
            raise RuntimePacketError(f"MMS_FA returned an empty span for {word}")
        start_frame = int(word_spans[0].start)
        end_frame = int(word_spans[-1].end)
        start_sample = round(start_frame * source_samples / emission_frames)
        end_sample = round(end_frame * source_samples / emission_frames)
        scores = [float(span.score) for span in word_spans]
        intervals.append({
            "label": word,
            "start_sample": int(start_sample),
            "end_sample": int(end_sample),
            "start_seconds": round(start_sample / source_rate, 9),
            "end_seconds": round(end_sample / source_rate, 9),
            "confidence": round(sum(scores) / len(scores), 9),
            "ctc_start_frame": start_frame,
            "ctc_end_frame": end_frame,
        })
    validate_intervals(intervals, source_samples, "word")
    alignment = {
        "schema_version": "1.0",
        "candidate_id": "W64-QWEN3-BASE-ICL-CLONE-SEED-12401",
        "artifact_sha256": SOURCE_SHA256,
        "sample_rate_hz": int(source_rate),
        "transcript": transcript,
        "normalized_words": words,
        "words": intervals,
        "phonemes": [],
        "coverage": 1.0,
        "monotonic": True,
        "pass": True,
        "alignment_authority": {
            "method": "torchaudio_mms_fa_ctc_grapheme_word_alignment",
            "emission_frame_count": emission_frames,
            "word_timing_runtime_pass": True,
            "grapheme_ctc_runtime_pass": True,
            "phoneme_forced_alignment_pass": False,
            "mfa_style_phoneme_authority": False,
            "whisperx_style_word_authority": False,
            "ambiguous_transform_rejected": True,
        },
    }
    return alignment, mono, int(source_rate)


VISEME_MAP = {
    "SIL": ("sil", 0.0, 0.0),
    "P": ("MBP", 0.05, 0.95), "B": ("MBP", 0.08, 0.9), "M": ("MBP", 0.05, 1.0),
    "F": ("FV", 0.18, 0.65), "V": ("FV", 0.2, 0.62),
    "TH": ("TH", 0.24, 0.35), "DH": ("TH", 0.22, 0.32),
    "S": ("SZ", 0.16, 0.25), "Z": ("SZ", 0.18, 0.25),
    "SH": ("SH", 0.2, 0.42), "ZH": ("SH", 0.22, 0.4),
    "T": ("TD", 0.1, 0.5), "D": ("TD", 0.12, 0.48), "K": ("KG", 0.2, 0.35), "G": ("KG", 0.22, 0.34),
    "L": ("L", 0.28, 0.25), "R": ("R", 0.24, 0.38), "W": ("WQ", 0.18, 0.72), "Y": ("Y", 0.24, 0.18),
    "AA": ("A", 0.82, 0.08), "AE": ("A", 0.75, 0.12), "AH": ("A", 0.62, 0.14), "AO": ("O", 0.7, 0.54),
    "EH": ("E", 0.55, 0.14), "ER": ("R", 0.48, 0.32), "IH": ("I", 0.4, 0.16), "IY": ("I", 0.38, 0.2),
    "OW": ("O", 0.58, 0.68), "UH": ("U", 0.48, 0.58), "UW": ("U", 0.46, 0.78),
}


def compile_viseme_fixture(sample_rate: int, fps: int = FPS) -> dict[str, Any]:
    fixture = ["SIL", "P", "AA", "T", "F", "IH", "S", "M", "OW", "K", "SIL"]
    duration_samples = round(sample_rate * 0.09)
    intervals = []
    for index, phoneme in enumerate(fixture):
        start = index * duration_samples
        end = (index + 1) * duration_samples
        viseme, jaw, lip = VISEME_MAP[phoneme]
        intervals.append({
            "phoneme": phoneme,
            "viseme": viseme,
            "start_sample": start,
            "end_sample": end,
            "start_frame": math.floor(start * fps / sample_rate),
            "end_frame_exclusive": max(math.floor(start * fps / sample_rate) + 1, math.ceil(end * fps / sample_rate)),
            "confidence": 1.0,
            "jaw_open": jaw,
            "lip_closure_or_rounding": lip,
            "coarticulation": {"attack_fraction": 0.2, "release_fraction": 0.2, "cross_interval_overlap": False},
        })
    validate_intervals(
        [{"start_sample": item["start_sample"], "end_sample": item["end_sample"], "confidence": item["confidence"]} for item in intervals],
        len(fixture) * duration_samples,
        "viseme fixture",
    )
    categories = {
        "silence": any(item["phoneme"] == "SIL" for item in intervals),
        "plosive": any(item["phoneme"] in {"P", "B", "T", "D", "K", "G"} for item in intervals),
        "closure": any(item["viseme"] == "MBP" for item in intervals),
        "fricative": any(item["phoneme"] in {"F", "V", "S", "Z", "SH", "ZH", "TH", "DH"} for item in intervals),
        "vowel": any(item["phoneme"] in {"AA", "AE", "AH", "AO", "EH", "ER", "IH", "IY", "OW", "UH", "UW"} for item in intervals),
        "rapid_transition": all(item["end_sample"] - item["start_sample"] <= round(sample_rate * 0.1) for item in intervals),
    }
    return {
        "schema_version": "1.0",
        "compiler_version": "wave64_viseme_coarticulation_v1",
        "fps": fps,
        "input_authority": "DETERMINISTIC_PHONEME_FIXTURE_ONLY",
        "production_phoneme_input_used": False,
        "fixture_runtime_pass": all(categories.values()),
        "fixture_coverage": categories,
        "intervals": intervals,
        "row_complete": False,
        "remaining_blockers": ["production phoneme-alignment authority is not available from Row135"],
    }


def render_spatial(mono, sample_rate: int):
    import numpy as np
    from scipy.signal import butter, sosfilt

    if mono.ndim != 1 or mono.size < sample_rate // 4 or not np.isfinite(mono).all():
        raise RuntimePacketError("spatial input must be finite mono audio at least 250 ms long")
    count = mono.size
    phase = np.linspace(0.0, 1.0, count, dtype=np.float64)
    pan = -0.65 + 1.3 * phase
    distance_m = 1.1 + 1.4 * np.sin(np.pi * phase) ** 2
    elevation_m = 1.45 + 0.35 * np.sin(2.0 * np.pi * phase)
    attenuation = 1.0 / np.maximum(1.0, distance_m)
    left_gain = np.cos((pan + 1.0) * np.pi / 4.0) * attenuation
    right_gain = np.sin((pan + 1.0) * np.pi / 4.0) * attenuation

    occluded = sosfilt(butter(3, 4200.0, btype="lowpass", fs=sample_rate, output="sos"), mono.astype(np.float64))
    elevation_presence = sosfilt(butter(2, 1800.0, btype="highpass", fs=sample_rate, output="sos"), occluded)
    microphone = 0.9 * occluded + 0.1 * elevation_presence * (0.5 + elevation_m / 3.6)
    stereo = np.column_stack((microphone * left_gain, microphone * right_gain))

    for delay_ms, gain, cross in ((17.0, 0.12, False), (31.0, 0.08, True), (47.0, 0.05, False)):
        delay = max(1, round(sample_rate * delay_ms / 1000.0))
        reflected = stereo[:-delay] * gain
        if cross:
            reflected = reflected[:, ::-1]
        stereo[delay:] += reflected
    for delay_ms, gain in ((73.0, 0.035), (113.0, 0.025), (167.0, 0.018)):
        delay = max(1, round(sample_rate * delay_ms / 1000.0))
        stereo[delay:] += stereo[:-delay] * gain

    peak = float(np.max(np.abs(stereo)))
    normalization_gain = 1.0
    if peak > 0.96:
        normalization_gain = 0.96 / peak
        stereo *= normalization_gain
    if not np.isfinite(stereo).all():
        raise RuntimePacketError("spatial renderer produced non-finite samples")
    metadata = {
        "renderer": "wave64_deterministic_stereo_scene_v1",
        "trajectory": {
            "start": {"pan": -0.65, "distance_m": 1.1, "elevation_m": 1.45},
            "mid": {"pan": 0.0, "distance_m": 2.5, "elevation_m": 1.45},
            "end": {"pan": 0.65, "distance_m": 1.1, "elevation_m": 1.45},
        },
        "distance_model": "inverse_distance_clamped_at_1m",
        "occlusion": {"enabled": True, "lowpass_hz": 4200.0, "order": 3},
        "elevation": {"enabled": True, "presence_highpass_hz": 1800.0},
        "early_reflections": [{"delay_ms": 17.0, "gain": 0.12}, {"delay_ms": 31.0, "gain": 0.08}, {"delay_ms": 47.0, "gain": 0.05}],
        "reverb_tail": [{"delay_ms": 73.0, "gain": 0.035}, {"delay_ms": 113.0, "gain": 0.025}, {"delay_ms": 167.0, "gain": 0.018}],
        "microphone_perspective": "occluded_room_listener_v1",
        "normalization_gain": round(normalization_gain, 9),
    }
    return stereo.astype(np.float32), metadata


def canonical_sha256(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def run(args: argparse.Namespace) -> dict[str, Any]:
    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio

    source = args.source_audio.resolve()
    model_path = args.mms_model.resolve()
    source_binding_before = bind(source, SOURCE_SHA256, "immutable Qwen L01 source")
    model_binding = bind(model_path, MMS_MODEL_SHA256, "Torchaudio MMS_FA model")
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise RuntimePacketError(f"immutable output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)

    alignment, mono, sample_rate = align_words(source, TRANSCRIPT, model_path, args.device)
    alignment_path = output_dir / "row135_mms_fa_word_grapheme_alignment.json"
    alignment_binding = write_json_new(alignment_path, alignment)

    viseme = compile_viseme_fixture(sample_rate)
    viseme_path = output_dir / "row136_viseme_coarticulation_fixture.json"
    viseme_binding = write_json_new(viseme_path, viseme)

    spatial, renderer = render_spatial(mono, sample_rate)
    spatial_path = output_dir / "row138_l01_spatial_scene_pcm24_stereo.wav"
    sf.write(str(spatial_path), spatial, sample_rate, subtype="PCM_24")
    spatial_binding = bind(spatial_path)
    decoded, decoded_rate = sf.read(str(spatial_path), dtype="float32", always_2d=True)
    if decoded_rate != sample_rate or decoded.shape != spatial.shape or not np.isfinite(decoded).all():
        raise RuntimePacketError("spatial output decode verification failed")

    source_binding_after = bind(source, SOURCE_SHA256, "immutable Qwen L01 source after render")
    if source_binding_after != source_binding_before:
        raise RuntimePacketError("source binding changed during runtime")
    configuration = {
        "transcript": TRANSCRIPT,
        "fps": FPS,
        "renderer": renderer,
        "source_sha256": SOURCE_SHA256,
        "mms_model_sha256": MMS_MODEL_SHA256,
    }
    manifest = {
        "schema_version": "1.0",
        "artifact_type": "wave64_alignment_viseme_spatial_runtime_manifest",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "classification": "W64_ROWS135_136_138_BOUNDED_RUNTIME_PASS_PRODUCTION_AUTHORITY_BLOCKED",
        "source": {**source_binding_before, "transcript": TRANSCRIPT, "source_unchanged_after_runtime": True},
        "dependencies": {
            "torch": torch.__version__,
            "torchaudio": torchaudio.__version__,
            "mms_fa": {**model_binding, "official_url": MMS_MODEL_URL, "license": MMS_LICENSE},
        },
        "row135": {
            "status": "Blocked_Mandated_Alignment_Assets_And_True_Phoneme_Authority_Pending",
            "runtime_classification": "MMS_FA_L01_WORD_GRAPHEME_RUNTIME_PASS",
            "alignment": alignment_binding,
            "word_alignment_pass": True,
            "phoneme_alignment_pass": False,
            "row_complete": False,
            "required_assets_still_unproven": ["whisper_large_v3_turbo", "pyannote_diarization_community_1", "latentsync_1_6"],
        },
        "row136": {
            "status": "Blocked_Production_Phoneme_Alignment_Input_Pending_Compiler_Runtime_Pass",
            "runtime_classification": "VISEME_COARTICULATION_FIXTURE_RUNTIME_PASS",
            "fixture": viseme_binding,
            "fixture_runtime_pass": bool(viseme["fixture_runtime_pass"]),
            "production_input_pass": False,
            "row_complete": False,
        },
        "row138": {
            "status": "Blocked_Independent_Spatial_Playback_And_Production_Scene_Authority_Pending",
            "runtime_classification": "DETERMINISTIC_SPATIAL_SCENE_RENDER_AUTOMATED_QA_PENDING",
            "output": {**spatial_binding, "sample_rate_hz": sample_rate, "channels": 2, "samples_per_channel": int(spatial.shape[0]), "subtype": "PCM_24"},
            "renderer": renderer,
            "source_unchanged": True,
            "deterministic_configuration_sha256": canonical_sha256(configuration),
            "intelligibility_evaluation_pass": None,
            "speaker_identity_evaluation_pass": None,
            "independent_playback_review_pass": False,
            "production_scene_authority_pass": False,
            "row_complete": False,
        },
        "boundaries": {
            "mms_grapheme_is_phoneme_authority": False,
            "fixture_is_production_alignment": False,
            "automated_metrics_are_human_playback": False,
            "production_ready": False,
            "content_based_suppression": False,
            "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False,
        },
    }
    manifest_binding = write_json_new(output_dir / "wave64_alignment_viseme_spatial_runtime_manifest.json", manifest)
    return {
        "classification": manifest["classification"],
        "manifest": manifest_binding,
        "alignment": alignment_binding,
        "viseme_fixture": viseme_binding,
        "spatial_audio": spatial_binding,
        "word_count": len(alignment["words"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-audio", type=Path, required=True)
    parser.add_argument("--mms-model", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        print(json.dumps({"classification": "W64_ROWS135_136_138_RUNTIME_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
