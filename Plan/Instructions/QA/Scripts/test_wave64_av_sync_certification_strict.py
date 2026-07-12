#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
import wave
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable
from unittest import mock

from jsonschema import Draft202012Validator

import av

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_av_sync_certification.py"
REQUEST_SCHEMA_PATH = REPO_ROOT / "Plan/08_SCHEMAS/wave64_av_sync_measurement_packet.schema.json"
REPORT_SCHEMA_PATH = REPO_ROOT / "Plan/08_SCHEMAS/wave64_av_sync_certification_report.schema.json"
REGISTRY_PATH = REPO_ROOT / "Plan/10_REGISTRIES/wave64_av_sync_gate_rules.json"
RUNTIME_ARTIFACTS_DIR = REPO_ROOT / "runtime_artifacts"

EVALUATOR_MODULE_NAME = "wave64_av_sync_evaluator_under_test"
EVALUATOR_SPEC = importlib.util.spec_from_file_location(EVALUATOR_MODULE_NAME, SCRIPT_PATH)
if EVALUATOR_SPEC is None or EVALUATOR_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"unable to load evaluator module from {SCRIPT_PATH}")
EVALUATOR = importlib.util.module_from_spec(EVALUATOR_SPEC)
sys.modules[EVALUATOR_MODULE_NAME] = EVALUATOR
EVALUATOR_SPEC.loader.exec_module(EVALUATOR)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _wav_metrics(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        channels = int(handle.getnchannels())
        sample_rate = int(handle.getframerate())
        sample_width = int(handle.getsampwidth())
        frame_count = int(handle.getnframes())
        payload = handle.readframes(frame_count)
    return {
        "channels": channels,
        "sample_rate_hz": sample_rate,
        "sample_width_bytes": sample_width,
        "frame_count": frame_count,
        "bytes": len(payload),
        "duration_seconds": frame_count / float(sample_rate),
        "sha256_pcm": hashlib.sha256(payload).hexdigest(),
    }


def _artifact_binding(path: Path, media_type: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "path": str(path.resolve()),
        "sha256": _sha256(path),
    }
    if media_type is not None:
        payload["bytes"] = path.stat().st_size
        payload["media_type"] = media_type
    return payload


def _write_pcm_wav(
    path: Path,
    *,
    seconds: float = 12.0 / 24.0,
    sample_rate: int = 16000,
    amplitude: float = 0.2,
    frequency_hz: float = 440.0,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(round(seconds * sample_rate))
    max_sample = 32767
    pcm = bytearray()
    for idx in range(frame_count):
        value = int(max_sample * amplitude * math.sin(2.0 * math.pi * frequency_hz * (idx / float(sample_rate))))
        if value > max_sample:
            value = max_sample
        if value < -max_sample:
            value = -max_sample
        pcm.extend(int(value).to_bytes(2, byteorder="little", signed=True))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(pcm))
    return {
        "path": str(path.resolve()),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _fill_gray_frame(frame: Any, index: int) -> None:
    plane = frame.planes[0]
    width = int(frame.width)
    height = int(frame.height)
    stride = int(plane.line_size)
    payload = bytearray()
    for y in range(height):
        for x in range(width):
            payload.append((index * 13 + x * 7 + y * 3) % 256)
        if stride > width:
            payload.extend(b"\x00" * (stride - width))
    plane.update(bytes(payload))


def _fill_rgb_frame(frame: Any, index: int) -> None:
    plane = frame.planes[0]
    width = int(frame.width)
    height = int(frame.height)
    stride = int(plane.line_size)
    payload = bytearray()
    for y in range(height):
        for x in range(width):
            payload.extend(
                (
                    (index * 17 + x * 9 + y * 2) % 256,
                    (index * 5 + x * 3 + y * 11) % 256,
                    (index * 13 + x * 2 + y * 7) % 256,
                )
            )
        if stride > width * 3:
            payload.extend(b"\x00" * (stride - width * 3))
    plane.update(bytes(payload))


def _write_source_video(
    path: Path,
    *,
    frame_count: int = 12,
    width: int = 16,
    height: int = 16,
    fps: int = 24,
    seed_offset: int = 0,
    color: bool = False,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    container = av.open(str(path), mode="w")
    try:
        stream = container.add_stream("ffv1", rate=fps)
        stream.width = width
        stream.height = height
        stream.pix_fmt = "yuv444p" if color else "gray"
        for idx in range(frame_count):
            frame = av.VideoFrame(width, height, "rgb24" if color else "gray")
            if color:
                _fill_rgb_frame(frame, idx + seed_offset)
            else:
                _fill_gray_frame(frame, idx + seed_offset)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    finally:
        container.close()
    return {
        "path": str(path.resolve()),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "frame_count": frame_count,
        "fps": fps,
        "width": width,
        "height": height,
    }


def _write_irregular_video(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    container = av.open(str(path), mode="w")
    try:
        stream = container.add_stream("ffv1", rate=24)
        stream.width = 16
        stream.height = 16
        stream.pix_fmt = "gray"
        stream.time_base = Fraction(1, 1000)
        for idx, pts in enumerate((0, 40, 80, 160)):
            frame = av.VideoFrame(16, 16, "gray")
            _fill_gray_frame(frame, idx)
            frame.pts = pts
            frame.time_base = Fraction(1, 1000)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    finally:
        container.close()


def _read_wav_pcm_bytes(path: Path) -> tuple[int, bytes]:
    with wave.open(str(path), "rb") as handle:
        sample_rate = int(handle.getframerate())
        frame_count = int(handle.getnframes())
        if int(handle.getnchannels()) != 1 or int(handle.getsampwidth()) != 2:
            raise ValueError("fixture WAV must be mono s16")
        payload = handle.readframes(frame_count)
    return sample_rate, payload


def _write_mux(
    path: Path,
    source_video_path: Path,
    source_audio_path: Path,
    *,
    video_source_override: Path | None = None,
    audio_source_override: Path | None = None,
    include_extra_audio_stream: bool = False,
    audio_start_offset_samples: int = 0,
    output_audio_rate: int = 16000,
    output_audio_channels: int = 1,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    source_for_video = video_source_override or source_video_path
    source_for_audio = audio_source_override or source_audio_path

    video_input = av.open(str(source_for_video))
    try:
        stream_info = video_input.streams.video[0]
        fps = stream_info.average_rate if stream_info.average_rate is not None else Fraction(24, 1)
        width = int(stream_info.codec_context.width or stream_info.width)
        height = int(stream_info.codec_context.height or stream_info.height)
        input_sample_rate, audio_bytes = _read_wav_pcm_bytes(source_for_audio)
        if output_audio_channels == 2:
            stereo = bytearray()
            for idx in range(0, len(audio_bytes), 2):
                sample = audio_bytes[idx : idx + 2]
                stereo.extend(sample)
                stereo.extend(sample)
            audio_bytes = bytes(stereo)
        bytes_per_sample = output_audio_channels * 2
        total_samples = len(audio_bytes) // bytes_per_sample
        layout = "mono" if output_audio_channels == 1 else "stereo"

        out = av.open(str(path), mode="w")
        out_video = out.add_stream("ffv1", rate=fps)
        out_video.width = width
        out_video.height = height
        out_video.pix_fmt = "gray"
        audio_stream = out.add_stream("pcm_s16le", rate=output_audio_rate)
        audio_stream.layout = layout
        audio_stream.time_base = Fraction(1, output_audio_rate)
        extra_stream = None
        if include_extra_audio_stream:
            extra_stream = out.add_stream("pcm_s16le", rate=output_audio_rate)
            extra_stream.layout = layout
            extra_stream.time_base = Fraction(1, output_audio_rate)

        packets: list[Any] = []
        for frame in video_input.decode(video=0):
            gray = frame.reformat(format="gray")
            for packet in out_video.encode(gray):
                packets.append(packet)
        packets.extend(out_video.encode(None))

        def encode_stream(stream: Any, pts_offset: int) -> None:
            chunk = 512
            for offset in range(0, total_samples, chunk):
                count = min(chunk, total_samples - offset)
                frame = av.AudioFrame(format="s16", layout=layout, samples=count)
                frame.sample_rate = output_audio_rate
                frame.time_base = Fraction(1, output_audio_rate)
                frame.pts = offset + pts_offset
                start = offset * bytes_per_sample
                end = (offset + count) * bytes_per_sample
                frame.planes[0].update(audio_bytes[start:end])
                packets.extend(stream.encode(frame))
            packets.extend(stream.encode(None))

        encode_stream(audio_stream, audio_start_offset_samples)
        if extra_stream is not None:
            encode_stream(extra_stream, audio_start_offset_samples)

        def packet_time(packet: Any) -> float:
            timestamp = packet.dts if packet.dts is not None else packet.pts
            return float(timestamp * packet.time_base) if timestamp is not None else 0.0

        for packet in sorted(packets, key=packet_time):
            out.mux(packet)
    finally:
        video_input.close()
        if "out" in locals():
            out.close()

    return {
        "path": str(path.resolve()),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "input_sample_rate_hz": input_sample_rate,
        "output_sample_rate_hz": output_audio_rate,
    }


def _run_eval(request_path: Path, output_path: Path, *, root: Path | None = None) -> subprocess.CompletedProcess[str]:
    argv = [
        sys.executable,
        str(SCRIPT_PATH),
        "--root",
        str(root if root is not None else REPO_ROOT),
        "--input",
        str(request_path),
        "--output",
        str(output_path),
    ]
    return subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True, check=False)


class Wave64AvSyncCertificationStrictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.request_schema = json.loads(REQUEST_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.report_schema = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.request_validator = Draft202012Validator(cls.request_schema)
        cls.report_validator = Draft202012Validator(cls.report_schema)
        cls.registry_hash = _sha256(REGISTRY_PATH)
        cls.fixture_measurement_sha = hashlib.sha256("wave64-fixture-measurement-model".encode("utf-8")).hexdigest()
        cls.fixture_playback_sha = hashlib.sha256("wave64-fixture-playback-model".encode("utf-8")).hexdigest()
        cls.fixture_runtime_sha = hashlib.sha256("wave64-fixture-runtime-model".encode("utf-8")).hexdigest()

    def setUp(self) -> None:
        RUNTIME_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        self.tempdir = tempfile.TemporaryDirectory(dir=RUNTIME_ARTIFACTS_DIR)
        self.tmpdir = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.assertEqual(_sha256(REGISTRY_PATH), self.registry_hash)
        self.tempdir.cleanup()

    def _write_case(self, *, synthetic: bool, evidence_origin: str) -> dict[str, Any]:
        source_video = _write_source_video(self.tmpdir / "source_video.mkv")
        source_audio = _write_pcm_wav(self.tmpdir / "source_audio.wav")
        final_mux = _write_mux(
            self.tmpdir / "final_mux.mkv",
            Path(source_video["path"]),
            Path(source_audio["path"]),
            output_audio_rate=16000,
            output_audio_channels=1,
        )
        audio_metrics = _wav_metrics(Path(source_audio["path"]))

        wave30_event = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave30_audio_event_manifest",
            "event_manifest_version": 1,
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "is_synthetic": synthetic,
            "production_proof": {
                "runtime_proof_present": False,
                "audio_review_present": False,
                "certified_for_release": False,
            },
            "taxonomy_registry_path": "Plan/10_REGISTRIES/wave30_audio_event_taxonomy.json",
            "taxonomy_registry_sha256": hashlib.sha256(b"wave30-taxonomy").hexdigest(),
            "audio_event_count": 1,
            "required_lanes": ["foley"],
            "audio_events": [
                {
                    "audio_event_id": "audio_evt_001",
                    "scene_id": "scene_001",
                    "shot_id": "shot_001",
                    "event_type": "clothing_foley",
                    "sync_class": "frame_exact",
                    "purpose": "contact rustle",
                    "source_event_id": "src_evt_001",
                    "start_seconds": 6.0 / 24.0,
                    "end_seconds": 10.0 / 24.0,
                    "expected_video_frame_range": {
                        "start_frame": 6,
                        "end_frame": 10,
                        "frame_rate": 24.0,
                    },
                    "qa_rules": ["rule_sync"],
                    "layer": "foley",
                    "routing": {"lane": "foley"},
                    "subject_binding": {
                        "binding_type": "character",
                        "character_id": "char_a",
                        "object_id": None,
                    },
                    "artifact": {
                        "path": str(Path(source_audio["path"]).resolve()),
                        "sha256": source_audio["sha256"],
                        "bytes": source_audio["bytes"],
                        "duration_seconds": round(audio_metrics["duration_seconds"], 6),
                        "sample_rate_hz": int(audio_metrics["sample_rate_hz"]),
                        "channels": int(audio_metrics["channels"]),
                        "sample_width_bytes": int(audio_metrics["sample_width_bytes"]),
                        "frame_count": int(audio_metrics["frame_count"]),
                    },
                    "synthetic_state": {
                        "synthetic_origin": "synthetic_fixture" if synthetic else "captured_live",
                        "production_proof_claimed": False,
                    },
                }
            ],
            "artifact_manifest": {
                "source_input_path": str((self.tmpdir / "wave30_input.json").resolve()),
                "source_input_sha256": hashlib.sha256(b"wave30-input").hexdigest(),
            },
            "av_sync_binding": {"frame_rate": 24.0, "sync_scope": "event_level"},
        }
        wave30_event_path = self.tmpdir / "wave30_event_manifest.json"
        _write_json(wave30_event_path, wave30_event)

        placeholder_runtime = self.tmpdir / "wave30_runtime_placeholder.json"
        placeholder_review = self.tmpdir / "wave30_review_placeholder.json"
        _write_json(placeholder_runtime, {"ok": True})
        _write_json(placeholder_review, {"ok": True})
        wave30_mix = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave30_audio_mix_manifest",
            "mix_manifest_version": 1,
            "run_id": "run_001",
            "mix_id": "mix_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "is_synthetic": synthetic,
            "event_manifest_bindings": [
                {
                    "path": str(wave30_event_path.resolve()),
                    "sha256": _sha256(wave30_event_path),
                }
            ],
            "mixdown_artifact": {
                "path": str(Path(source_audio["path"]).resolve()),
                "sha256": source_audio["sha256"],
                "bytes": source_audio["bytes"],
            },
            "mix_technical": {
                "duration_seconds": round(audio_metrics["duration_seconds"], 6),
                "sample_rate_hz": int(audio_metrics["sample_rate_hz"]),
                "channels": int(audio_metrics["channels"]),
                "channel_layout": "mono",
                "sample_width_bytes": int(audio_metrics["sample_width_bytes"]),
                "frame_count": int(audio_metrics["frame_count"]),
            },
            "mix_event_metadata": [
                {
                    "audio_event_id": "audio_evt_001",
                    "gain_db": -3.0,
                    "pan": 0.0,
                    "spatial_position": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "distance_meters": 1.0,
                }
            ],
            "mix_loudness": {"integrated_lufs": -18.0, "true_peak_dbtp": -3.0, "clipping_detected": False},
            "dialogue_ducking": {"enabled": False, "duck_db": -6.0, "recovery_ms": 250},
            "av_sync_evidence": {"frame_rate": 24.0, "start_frame": 6, "end_frame": 10, "frame_offset": 0},
            "runtime_proof": {
                "proof_kind": "runtime",
                "path": str(placeholder_runtime.resolve()),
                "sha256": _sha256(placeholder_runtime),
            },
            "audio_review": {
                "proof_kind": "audio_review",
                "path": str(placeholder_review.resolve()),
                "sha256": _sha256(placeholder_review),
            },
            "production_state": {
                "runtime_proof_present": False,
                "audio_review_present": False,
                "certified_for_release": False,
            },
            "promotion_decision": "block",
        }
        wave30_mix_path = self.tmpdir / "wave30_mix_manifest.json"
        _write_json(wave30_mix_path, wave30_mix)

        measurement = {
            "schema_name": "wave64_av_sync_anchor_measurement_proof",
            "proof_kind": "anchor_measurement",
            "engine": "fixture_anchor_engine",
            "model": "fixture_anchor_model",
            "model_version": "2026.fixture",
            "model_sha256": self.fixture_measurement_sha,
            "authority_id": "wave64_fixture_anchor_lab",
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
            "evidence_origin": evidence_origin,
            "source_video_sha256": source_video["sha256"],
            "source_audio_sha256": source_audio["sha256"],
            "mux_sha256": final_mux["sha256"],
            "anchors": [
                {
                    "audio_event_id": "audio_evt_001",
                    "source_event_id": "src_evt_001",
                    "sync_class": "frame_exact",
                    "expected_start_frame": 6,
                    "expected_end_frame": 10,
                    "observed_frame": 8,
                    "observed_time_seconds": 8.0 / 24.0,
                    "observed_owner_id": "char_a",
                }
            ],
        }
        measurement_path = self.tmpdir / "measurement_proof.json"
        _write_json(measurement_path, measurement)

        playback = {
            "schema_name": "wave64_av_sync_playback_proof",
            "proof_kind": "av_sync_playback_review",
            "engine": "fixture_playback_engine",
            "model": "fixture_playback_model",
            "model_version": "2026.fixture",
            "model_sha256": self.fixture_playback_sha,
            "authority_id": "wave64_fixture_playback_lab",
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
            "evidence_origin": evidence_origin,
            "source_video_sha256": source_video["sha256"],
            "source_audio_sha256": source_audio["sha256"],
            "mux_sha256": final_mux["sha256"],
            "measurement_proof_sha256": _sha256(measurement_path),
            "review_results": ["PASS"],
            "self_authorized": False,
        }
        playback_path = self.tmpdir / "playback_proof.json"
        _write_json(playback_path, playback)

        runtime = {
            "schema_name": "wave64_production_runtime_proof",
            "proof_kind": "production_runtime",
            "engine": "fixture_runtime_engine",
            "model": "fixture_runtime_model",
            "model_version": "2026.fixture",
            "model_sha256": self.fixture_runtime_sha,
            "authority_id": "wave64_fixture_runtime_lab",
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
            "evidence_origin": evidence_origin,
            "source_video_sha256": source_video["sha256"],
            "source_audio_sha256": source_audio["sha256"],
            "mux_sha256": final_mux["sha256"],
            "measurement_proof_sha256": _sha256(measurement_path),
            "review_results": ["PASS"],
            "self_authorized": False,
        }
        runtime_path = self.tmpdir / "runtime_proof.json"
        _write_json(runtime_path, runtime)

        bundle = {
            "schema_name": "wave64_av_sync_production_authority_bundle",
            "proof_kind": "production_av_sync_authority",
            "bundle_version": 1,
            "bundle_id": "bundle_001",
            "authority_id": "wave64_authority_board",
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
            "evidence_origin": evidence_origin,
            "source_video_sha256": source_video["sha256"],
            "source_audio_sha256": source_audio["sha256"],
            "mux_sha256": final_mux["sha256"],
            "measurement_proof_sha256": _sha256(measurement_path),
            "playback_proof_sha256": _sha256(playback_path),
            "runtime_proof_sha256": _sha256(runtime_path),
            "self_authorized": False,
        }
        bundle_path = self.tmpdir / "production_bundle.json"
        _write_json(bundle_path, bundle)

        request = {
            "schema_name": "wave64_av_sync_measurement_packet",
            "packet_version": 1,
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
            "evidence_origin": evidence_origin,
            "source_video_artifact": _artifact_binding(Path(source_video["path"]), "video/x-matroska"),
            "source_audio_mix_artifact": _artifact_binding(Path(source_audio["path"]), "audio/wav"),
            "final_mux_artifact": _artifact_binding(Path(final_mux["path"]), "video/x-matroska"),
            "wave30_event_manifest_binding": _artifact_binding(wave30_event_path),
            "wave30_mix_manifest_binding": _artifact_binding(wave30_mix_path),
            "observed_anchor_measurement_proof_binding": _artifact_binding(measurement_path),
            "playback_proof_binding": _artifact_binding(playback_path),
            "runtime_proof_binding": _artifact_binding(runtime_path),
            "production_certification_bundle_binding": _artifact_binding(bundle_path),
            "caller_claimed_overall_pass": True,
        }
        return {
            "request": request,
            "paths": {
                "source_video": Path(source_video["path"]),
                "source_audio": Path(source_audio["path"]),
                "final_mux": Path(final_mux["path"]),
                "wave30_event": wave30_event_path,
                "wave30_mix": wave30_mix_path,
                "measurement": measurement_path,
                "playback": playback_path,
                "runtime": runtime_path,
                "bundle": bundle_path,
            },
        }

    def _rebuild_hash_chain(self, case: dict[str, Any]) -> None:
        request = case["request"]
        paths = case["paths"]
        source_video = paths["source_video"]
        source_audio = paths["source_audio"]
        final_mux = paths["final_mux"]
        event_path = paths["wave30_event"]
        mix_path = paths["wave30_mix"]
        measurement_path = paths["measurement"]
        playback_path = paths["playback"]
        runtime_path = paths["runtime"]
        bundle_path = paths["bundle"]

        mix_payload = json.loads(mix_path.read_text(encoding="utf-8"))
        mix_payload["event_manifest_bindings"] = [_artifact_binding(event_path)]
        mix_payload["mixdown_artifact"] = {
            "path": str(source_audio.resolve()),
            "sha256": _sha256(source_audio),
            "bytes": source_audio.stat().st_size,
        }
        _write_json(mix_path, mix_payload)

        request["source_video_artifact"] = _artifact_binding(source_video, "video/x-matroska")
        request["source_audio_mix_artifact"] = _artifact_binding(source_audio, "audio/wav")
        request["final_mux_artifact"] = _artifact_binding(final_mux, "video/x-matroska")
        request["wave30_event_manifest_binding"] = _artifact_binding(event_path)
        request["wave30_mix_manifest_binding"] = _artifact_binding(mix_path)
        request["observed_anchor_measurement_proof_binding"] = _artifact_binding(measurement_path)

        measurement_payload = json.loads(measurement_path.read_text(encoding="utf-8"))
        measurement_payload["run_id"] = request["run_id"]
        measurement_payload["scene_id"] = request["scene_id"]
        measurement_payload["shot_id"] = request["shot_id"]
        measurement_payload["take_id"] = request["take_id"]
        measurement_payload["is_synthetic"] = request["is_synthetic"]
        measurement_payload["evidence_origin"] = request["evidence_origin"]
        measurement_payload["source_video_sha256"] = request["source_video_artifact"]["sha256"]
        measurement_payload["source_audio_sha256"] = request["source_audio_mix_artifact"]["sha256"]
        measurement_payload["mux_sha256"] = request["final_mux_artifact"]["sha256"]
        _write_json(measurement_path, measurement_payload)
        request["observed_anchor_measurement_proof_binding"] = _artifact_binding(measurement_path)

        for proof_path, binding_key in ((playback_path, "playback_proof_binding"), (runtime_path, "runtime_proof_binding")):
            if request.get(binding_key) is None:
                continue
            proof = json.loads(proof_path.read_text(encoding="utf-8"))
            proof["run_id"] = request["run_id"]
            proof["scene_id"] = request["scene_id"]
            proof["shot_id"] = request["shot_id"]
            proof["take_id"] = request["take_id"]
            proof["is_synthetic"] = request["is_synthetic"]
            proof["evidence_origin"] = request["evidence_origin"]
            proof["source_video_sha256"] = request["source_video_artifact"]["sha256"]
            proof["source_audio_sha256"] = request["source_audio_mix_artifact"]["sha256"]
            proof["mux_sha256"] = request["final_mux_artifact"]["sha256"]
            proof["measurement_proof_sha256"] = _sha256(measurement_path)
            _write_json(proof_path, proof)
            request[binding_key] = _artifact_binding(proof_path)

        if request.get("production_certification_bundle_binding") is not None:
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            bundle["run_id"] = request["run_id"]
            bundle["scene_id"] = request["scene_id"]
            bundle["shot_id"] = request["shot_id"]
            bundle["take_id"] = request["take_id"]
            bundle["is_synthetic"] = request["is_synthetic"]
            bundle["evidence_origin"] = request["evidence_origin"]
            bundle["source_video_sha256"] = request["source_video_artifact"]["sha256"]
            bundle["source_audio_sha256"] = request["source_audio_mix_artifact"]["sha256"]
            bundle["mux_sha256"] = request["final_mux_artifact"]["sha256"]
            bundle["measurement_proof_sha256"] = _sha256(measurement_path)
            bundle["playback_proof_sha256"] = _sha256(playback_path)
            bundle["runtime_proof_sha256"] = _sha256(runtime_path)
            _write_json(bundle_path, bundle)
            request["production_certification_bundle_binding"] = _artifact_binding(bundle_path)

    def _write_request_and_validate_schema(self, request_path: Path, request: dict[str, Any]) -> None:
        _write_json(request_path, request)
        errors = sorted(self.request_validator.iter_errors(request), key=lambda item: list(item.path))
        self.assertFalse(errors, msg=f"request schema errors: {[item.message for item in errors]}")

    def _run_case(self, request: dict[str, Any], output_name: str = "report.json") -> tuple[subprocess.CompletedProcess[str], Path]:
        request_path = self.tmpdir / "request.json"
        output_path = self.tmpdir / output_name
        self._write_request_and_validate_schema(request_path, request)
        result = _run_eval(request_path, output_path)
        return result, output_path

    def _assert_report_schema(self, output_path: Path) -> dict[str, Any]:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        errors = sorted(self.report_validator.iter_errors(payload), key=lambda item: list(item.path))
        self.assertFalse(errors, msg=f"report schema errors: {[item.message for item in errors]}")
        return payload

    def _mutate_measurement_proof(self, case: dict[str, Any], mutate: Callable[[dict[str, Any]], None]) -> None:
        measurement_path = case["paths"]["measurement"]
        initial = json.loads(measurement_path.read_text(encoding="utf-8"))
        mutate(initial)
        _write_json(measurement_path, initial)
        self._rebuild_hash_chain(case)
        updated = json.loads(measurement_path.read_text(encoding="utf-8"))
        mutate(updated)
        _write_json(measurement_path, updated)
        case["request"]["observed_anchor_measurement_proof_binding"] = _artifact_binding(measurement_path)

    def test_coherent_synthetic_packet_exit_two(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["sync_offset_threshold"]["status"], "PASS")
        self.assertEqual(report["gates"]["drift_check"]["status"], "PASS")
        self.assertEqual(report["gates"]["mux_manifest"]["status"], "PASS")
        self.assertEqual(report["gates"]["production_runtime_proof"]["status"], "BLOCKED")
        self.assertFalse(report["overall_pass"])

    def test_coherent_hand_authored_relabel_packet_exit_two(self) -> None:
        case = self._write_case(synthetic=False, evidence_origin="hand_authored_relabel")
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_owner_alignment"]["status"], "BLOCKED")
        self.assertFalse(report["overall_pass"])

    def test_color_loss_fails_full_color_video_lineage(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        _write_source_video(case["paths"]["source_video"], color=True)
        _write_mux(
            case["paths"]["final_mux"],
            case["paths"]["source_video"],
            case["paths"]["source_audio"],
        )
        self._rebuild_hash_chain(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["mux_manifest"]["status"], "FAIL")
        self.assertIn(
            "mux video decoded sequence hash mismatch against source video",
            report["gates"]["mux_manifest"]["blockers"],
        )

    def test_irregular_video_endpoint_uses_decoded_last_frame_duration(self) -> None:
        path = self.tmpdir / "irregular_video.mkv"
        _write_irregular_video(path)
        container = av.open(str(path))
        try:
            stream = container.streams.video[0]
            frames = list(container.decode(video=0))
            self.assertGreaterEqual(len(frames), 2)
            last = frames[-1]
            expected_end = float(last.pts * last.time_base) + float(last.duration * last.time_base)
            cfr_end = float(last.pts * last.time_base) + (1.0 / float(stream.average_rate))
        finally:
            container.close()
        self.assertGreater(abs(expected_end - cfr_end), 1e-4)
        metrics = EVALUATOR._decode_video_container(path, "irregular_video")
        self.assertAlmostEqual(float(metrics["end_timestamp_seconds"]), expected_end, places=6)

    def test_missing_mux_frame_timestamp_fails_offset_gate(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        source_metrics = EVALUATOR._decode_video_container(case["paths"]["source_video"], "source")
        mux_metrics = EVALUATOR._decode_video_container(case["paths"]["final_mux"], "mux")
        mux_metrics["missing_frame_pts_count"] = 1
        mux_metrics["first_pts_seconds"] = 0.0
        request_path = self.tmpdir / "missing_pts_request.json"
        output_path = self.tmpdir / "missing_pts_report.json"
        self._write_request_and_validate_schema(request_path, case["request"])
        with mock.patch.object(EVALUATOR, "_decode_video_container", side_effect=[source_metrics, mux_metrics]):
            return_code = EVALUATOR.evaluate(REPO_ROOT, request_path, output_path)
        self.assertEqual(return_code, 2)
        report = self._assert_report_schema(output_path)
        self.assertEqual(report["gates"]["sync_offset_threshold"]["status"], "FAIL")
        self.assertIn(
            "final_mux_video has missing frame timestamps",
            report["gates"]["sync_offset_threshold"]["blockers"],
        )

    def test_wave30_frame_offset_contradiction_fails_offset_gate(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        mix = json.loads(case["paths"]["wave30_mix"].read_text(encoding="utf-8"))
        mix["av_sync_evidence"]["frame_offset"] = 10
        _write_json(case["paths"]["wave30_mix"], mix)
        self._rebuild_hash_chain(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["sync_offset_threshold"]["status"], "FAIL")
        self.assertIn(
            "wave30 mix av_sync_evidence frame_offset contradicts decoded AV start offset",
            report["gates"]["sync_offset_threshold"]["blockers"],
        )

    def test_anchor_beyond_decoded_mux_timeline_fails(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        event = json.loads(case["paths"]["wave30_event"].read_text(encoding="utf-8"))
        event["audio_events"][0]["end_seconds"] = 12.0 / 24.0
        event["audio_events"][0]["expected_video_frame_range"]["end_frame"] = 12
        _write_json(case["paths"]["wave30_event"], event)
        mix = json.loads(case["paths"]["wave30_mix"].read_text(encoding="utf-8"))
        mix["av_sync_evidence"]["end_frame"] = 12
        _write_json(case["paths"]["wave30_mix"], mix)
        measurement = json.loads(case["paths"]["measurement"].read_text(encoding="utf-8"))
        measurement["anchors"][0]["expected_end_frame"] = 12
        measurement["anchors"][0]["observed_frame"] = 12
        measurement["anchors"][0]["observed_time_seconds"] = 12.0 / 24.0
        _write_json(case["paths"]["measurement"], measurement)
        self._rebuild_hash_chain(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_owner_alignment"]["status"], "FAIL")
        self.assertTrue(
            any("decoded mux" in blocker for blocker in report["gates"]["event_owner_alignment"]["blockers"])
        )

    def test_sync_offset_threshold_fail(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        _write_mux(
            case["paths"]["final_mux"],
            case["paths"]["source_video"],
            case["paths"]["source_audio"],
            audio_start_offset_samples=1600,
        )
        self._rebuild_hash_chain(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["sync_offset_threshold"]["status"], "FAIL")

    def test_extra_audio_stream_fails_mux_manifest(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        _write_mux(
            case["paths"]["final_mux"],
            case["paths"]["source_video"],
            case["paths"]["source_audio"],
            include_extra_audio_stream=True,
        )
        self._rebuild_hash_chain(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["mux_manifest"]["status"], "FAIL")

    def test_unrelated_audio_content_fails_mux_manifest(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        unrelated_audio = _write_pcm_wav(self.tmpdir / "unrelated_audio.wav", frequency_hz=880.0, amplitude=0.3)
        _write_mux(
            case["paths"]["final_mux"],
            case["paths"]["source_video"],
            case["paths"]["source_audio"],
            audio_source_override=Path(unrelated_audio["path"]),
        )
        self._rebuild_hash_chain(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["mux_manifest"]["status"], "FAIL")

    def test_unrelated_video_content_fails_mux_manifest(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        other_video = _write_source_video(self.tmpdir / "other_video.mkv", seed_offset=99)
        _write_mux(
            case["paths"]["final_mux"],
            case["paths"]["source_video"],
            case["paths"]["source_audio"],
            video_source_override=Path(other_video["path"]),
        )
        self._rebuild_hash_chain(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["mux_manifest"]["status"], "FAIL")

    def test_audio_sample_rate_and_channel_mismatch_fails_mux_manifest(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        _write_mux(
            case["paths"]["final_mux"],
            case["paths"]["source_video"],
            case["paths"]["source_audio"],
            output_audio_rate=8000,
            output_audio_channels=2,
        )
        self._rebuild_hash_chain(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["mux_manifest"]["status"], "FAIL")

    def test_measurement_producer_not_allowlisted_blocks(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")

        def set_unallowlisted_model(proof: dict[str, Any]) -> None:
            proof["model"] = "unknown_model"

        self._mutate_measurement_proof(case, set_unallowlisted_model)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_owner_alignment"]["status"], "BLOCKED")

    def test_anchor_owner_mismatch_fails(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")

        def set_owner_mismatch(proof: dict[str, Any]) -> None:
            proof["anchors"][0]["observed_owner_id"] = "char_b"

        self._mutate_measurement_proof(case, set_owner_mismatch)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_owner_alignment"]["status"], "FAIL")

    def test_anchor_duplicate_missing_and_extra_fail(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        proof = json.loads(case["paths"]["measurement"].read_text(encoding="utf-8"))
        proof["anchors"].append(copy.deepcopy(proof["anchors"][0]))
        proof["anchors"].append(
            {
                "audio_event_id": "unknown_evt",
                "source_event_id": "unknown_src",
                "sync_class": "frame_exact",
                "expected_start_frame": 0,
                "expected_end_frame": 0,
                "observed_frame": 0,
                "observed_time_seconds": 0.0,
                "observed_owner_id": "n/a",
            }
        )
        _write_json(case["paths"]["measurement"], proof)
        self._rebuild_hash_chain(case)
        proof = json.loads(case["paths"]["measurement"].read_text(encoding="utf-8"))
        proof["anchors"] = proof["anchors"][1:]
        _write_json(case["paths"]["measurement"], proof)
        case["request"]["observed_anchor_measurement_proof_binding"] = _artifact_binding(case["paths"]["measurement"])
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_owner_alignment"]["status"], "FAIL")

    def test_playback_proof_missing_blocks_gate(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        case["request"]["playback_proof_binding"] = None
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["av_review_record"]["status"], "BLOCKED")

    def test_runtime_proof_missing_blocks_gate(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        case["request"]["runtime_proof_binding"] = None
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_runtime_proof"]["status"], "BLOCKED")

    def test_playback_proof_hash_mismatch_fails_gate(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        playback = json.loads(case["paths"]["playback"].read_text(encoding="utf-8"))
        playback["mux_sha256"] = "f" * 64
        _write_json(case["paths"]["playback"], playback)
        case["request"]["playback_proof_binding"] = _artifact_binding(case["paths"]["playback"])
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["av_review_record"]["status"], "FAIL")

    def test_playback_self_authorization_fails_gate(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        playback = json.loads(case["paths"]["playback"].read_text(encoding="utf-8"))
        playback["self_authorized"] = True
        _write_json(case["paths"]["playback"], playback)
        self._rebuild_hash_chain(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["av_review_record"]["status"], "FAIL")
        self.assertIn("playback_proof self_authorized is forbidden", report["gates"]["av_review_record"]["blockers"])

    def test_runtime_producer_unapproved_blocks_gate(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        runtime = json.loads(case["paths"]["runtime"].read_text(encoding="utf-8"))
        runtime["model_sha256"] = "f" * 64
        _write_json(case["paths"]["runtime"], runtime)
        case["request"]["runtime_proof_binding"] = _artifact_binding(case["paths"]["runtime"])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["runtime_proof_sha256"] = _sha256(case["paths"]["runtime"])
        _write_json(case["paths"]["bundle"], bundle)
        case["request"]["production_certification_bundle_binding"] = _artifact_binding(case["paths"]["bundle"])
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_runtime_proof"]["status"], "BLOCKED")

    def test_runtime_self_authorization_fails_gate(self) -> None:
        case = self._write_case(synthetic=False, evidence_origin="technical_capture")
        runtime = json.loads(case["paths"]["runtime"].read_text(encoding="utf-8"))
        runtime["self_authorized"] = True
        _write_json(case["paths"]["runtime"], runtime)
        self._rebuild_hash_chain(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_runtime_proof"]["status"], "FAIL")
        self.assertIn(
            "runtime_proof self_authorized is forbidden",
            report["gates"]["production_runtime_proof"]["blockers"],
        )

    def test_production_bundle_self_authorization_is_rejected(self) -> None:
        case = self._write_case(synthetic=False, evidence_origin="technical_capture")
        request = case["request"]
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["self_authorized"] = True
        _, _, blockers = EVALUATOR._validate_production_bundle(
            bundle,
            run_id=request["run_id"],
            scene_id=request["scene_id"],
            shot_id=request["shot_id"],
            take_id=request["take_id"],
            is_synthetic=request["is_synthetic"],
            evidence_origin=request["evidence_origin"],
            source_video_sha256=request["source_video_artifact"]["sha256"],
            source_audio_sha256=request["source_audio_mix_artifact"]["sha256"],
            mux_sha256=request["final_mux_artifact"]["sha256"],
            measurement_proof_sha256=request["observed_anchor_measurement_proof_binding"]["sha256"],
            playback_proof_sha256=request["playback_proof_binding"]["sha256"],
            runtime_proof_sha256=request["runtime_proof_binding"]["sha256"],
            forbid_self_authorization=True,
        )
        self.assertIn("production_certification_bundle self_authorized is forbidden", blockers)

    def test_registry_rejects_cross_role_authority_collision(self) -> None:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        registry["producer_rules"]["playback_allowlist"][0]["authority_id"] = registry["producer_rules"][
            "measurement_allowlist"
        ][0]["authority_id"]
        with self.assertRaisesRegex(EVALUATOR.InvalidInputError, "cannot authorize multiple proof roles"):
            EVALUATOR._parse_gate_registry(registry)

    def test_production_authority_bundle_empty_allowlist_blocks(self) -> None:
        case = self._write_case(synthetic=False, evidence_origin="technical_capture")
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_av_sync_authority"]["status"], "BLOCKED")

    def test_tampered_hash_invalid_exit_one(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        case["request"]["source_video_artifact"]["sha256"] = "0" * 64
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_malformed_mux_container_invalid_exit_one(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        mux_path = case["paths"]["final_mux"]
        original = mux_path.read_bytes()
        mux_path.write_bytes(original[:100])
        self._rebuild_hash_chain(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_unknown_request_key_invalid(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        case["request"]["unexpected"] = True
        request_path = self.tmpdir / "bad_request.json"
        output_path = self.tmpdir / "report.json"
        _write_json(request_path, case["request"])
        result = _run_eval(request_path, output_path)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_nonfinite_value_invalid(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        request_path = self.tmpdir / "nonfinite_request.json"
        output_path = self.tmpdir / "report.json"
        text = json.dumps(case["request"], indent=2, sort_keys=True)
        text = text.replace('"caller_claimed_overall_pass": true', '"caller_claimed_overall_pass": NaN')
        request_path.write_text(text, encoding="utf-8")
        result = _run_eval(request_path, output_path)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_root_escape_override_and_output_collision_invalid(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        case["request"]["source_video_artifact"]["path"] = "/tmp/escape.mkv"
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

        case2 = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        request_path = self.tmpdir / "request2.json"
        output_path = self.tmpdir / "report2.json"
        self._write_request_and_validate_schema(request_path, case2["request"])
        bad_root = _run_eval(request_path, output_path, root=self.tmpdir)
        self.assertEqual(bad_root.returncode, 1)

        collision = _run_eval(request_path, request_path)
        self.assertEqual(collision.returncode, 1)

    def test_transactional_output_preservation(self) -> None:
        case = self._write_case(synthetic=True, evidence_origin="synthetic_fixture")
        request_path = self.tmpdir / "request_atomic.json"
        output_path = self.tmpdir / "report_atomic.json"
        self._write_request_and_validate_schema(request_path, case["request"])
        original_payload = {"keep": True}
        _write_json(output_path, original_payload)
        bad = copy.deepcopy(case["request"])
        bad["wave30_event_manifest_binding"]["sha256"] = "a" * 64
        _write_json(request_path, bad)
        result = _run_eval(request_path, output_path)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), original_payload)

    def test_schema_roundtrip_and_no_current_exit_zero_assertion(self) -> None:
        case = self._write_case(synthetic=False, evidence_origin="technical_capture")
        result, output = self._run_case(case["request"])
        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertFalse(report["overall_pass"])


if __name__ == "__main__":
    unittest.main()
