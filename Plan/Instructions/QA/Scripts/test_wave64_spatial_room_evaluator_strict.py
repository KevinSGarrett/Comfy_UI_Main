#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import math
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_spatial_room_evidence.py"
REQUEST_SCHEMA_PATH = REPO_ROOT / "Plan/08_SCHEMAS/wave64_spatial_room_evidence_bundle.schema.json"
REPORT_SCHEMA_PATH = REPO_ROOT / "Plan/08_SCHEMAS/wave64_spatial_room_evaluator_report.schema.json"
REGISTRY_PATH = REPO_ROOT / "Plan/10_REGISTRIES/wave64_spatial_room_gate_rules.json"
RUNTIME_ARTIFACTS_DIR = REPO_ROOT / "runtime_artifacts"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _pack_sample(sample: int, sample_width: int) -> bytes:
    if sample_width == 1:
        clamped = max(-127, min(127, sample))
        return bytes([clamped + 128])
    if sample_width == 2:
        clamped = max(-32767, min(32767, sample))
        return struct.pack("<h", clamped)
    if sample_width == 3:
        max_val = (1 << 23) - 1
        clamped = max(-max_val, min(max_val, sample))
        return int(clamped).to_bytes(3, "little", signed=True)
    if sample_width == 4:
        max_val = (1 << 31) - 1
        clamped = max(-max_val, min(max_val, sample))
        return struct.pack("<i", clamped)
    raise ValueError(f"unsupported sample_width: {sample_width}")


def _write_pcm_wav(
    path: Path,
    *,
    channels: int = 2,
    seconds: float = 0.8,
    sample_rate: int = 16000,
    sample_width: int = 2,
    amplitude: float = 0.2,
    left_gain: float = 1.0,
    right_gain: float = 1.0,
    frequency_hz: float = 220.0,
    decay: float = 0.0,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(seconds * sample_rate)
    max_sample = 127 if sample_width == 1 else (1 << (8 * sample_width - 1)) - 1
    amp = int(max_sample * amplitude)
    payload = bytearray()
    for frame_index in range(frame_count):
        t = frame_index / float(sample_rate)
        envelope = math.exp(-decay * t) if decay > 0.0 else 1.0
        base = int(amp * envelope * math.sin(2.0 * math.pi * frequency_hz * t))
        if channels == 1:
            payload.extend(_pack_sample(base, sample_width))
        elif channels == 2:
            payload.extend(_pack_sample(int(base * left_gain), sample_width))
            payload.extend(_pack_sample(int(base * right_gain), sample_width))
        else:
            raise ValueError("test helper supports mono or stereo only")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(sample_width)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(payload))
    return {
        "path": str(path.resolve()),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _read_pcm_wav(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        channels = int(handle.getnchannels())
        sample_width = int(handle.getsampwidth())
        sample_rate = int(handle.getframerate())
        frame_count = int(handle.getnframes())
        payload = handle.readframes(frame_count)
    if sample_width == 1:
        samples = [value - 128 for value in payload]
        max_sample = 127
    elif sample_width == 2:
        samples = [item[0] for item in struct.iter_unpack("<h", payload)]
        max_sample = (1 << 15) - 1
    elif sample_width == 3:
        samples = []
        max_sample = (1 << 23) - 1
        for idx in range(0, len(payload), 3):
            chunk = payload[idx : idx + 3]
            suffix = b"\xff" if chunk[2] & 0x80 else b"\x00"
            samples.append(int.from_bytes(chunk + suffix, "little", signed=True))
    elif sample_width == 4:
        samples = [item[0] for item in struct.iter_unpack("<i", payload)]
        max_sample = (1 << 31) - 1
    else:
        raise ValueError(f"unsupported sample_width: {sample_width}")
    return {
        "channels": channels,
        "sample_width": sample_width,
        "sample_rate": sample_rate,
        "frame_count": frame_count,
        "samples": samples,
        "max_sample": max_sample,
    }


def _write_pcm_from_samples(path: Path, pcm: dict[str, Any], samples: list[int]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_width = int(pcm["sample_width"])
    payload = bytearray()
    for sample in samples:
        payload.extend(_pack_sample(int(sample), sample_width))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(int(pcm["channels"]))
        handle.setsampwidth(sample_width)
        handle.setframerate(int(pcm["sample_rate"]))
        handle.writeframes(bytes(payload))
    return {
        "path": str(path.resolve()),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _write_sum_mix(path: Path, spatial_path: Path, ambience_path: Path) -> dict[str, Any]:
    spatial_pcm = _read_pcm_wav(spatial_path)
    ambience_pcm = _read_pcm_wav(ambience_path)
    if (
        spatial_pcm["channels"] != ambience_pcm["channels"]
        or spatial_pcm["sample_width"] != ambience_pcm["sample_width"]
        or spatial_pcm["sample_rate"] != ambience_pcm["sample_rate"]
        or spatial_pcm["frame_count"] != ambience_pcm["frame_count"]
    ):
        raise ValueError("mix inputs must share format")
    max_sample = int(spatial_pcm["max_sample"])
    mixed: list[int] = []
    for spatial_sample, ambience_sample in zip(spatial_pcm["samples"], ambience_pcm["samples"]):
        value = int(spatial_sample) + int(ambience_sample)
        value = max(-max_sample, min(max_sample, value))
        mixed.append(value)
    return _write_pcm_from_samples(path, spatial_pcm, mixed)


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


class Wave64SpatialRoomEvaluatorStrictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.request_schema = json.loads(REQUEST_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.report_schema = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.request_validator = Draft202012Validator(cls.request_schema)
        cls.report_validator = Draft202012Validator(cls.report_schema)
        cls.registry_hash = _sha256(REGISTRY_PATH)

    def setUp(self) -> None:
        RUNTIME_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        self.tempdir = tempfile.TemporaryDirectory(dir=RUNTIME_ARTIFACTS_DIR)
        self.tmpdir = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.assertEqual(_sha256(REGISTRY_PATH), self.registry_hash)
        self.tempdir.cleanup()

    def _refresh_binding(self, request: dict[str, Any], key: str, path: Path) -> None:
        request[key] = {"path": str(path.resolve()), "sha256": _sha256(path)}

    def _refresh_audio_binding(self, request: dict[str, Any], key: str, path: Path) -> None:
        request["audio_artifacts"][key] = {
            "path": str(path.resolve()),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }

    def _refresh_ambience_segment_binding(self, request: dict[str, Any], key: str, path: Path) -> None:
        request["ambience_continuity_evidence"][key] = {
            "path": str(path.resolve()),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }

    def _sync_proofs_and_bundle(self, case: dict[str, Any]) -> None:
        request = case["request"]
        paths = case["paths"]
        self._refresh_binding(request, "wave31_spatial_mix_binding", paths["wave31_spatial_mix"])
        self._refresh_binding(request, "wave31_room_acoustics_binding", paths["wave31_room_acoustics"])
        self._refresh_audio_binding(request, "dry_dialogue", paths["dry_dialogue"])
        self._refresh_audio_binding(request, "spatial_dialogue", paths["spatial_dialogue"])
        self._refresh_audio_binding(request, "ambience_bed", paths["ambience_bed"])
        self._refresh_audio_binding(request, "final_mix", paths["final_mix"])
        self._refresh_ambience_segment_binding(request, "previous_segment", paths["ambience_previous_segment"])
        self._refresh_ambience_segment_binding(request, "current_segment", paths["ambience_current_segment"])

        playback = json.loads(paths["playback_proof"].read_text(encoding="utf-8"))
        runtime = json.loads(paths["runtime_proof"].read_text(encoding="utf-8"))
        bundle = json.loads(paths["production_bundle"].read_text(encoding="utf-8"))
        for proof in (playback, runtime):
            proof["run_id"] = request["run_id"]
            proof["scene_id"] = request["scene_id"]
            proof["shot_id"] = request["shot_id"]
            proof["take_id"] = request["take_id"]
            proof["is_synthetic"] = request["is_synthetic"]
            proof["evidence_origin"] = request["evidence_origin"]
            proof["artifact_hashes"] = {
                "dry_dialogue_sha256": request["audio_artifacts"]["dry_dialogue"]["sha256"],
                "spatial_dialogue_sha256": request["audio_artifacts"]["spatial_dialogue"]["sha256"],
                "ambience_bed_sha256": request["audio_artifacts"]["ambience_bed"]["sha256"],
                "final_mix_sha256": request["audio_artifacts"]["final_mix"]["sha256"],
            }
        _write_json(paths["playback_proof"], playback)
        _write_json(paths["runtime_proof"], runtime)

        bundle["run_id"] = request["run_id"]
        bundle["scene_id"] = request["scene_id"]
        bundle["shot_id"] = request["shot_id"]
        bundle["take_id"] = request["take_id"]
        bundle["is_synthetic"] = request["is_synthetic"]
        bundle["evidence_origin"] = request["evidence_origin"]
        bundle["playback_proof_sha256"] = _sha256(paths["playback_proof"])
        bundle["runtime_proof_sha256"] = _sha256(paths["runtime_proof"])
        bundle["artifact_hashes"] = {
            "dry_dialogue_sha256": request["audio_artifacts"]["dry_dialogue"]["sha256"],
            "spatial_dialogue_sha256": request["audio_artifacts"]["spatial_dialogue"]["sha256"],
            "ambience_bed_sha256": request["audio_artifacts"]["ambience_bed"]["sha256"],
            "final_mix_sha256": request["audio_artifacts"]["final_mix"]["sha256"],
        }
        _write_json(paths["production_bundle"], bundle)

        self._refresh_binding(request, "playback_proof_binding", paths["playback_proof"])
        self._refresh_binding(request, "runtime_proof_binding", paths["runtime_proof"])
        self._refresh_binding(request, "production_authority_bundle_binding", paths["production_bundle"])

    def _build_case(self, *, synthetic: bool, evidence_origin: str) -> dict[str, Any]:
        wave31_spatial_mix = {
            "mix_id": "mix_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "audio_events": ["dialogue_001"],
            "room_profile": "small_soft_room",
            "camera_listener_state": {"camera": "present", "listener": "present"},
            "spatial_layers": [
                {
                    "source_id": "dialogue_source",
                    "pan": 0.65,
                    "gain": 0.6,
                    "distance": 1.41,
                    "reverb_profile": "short_warm_room",
                    "occlusion_profile": "none",
                    "sync_time": 0.0,
                }
            ],
            "qa_scores": {"spatial": 0.95},
            "promotion_decision": "hold",
            "run_id": "run_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
        }
        wave31_room = {
            "room_profile_id": "small_soft_room",
            "environment_type": "interior",
            "room_size": "small",
            "surface_materials": ["fabric", "carpet", "soft_furniture"],
            "furniture_density": "medium",
            "reverb_profile": "short_warm_room",
            "ambience_profile": "quiet_room_tone",
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
        }
        wave31_spatial_mix_path = self.tmpdir / "wave31_spatial_mix.json"
        wave31_room_path = self.tmpdir / "wave31_room.json"
        _write_json(wave31_spatial_mix_path, wave31_spatial_mix)
        _write_json(wave31_room_path, wave31_room)

        dry = _write_pcm_wav(self.tmpdir / "dry_dialogue.wav", amplitude=0.2, left_gain=1.0, right_gain=1.0, decay=0.0)
        spatial = _write_pcm_wav(
            self.tmpdir / "spatial_dialogue.wav",
            amplitude=0.6,
            left_gain=0.17,
            right_gain=0.83,
            decay=18.0,
        )
        ambience = _write_pcm_wav(self.tmpdir / "ambience_bed.wav", amplitude=0.02, left_gain=1.0, right_gain=1.0)
        final_mix = _write_sum_mix(self.tmpdir / "final_mix.wav", Path(spatial["path"]), Path(ambience["path"]))
        ambience_prev = _write_pcm_wav(self.tmpdir / "ambience_prev.wav", amplitude=0.08, left_gain=1.0, right_gain=1.0)
        ambience_curr = _write_pcm_wav(self.tmpdir / "ambience_curr.wav", amplitude=0.081, left_gain=1.0, right_gain=1.0)
        if synthetic:
            playback_engine = "fixture_playback_engine"
            playback_model = "fixture_playback_model"
            playback_model_version = "2026.fixture"
            playback_model_sha = hashlib.sha256(b"fixture-playback").hexdigest()
            runtime_engine = "fixture_runtime_engine"
            runtime_model = "fixture_runtime_model"
            runtime_model_version = "2026.fixture"
            runtime_model_sha = hashlib.sha256(b"fixture-runtime").hexdigest()
        else:
            playback_engine = "playback_engine"
            playback_model = "playback_model"
            playback_model_version = "2026.07"
            playback_model_sha = hashlib.sha256(b"playback").hexdigest()
            runtime_engine = "runtime_engine"
            runtime_model = "runtime_model"
            runtime_model_version = "2026.07"
            runtime_model_sha = hashlib.sha256(b"runtime").hexdigest()

        playback_proof = {
            "schema_name": "wave64_spatial_audio_playback_proof",
            "proof_kind": "spatial_audio_playback_review",
            "engine": playback_engine,
            "model": playback_model,
            "model_version": playback_model_version,
            "model_sha256": playback_model_sha,
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
            "evidence_origin": evidence_origin,
            "artifact_hashes": {
                "dry_dialogue_sha256": dry["sha256"],
                "spatial_dialogue_sha256": spatial["sha256"],
                "ambience_bed_sha256": ambience["sha256"],
                "final_mix_sha256": final_mix["sha256"],
            },
            "review_results": ["PASS"],
            "self_authorized": False,
        }
        runtime_proof = {
            "schema_name": "wave64_production_runtime_proof",
            "proof_kind": "production_runtime",
            "engine": runtime_engine,
            "model": runtime_model,
            "model_version": runtime_model_version,
            "model_sha256": runtime_model_sha,
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
            "evidence_origin": evidence_origin,
            "artifact_hashes": {
                "dry_dialogue_sha256": dry["sha256"],
                "spatial_dialogue_sha256": spatial["sha256"],
                "ambience_bed_sha256": ambience["sha256"],
                "final_mix_sha256": final_mix["sha256"],
            },
            "review_results": ["PASS"],
            "self_authorized": False,
        }
        playback_path = self.tmpdir / "playback_proof.json"
        runtime_path = self.tmpdir / "runtime_proof.json"
        _write_json(playback_path, playback_proof)
        _write_json(runtime_path, runtime_proof)

        bundle = {
            "schema_name": "wave64_production_spatial_room_authority_bundle",
            "proof_kind": "production_spatial_room_authority",
            "bundle_version": 1,
            "bundle_id": "bundle_001",
            "authority_id": "authority_wave64",
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
            "evidence_origin": evidence_origin,
            "playback_proof_sha256": _sha256(playback_path),
            "runtime_proof_sha256": _sha256(runtime_path),
            "artifact_hashes": {
                "dry_dialogue_sha256": dry["sha256"],
                "spatial_dialogue_sha256": spatial["sha256"],
                "ambience_bed_sha256": ambience["sha256"],
                "final_mix_sha256": final_mix["sha256"],
            },
            "self_authorized": False,
        }
        bundle_path = self.tmpdir / "production_bundle.json"
        _write_json(bundle_path, bundle)

        request = {
            "schema_name": "wave64_spatial_room_evidence_bundle",
            "bundle_version": 1,
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
            "evidence_origin": evidence_origin,
            "listener_position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "camera_position": {"x": 0.2, "y": 0.0, "z": 0.0},
            "camera_orientation": {
                "right_unit_vector": {"x": 1.0, "y": 0.0, "z": 0.0},
                "forward_unit_vector": {"x": 0.0, "y": 1.0, "z": 0.0},
            },
            "source_position": {"x": 1.0, "y": 1.0, "z": 0.0},
            "wave31_spatial_mix_binding": {"path": str(wave31_spatial_mix_path.resolve()), "sha256": _sha256(wave31_spatial_mix_path)},
            "wave31_room_acoustics_binding": {"path": str(wave31_room_path.resolve()), "sha256": _sha256(wave31_room_path)},
            "audio_artifacts": {
                "dry_dialogue": dry,
                "spatial_dialogue": spatial,
                "ambience_bed": ambience,
                "final_mix": final_mix,
            },
            "ambience_continuity_evidence": {
                "previous_segment": ambience_prev,
                "current_segment": ambience_curr,
                "hard_cut_contract": None,
            },
            "playback_proof_binding": {"path": str(playback_path.resolve()), "sha256": _sha256(playback_path)},
            "runtime_proof_binding": {"path": str(runtime_path.resolve()), "sha256": _sha256(runtime_path)},
            "production_authority_bundle_binding": {"path": str(bundle_path.resolve()), "sha256": _sha256(bundle_path)},
            "threshold_overrides": {
                "max_camera_listener_distance_delta": 1.0,
                "max_pan_error": 0.25,
                "min_attenuation_ratio": 0.3,
                "max_attenuation_ratio": 0.95,
                "min_rt60_seconds": 0.2,
                "max_rt60_seconds": 0.8,
                "max_reverb_tail_error_seconds": 0.1,
                "max_ambience_drift": 0.2,
                "min_dialogue_to_ambience_db": 3.0,
                "max_clipping_ratio": 0.0008,
                "max_stereo_balance_delta": 0.25,
                "max_duration_delta_seconds": 0.03,
            },
        }

        return {
            "request": request,
            "paths": {
                "wave31_spatial_mix": wave31_spatial_mix_path,
                "wave31_room_acoustics": wave31_room_path,
                "dry_dialogue": Path(dry["path"]),
                "spatial_dialogue": Path(spatial["path"]),
                "ambience_bed": Path(ambience["path"]),
                "final_mix": Path(final_mix["path"]),
                "ambience_previous_segment": Path(ambience_prev["path"]),
                "ambience_current_segment": Path(ambience_curr["path"]),
                "playback_proof": playback_path,
                "runtime_proof": runtime_path,
                "production_bundle": bundle_path,
            },
        }

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

    def test_coherent_synthetic_technical_packet_exit_two(self) -> None:
        case = self._build_case(synthetic=True, evidence_origin="synthetic_fixture")
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_runtime_proof"]["status"], "BLOCKED")
        self.assertFalse(report["overall_pass"])

    def test_coherent_hand_authored_non_synthetic_relabel_exit_two(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="hand_authored_relabel")
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_spatial_room_authority"]["status"], "BLOCKED")
        self.assertFalse(report["overall_pass"])

    def test_spatial_pan_defect_fails_spatial_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        _write_pcm_wav(case["paths"]["spatial_dialogue"], amplitude=0.21, left_gain=0.9, right_gain=0.1, decay=20.0)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["spatial_position_check"]["status"], "FAIL")

    def test_spatial_distance_exceeds_registry_fails(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["request"]["source_position"]["x"] = 100.0
        case["request"]["source_position"]["y"] = 0.0
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["spatial_position_check"]["status"], "FAIL")

    def test_camera_listener_mismatch_fails_spatial_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["request"]["camera_position"] = {"x": 5.0, "y": 0.0, "z": 0.0}
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["spatial_position_check"]["status"], "FAIL")

    def test_attenuation_ratio_defect_fails_spatial_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        _write_pcm_wav(case["paths"]["spatial_dialogue"], amplitude=0.02, left_gain=0.17, right_gain=0.83, decay=20.0)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["spatial_position_check"]["status"], "FAIL")

    def test_non_unit_camera_orientation_invalid(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["request"]["camera_orientation"]["right_unit_vector"] = {"x": 2.0, "y": 0.0, "z": 0.0}
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertFalse(output.exists())

    def test_camera_right_vector_controls_pan_expectation(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["request"]["source_position"] = {"x": 1.0, "y": 0.0, "z": 0.0}
        case["request"]["camera_orientation"] = {
            "right_unit_vector": {"x": 1.0, "y": 0.0, "z": 0.0},
            "forward_unit_vector": {"x": 0.0, "y": 1.0, "z": 0.0},
        }
        _write_pcm_wav(case["paths"]["spatial_dialogue"], amplitude=0.6, left_gain=0.05, right_gain=0.95, decay=18.0)
        _write_sum_mix(case["paths"]["final_mix"], case["paths"]["spatial_dialogue"], case["paths"]["ambience_bed"])
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["spatial_position_check"]["status"], "PASS")

    def test_rotated_camera_right_vector_changes_pan_and_fails(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["request"]["source_position"] = {"x": 1.0, "y": 0.0, "z": 0.0}
        case["request"]["camera_orientation"] = {
            "right_unit_vector": {"x": 0.0, "y": 1.0, "z": 0.0},
            "forward_unit_vector": {"x": -1.0, "y": 0.0, "z": 0.0},
        }
        _write_pcm_wav(case["paths"]["spatial_dialogue"], amplitude=0.6, left_gain=0.05, right_gain=0.95, decay=18.0)
        _write_sum_mix(case["paths"]["final_mix"], case["paths"]["spatial_dialogue"], case["paths"]["ambience_bed"])
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["spatial_position_check"]["status"], "FAIL")

    def test_unknown_room_profile_fails_room_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        room = json.loads(case["paths"]["wave31_room_acoustics"].read_text(encoding="utf-8"))
        room["room_profile_id"] = "unknown_room"
        _write_json(case["paths"]["wave31_room_acoustics"], room)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["room_reverb_check"]["status"], "FAIL")

    def test_unknown_reverb_or_material_combo_fails_room_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        room = json.loads(case["paths"]["wave31_room_acoustics"].read_text(encoding="utf-8"))
        room["reverb_profile"] = "nonexistent_reverb"
        room["surface_materials"] = ["fabric", "metal"]
        _write_json(case["paths"]["wave31_room_acoustics"], room)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["room_reverb_check"]["status"], "FAIL")

    def test_rt60_mismatch_fails_room_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        _write_pcm_wav(case["paths"]["spatial_dialogue"], amplitude=0.21, left_gain=0.17, right_gain=0.83, decay=2.0)
        self._sync_proofs_and_bundle(case)
        case["request"]["threshold_overrides"]["max_rt60_seconds"] = 0.25
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["room_reverb_check"]["status"], "FAIL")

    def test_tail_mismatch_fails_room_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        _write_pcm_wav(case["paths"]["spatial_dialogue"], seconds=0.05, amplitude=0.21, left_gain=0.17, right_gain=0.83, decay=20.0)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["room_reverb_check"]["status"], "FAIL")

    def test_tail_override_cannot_bypass_registry_ceiling(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        _write_pcm_wav(case["paths"]["spatial_dialogue"], seconds=0.05, amplitude=0.21, left_gain=0.17, right_gain=0.83, decay=20.0)
        self._sync_proofs_and_bundle(case)
        case["request"]["threshold_overrides"]["max_reverb_tail_error_seconds"] = 10.0
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["room_reverb_check"]["status"], "FAIL")

    def test_continuous_ambience_drift_fails_without_hard_cut(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        _write_pcm_wav(case["paths"]["ambience_current_segment"], amplitude=0.45, left_gain=1.0, right_gain=1.0)
        self._sync_proofs_and_bundle(case)
        case["request"]["ambience_continuity_evidence"]["hard_cut_contract"] = None
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["ambience_continuity"]["status"], "FAIL")

    def test_valid_hard_cut_permits_ambience_discontinuity(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        _write_pcm_wav(case["paths"]["ambience_current_segment"], amplitude=0.45, left_gain=1.0, right_gain=1.0)
        self._sync_proofs_and_bundle(case)
        case["request"]["ambience_continuity_evidence"]["hard_cut_contract"] = {
            "cut_id": "cut_001",
            "reason": "camera_cut",
            "approver_id": "qa_reviewer",
        }
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["ambience_continuity"]["status"], "PASS")

    def test_ambience_previous_current_same_path_invalid(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["paths"]["ambience_current_segment"] = case["paths"]["ambience_previous_segment"]
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertFalse(output.exists())

    def test_ambience_previous_current_same_hash_invalid(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["paths"]["ambience_current_segment"].write_bytes(case["paths"]["ambience_previous_segment"].read_bytes())
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertFalse(output.exists())

    def test_unapproved_hard_cut_contract_fails_ambience_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        _write_pcm_wav(case["paths"]["ambience_current_segment"], amplitude=0.45, left_gain=1.0, right_gain=1.0)
        self._sync_proofs_and_bundle(case)
        case["request"]["ambience_continuity_evidence"]["hard_cut_contract"] = {
            "cut_id": "cut_002",
            "reason": "camera_cut",
            "approver_id": "unknown_approver",
        }
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["ambience_continuity"]["status"], "FAIL")
        blockers = report["gates"]["ambience_continuity"]["blockers"]
        self.assertTrue(any("not allowlisted" in blocker for blocker in blockers))

    def test_synthetic_only_hard_cut_approver_rejected_for_non_synthetic(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="hand_authored_relabel")
        _write_pcm_wav(case["paths"]["ambience_current_segment"], amplitude=0.45, left_gain=1.0, right_gain=1.0)
        self._sync_proofs_and_bundle(case)
        case["request"]["ambience_continuity_evidence"]["hard_cut_contract"] = {
            "cut_id": "cut_003",
            "reason": "fixture_reset",
            "approver_id": "fixture_cut_approver",
        }
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["ambience_continuity"]["status"], "FAIL")
        blockers = report["gates"]["ambience_continuity"]["blockers"]
        self.assertTrue(any("synthetic-only" in blocker for blocker in blockers))

    def test_dialogue_masking_fails_mix_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        _write_pcm_wav(case["paths"]["spatial_dialogue"], amplitude=0.03, left_gain=0.17, right_gain=0.83, decay=20.0)
        _write_pcm_wav(case["paths"]["ambience_bed"], amplitude=0.3, left_gain=1.0, right_gain=1.0)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["mix_balance_review"]["status"], "FAIL")

    def test_final_mix_clipping_fails_mix_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        _write_pcm_wav(case["paths"]["final_mix"], amplitude=1.0, left_gain=1.0, right_gain=1.0)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["mix_balance_review"]["status"], "FAIL")

    def test_sample_channel_mismatch_fails_mix_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        _write_pcm_wav(case["paths"]["final_mix"], channels=1, amplitude=0.2)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["mix_balance_review"]["status"], "FAIL")

    def test_final_mix_reused_stem_path_fails_mix_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["paths"]["final_mix"] = case["paths"]["spatial_dialogue"]
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["mix_balance_review"]["status"], "FAIL")
        blockers = report["gates"]["mix_balance_review"]["blockers"]
        self.assertTrue(any("distinct from every stem path" in blocker for blocker in blockers))

    def test_unrelated_same_format_final_mix_fails_reconstruction_rule(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        _write_pcm_wav(case["paths"]["final_mix"], amplitude=0.6, left_gain=1.0, right_gain=0.0, frequency_hz=880.0, decay=0.0)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["mix_balance_review"]["status"], "FAIL")
        blockers = report["gates"]["mix_balance_review"]["blockers"]
        self.assertTrue(any("reconstruction residual" in blocker for blocker in blockers))

    def test_one_frame_final_mix_mismatch_cannot_skip_reconstruction(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        final_pcm = _read_pcm_wav(case["paths"]["final_mix"])
        unrelated = _read_pcm_wav(case["paths"]["ambience_bed"])
        shortened_samples = list(unrelated["samples"][: -int(unrelated["channels"])])
        _write_pcm_from_samples(case["paths"]["final_mix"], final_pcm, shortened_samples)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["mix_balance_review"]["status"], "FAIL")
        blockers = report["gates"]["mix_balance_review"]["blockers"]
        self.assertTrue(any("exact PCM frame and format parity" in blocker for blocker in blockers))

    def test_missing_playback_proof_blocks_playback_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["request"]["playback_proof_binding"] = None
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["spatial_audio_playback_review"]["status"], "BLOCKED")

    def test_invalid_playback_proof_fails_playback_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        playback = json.loads(case["paths"]["playback_proof"].read_text(encoding="utf-8"))
        playback["review_results"] = ["FAIL"]
        _write_json(case["paths"]["playback_proof"], playback)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["spatial_audio_playback_review"]["status"], "FAIL")

    def test_unapproved_playback_producer_blocks_playback_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        playback = json.loads(case["paths"]["playback_proof"].read_text(encoding="utf-8"))
        playback["model"] = "playback_model_unapproved"
        _write_json(case["paths"]["playback_proof"], playback)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["spatial_audio_playback_review"]["status"], "BLOCKED")

    def test_missing_runtime_proof_blocks_runtime_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["request"]["runtime_proof_binding"] = None
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_runtime_proof"]["status"], "BLOCKED")

    def test_invalid_runtime_proof_hash_binding_fails_runtime_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        self._sync_proofs_and_bundle(case)
        runtime = json.loads(case["paths"]["runtime_proof"].read_text(encoding="utf-8"))
        runtime["artifact_hashes"]["final_mix_sha256"] = "f" * 64
        _write_json(case["paths"]["runtime_proof"], runtime)
        self._refresh_binding(case["request"], "runtime_proof_binding", case["paths"]["runtime_proof"])
        bundle = json.loads(case["paths"]["production_bundle"].read_text(encoding="utf-8"))
        bundle["runtime_proof_sha256"] = _sha256(case["paths"]["runtime_proof"])
        _write_json(case["paths"]["production_bundle"], bundle)
        self._refresh_binding(case["request"], "production_authority_bundle_binding", case["paths"]["production_bundle"])
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_runtime_proof"]["status"], "FAIL")

    def test_unapproved_runtime_producer_hash_blocks_runtime_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        runtime = json.loads(case["paths"]["runtime_proof"].read_text(encoding="utf-8"))
        runtime["model_sha256"] = "f" * 64
        _write_json(case["paths"]["runtime_proof"], runtime)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_runtime_proof"]["status"], "BLOCKED")

    def test_hand_authored_relabel_cannot_use_synthetic_only_producers(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="hand_authored_relabel")
        playback = json.loads(case["paths"]["playback_proof"].read_text(encoding="utf-8"))
        playback["engine"] = "fixture_playback_engine"
        playback["model"] = "fixture_playback_model"
        playback["model_version"] = "2026.fixture"
        playback["model_sha256"] = hashlib.sha256(b"fixture-playback").hexdigest()
        _write_json(case["paths"]["playback_proof"], playback)
        runtime = json.loads(case["paths"]["runtime_proof"].read_text(encoding="utf-8"))
        runtime["engine"] = "fixture_runtime_engine"
        runtime["model"] = "fixture_runtime_model"
        runtime["model_version"] = "2026.fixture"
        runtime["model_sha256"] = hashlib.sha256(b"fixture-runtime").hexdigest()
        _write_json(case["paths"]["runtime_proof"], runtime)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["spatial_audio_playback_review"]["status"], "BLOCKED")
        self.assertEqual(report["gates"]["production_runtime_proof"]["status"], "BLOCKED")

    def test_missing_production_bundle_blocks_authority(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["request"]["production_authority_bundle_binding"] = None
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_spatial_room_authority"]["status"], "BLOCKED")

    def test_invalid_bundle_self_authorization_fails_authority_gate(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        bundle = json.loads(case["paths"]["production_bundle"].read_text(encoding="utf-8"))
        bundle["self_authorized"] = True
        _write_json(case["paths"]["production_bundle"], bundle)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_spatial_room_authority"]["status"], "FAIL")

    def test_production_allowlist_empty_blocks_authority(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertIn("production authority bundle is not allowlisted", report["blockers"])

    def test_registry_thresholds_cannot_be_loosened(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["request"]["threshold_overrides"]["max_pan_error"] = 0.9
        _write_pcm_wav(case["paths"]["spatial_dialogue"], amplitude=0.21, left_gain=0.35, right_gain=0.65, decay=20.0)
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["spatial_position_check"]["status"], "FAIL")

    def test_tampered_hash_invalid(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["request"]["wave31_spatial_mix_binding"]["sha256"] = "0" * 64
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_malformed_wav_invalid(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["paths"]["spatial_dialogue"].write_bytes(b"not-a-valid-wav")
        self._sync_proofs_and_bundle(case)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_unknown_request_key_invalid(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["request"]["unexpected"] = True
        request_path = self.tmpdir / "bad_request.json"
        output_path = self.tmpdir / "report.json"
        _write_json(request_path, case["request"])
        result = _run_eval(request_path, output_path)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_nonfinite_value_invalid(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        request_path = self.tmpdir / "nonfinite_request.json"
        output_path = self.tmpdir / "report.json"
        text = json.dumps(case["request"], indent=2, sort_keys=True)
        text = text.replace('"max_pan_error": 0.25', '"max_pan_error": NaN')
        request_path.write_text(text, encoding="utf-8")
        result = _run_eval(request_path, output_path)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_root_escape_and_root_override_and_output_collision_invalid(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        case["request"]["wave31_spatial_mix_binding"]["path"] = "/tmp/outside.json"
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

        case2 = self._build_case(synthetic=False, evidence_origin="technical_capture")
        request_path = self.tmpdir / "request2.json"
        output_path = self.tmpdir / "report2.json"
        self._write_request_and_validate_schema(request_path, case2["request"])
        bad_root = _run_eval(request_path, output_path, root=self.tmpdir)
        self.assertEqual(bad_root.returncode, 1)

        collision = _run_eval(request_path, request_path)
        self.assertEqual(collision.returncode, 1)

    def test_synthetic_parity_mismatch_invalid(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        runtime = json.loads(case["paths"]["runtime_proof"].read_text(encoding="utf-8"))
        runtime["is_synthetic"] = True
        _write_json(case["paths"]["runtime_proof"], runtime)
        self._sync_proofs_and_bundle(case)
        runtime2 = json.loads(case["paths"]["runtime_proof"].read_text(encoding="utf-8"))
        runtime2["is_synthetic"] = True
        _write_json(case["paths"]["runtime_proof"], runtime2)
        self._refresh_binding(case["request"], "runtime_proof_binding", case["paths"]["runtime_proof"])
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_runtime_proof"]["status"], "FAIL")

    def test_transactional_output_preservation(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        request_path = self.tmpdir / "request_atomic.json"
        output_path = self.tmpdir / "report_atomic.json"
        self._write_request_and_validate_schema(request_path, case["request"])
        original_payload = {"keep": True}
        _write_json(output_path, original_payload)
        bad_request = copy.deepcopy(case["request"])
        bad_request["wave31_room_acoustics_binding"]["sha256"] = "a" * 64
        _write_json(request_path, bad_request)
        result = _run_eval(request_path, output_path)
        self.assertEqual(result.returncode, 1)
        observed = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(observed, original_payload)

    def test_schema_validity_roundtrip(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        _ = self._assert_report_schema(output)

    def test_no_current_production_exit_zero_assertion(self) -> None:
        case = self._build_case(synthetic=False, evidence_origin="technical_capture")
        result, _ = self._run_case(case["request"])
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
