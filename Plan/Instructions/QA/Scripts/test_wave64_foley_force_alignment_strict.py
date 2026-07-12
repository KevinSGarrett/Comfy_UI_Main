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
SCRIPT_PATH = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_foley_force_alignment.py"
REQUEST_SCHEMA_PATH = REPO_ROOT / "Plan/08_SCHEMAS/wave64_foley_force_alignment_request.schema.json"
REPORT_SCHEMA_PATH = REPO_ROOT / "Plan/08_SCHEMAS/wave64_foley_force_alignment_report.schema.json"
REGISTRY_PATH = REPO_ROOT / "Plan/10_REGISTRIES/wave64_foley_force_alignment_authority_registry.json"
RUNTIME_ARTIFACTS_DIR = REPO_ROOT / "runtime_artifacts"
MINIMAL_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a"
    "0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c6360000002000154a24f5d"
    "0000000049454e44ae426082"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_png(path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(MINIMAL_PNG_BYTES)
    return {"path": str(path.resolve()), "sha256": _sha256(path), "bytes": path.stat().st_size, "media_type": "image/png"}


def _write_contact_evidence(path: Path) -> dict[str, Any]:
    payload = {
        "schema_name": "wave64_contact_evidence",
        "evidence_version": 1,
        "edges": [{"contact_edge_id": "edge_001", "confidence": 0.99}],
    }
    _write_json(path, payload)
    return {
        "path": str(path.resolve()),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "media_type": "application/json",
    }


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
    seconds: float = 0.1,
    sample_rate: int = 16000,
    sample_width: int = 2,
    amplitude_ratio: float = 0.2,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(seconds * sample_rate)
    max_sample = 127 if sample_width == 1 else (1 << (8 * sample_width - 1)) - 1
    amplitude = int(max_sample * amplitude_ratio)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(sample_width)
        handle.setframerate(sample_rate)
        payload = bytearray()
        for i in range(frame_count):
            value = int(amplitude * math.sin(2.0 * math.pi * 220.0 * (i / sample_rate)))
            payload.extend(_pack_sample(value, sample_width))
        handle.writeframes(bytes(payload))
    return {"path": str(path.resolve()), "sha256": _sha256(path), "bytes": path.stat().st_size, "seconds": frame_count / sample_rate}


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


class Wave64FoleyForceAlignmentStrictTests(unittest.TestCase):
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

    def _model_hash(self, seed: str) -> str:
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    def _refresh_binding(self, request: dict[str, Any], key: str, path: Path) -> None:
        request[key] = {"path": str(path.resolve()), "sha256": _sha256(path)}

    def _refresh_optional_binding(self, request: dict[str, Any], key: str, path: Path | None) -> None:
        if path is None:
            request[key] = None
        else:
            request[key] = {"path": str(path.resolve()), "sha256": _sha256(path)}

    def _sync_proof_and_bundle_hashes(
        self,
        case: dict[str, Any],
        *,
        force_changed: bool = False,
        wave30_changed: bool = False,
        visual_changed: bool = False,
    ) -> None:
        if visual_changed:
            self._refresh_binding(case["request"], "visual_contact_manifest_binding", case["paths"]["visual"])
        if force_changed:
            self._refresh_binding(case["request"], "wave22_force_event_manifest_binding", case["paths"]["force"])
        if wave30_changed:
            self._refresh_binding(case["request"], "wave30_audio_event_manifest_binding", case["paths"]["wave30"])
        runtime = json.loads(case["paths"]["runtime"].read_text(encoding="utf-8"))
        review = json.loads(case["paths"]["review"].read_text(encoding="utf-8"))
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        if visual_changed:
            runtime["visual_contact_manifest_sha256"] = _sha256(case["paths"]["visual"])
            review["visual_contact_manifest_sha256"] = _sha256(case["paths"]["visual"])
            bundle["visual_contact_manifest_sha256"] = _sha256(case["paths"]["visual"])
            visual_manifest = json.loads(case["paths"]["visual"].read_text(encoding="utf-8"))
            bundle["visual_take_artifact_sha256"] = visual_manifest["visual_take_artifact"]["sha256"]
            bundle["contact_evidence_artifact_sha256"] = visual_manifest["contact_evidence_artifact"]["sha256"]
        if force_changed:
            runtime["wave22_force_event_manifest_sha256"] = _sha256(case["paths"]["force"])
            review["wave22_force_event_manifest_sha256"] = _sha256(case["paths"]["force"])
            bundle["wave22_force_event_manifest_sha256"] = _sha256(case["paths"]["force"])
        if wave30_changed:
            runtime["wave30_audio_event_manifest_sha256"] = _sha256(case["paths"]["wave30"])
            review["wave30_audio_event_manifest_sha256"] = _sha256(case["paths"]["wave30"])
            bundle["wave30_audio_event_manifest_sha256"] = _sha256(case["paths"]["wave30"])
        _write_json(case["paths"]["runtime"], runtime)
        _write_json(case["paths"]["review"], review)
        self._refresh_binding(case["request"], "runtime_proof_binding", case["paths"]["runtime"])
        self._refresh_binding(case["request"], "av_review_proof_binding", case["paths"]["review"])
        bundle["runtime_proof_sha256"] = _sha256(case["paths"]["runtime"])
        bundle["av_review_proof_sha256"] = _sha256(case["paths"]["review"])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_binding(case["request"], "production_alignment_bundle_binding", case["paths"]["bundle"])

    def _build_case(self, *, synthetic: bool = False, amplitude_ratio: float = 0.08) -> dict[str, Any]:
        visual_take = _write_png(self.tmpdir / "visual_take.png")
        contact_ev = _write_contact_evidence(self.tmpdir / "contact_evidence.json")
        mapped_wav = _write_pcm_wav(self.tmpdir / "mapped.wav", seconds=0.1, amplitude_ratio=amplitude_ratio)
        dialogue_wav = _write_pcm_wav(self.tmpdir / "dialogue.wav", seconds=0.1, amplitude_ratio=0.1)
        synthetic_origin = "synthetic_fixture" if synthetic else "captured_live"

        visual_manifest = {
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
            "frame_rate": 24.0,
            "frame_time_origin_seconds": 0.0,
            "visual_take_artifact": {
                "path": visual_take["path"],
                "sha256": visual_take["sha256"],
                "bytes": visual_take["bytes"],
                "media_type": visual_take["media_type"],
            },
            "contact_evidence_artifact": {
                "path": contact_ev["path"],
                "sha256": contact_ev["sha256"],
                "bytes": contact_ev["bytes"],
                "media_type": contact_ev["media_type"],
            },
            "contact_authority": {
                "authority_scope": "body_contact",
                "gold_mask_dependency_status": "cleared",
                "evidence_authority_class": "gold_mask_validated",
                "production_trust_claim": False,
            },
            "contact_edges": [
                {
                    "contact_edge_id": "edge_001",
                    "source_entity_id": "char_a_hand_l",
                    "target_entity_id": "char_b_forearm_l",
                    "source_owner_id": "char_a",
                    "target_owner_id": "char_b",
                    "source_material": "fabric",
                    "target_material": "skin",
                    "visual_force_intensity": "light",
                    "start_frame": 10,
                    "end_frame": 12,
                    "audio_expected": True,
                    "min_expected_force_events": 1,
                    "max_expected_force_events": 1,
                },
                {
                    "contact_edge_id": "edge_002",
                    "source_entity_id": "char_a_finger_l",
                    "target_entity_id": "table_corner",
                    "source_owner_id": "char_a",
                    "target_owner_id": "table_1",
                    "source_material": "skin",
                    "target_material": "wood",
                    "visual_force_intensity": "none",
                    "start_frame": 30,
                    "end_frame": 31,
                    "audio_expected": False,
                    "min_expected_force_events": 0,
                    "max_expected_force_events": 0,
                },
            ],
        }
        visual_path = self.tmpdir / "visual_contact_manifest.json"
        _write_json(visual_path, visual_manifest)

        force_manifest = {
            "schema_name": "wave22_audio_force_event_manifest",
            "manifest_version": 1,
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
            "frame_rate": 24.0,
            "force_events": [
                {
                    "event_id": "force_001",
                    "contact_edge_id": "edge_001",
                    "source_material": "fabric",
                    "target_material": "skin",
                    "expected_foley_family": "clothing_foley",
                    "audio_force_class": "soft_fabric_rustle",
                    "loudness_hint": "low",
                    "confidence": 0.95,
                    "start_frame": 10,
                    "end_frame": 12,
                }
            ],
        }
        force_path = self.tmpdir / "wave22_force_manifest.json"
        _write_json(force_path, force_manifest)

        wave30_manifest = {
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
            "taxonomy_registry_sha256": self._model_hash("taxonomy"),
            "audio_event_count": 2,
            "required_lanes": ["foley"],
            "audio_events": [
                {
                    "audio_event_id": "audio_001",
                    "scene_id": "scene_001",
                    "shot_id": "shot_001",
                    "event_type": "clothing_foley",
                    "sync_class": "frame_exact",
                    "purpose": "contact cloth rustle",
                    "source_event_id": "force_001",
                    "start_seconds": 10.0 / 24.0,
                    "end_seconds": 12.4 / 24.0,
                    "expected_video_frame_range": {"start_frame": 10, "end_frame": 12, "frame_rate": 24.0},
                    "qa_rules": ["rule_sync"],
                    "layer": "clothing_foley",
                    "routing": {"lane": "foley"},
                    "subject_binding": {"binding_type": "character", "character_id": "char_a", "object_id": None},
                    "artifact": {
                        "path": mapped_wav["path"],
                        "sha256": mapped_wav["sha256"],
                        "bytes": mapped_wav["bytes"],
                        "duration_seconds": mapped_wav["seconds"],
                        "sample_rate_hz": 16000,
                        "channels": 1,
                        "sample_width_bytes": 2,
                        "frame_count": int(mapped_wav["seconds"] * 16000),
                    },
                    "synthetic_state": {"synthetic_origin": synthetic_origin, "production_proof_claimed": False},
                },
                {
                    "audio_event_id": "audio_dialogue_001",
                    "scene_id": "scene_001",
                    "shot_id": "shot_001",
                    "event_type": "dialogue",
                    "sync_class": "windowed",
                    "purpose": "dialogue out of row scope",
                    "source_event_id": "dialogue_source_1",
                    "start_seconds": 1.0,
                    "end_seconds": 1.1,
                    "expected_video_frame_range": {"start_frame": 24, "end_frame": 26, "frame_rate": 24.0},
                    "qa_rules": ["rule_dialogue"],
                    "layer": "dialogue_lane",
                    "routing": {"lane": "dialogue"},
                    "subject_binding": {"binding_type": "character", "character_id": "char_a", "object_id": None},
                    "artifact": {
                        "path": dialogue_wav["path"],
                        "sha256": dialogue_wav["sha256"],
                        "bytes": dialogue_wav["bytes"],
                        "duration_seconds": dialogue_wav["seconds"],
                        "sample_rate_hz": 16000,
                        "channels": 1,
                        "sample_width_bytes": 2,
                        "frame_count": int(dialogue_wav["seconds"] * 16000),
                    },
                    "synthetic_state": {"synthetic_origin": synthetic_origin, "production_proof_claimed": False},
                },
            ],
            "artifact_manifest": {"source_input_path": str(self.tmpdir / "input.json"), "source_input_sha256": self._model_hash("in")},
            "av_sync_binding": {"frame_rate": 24.0, "sync_scope": "event_level"},
        }
        wave30_path = self.tmpdir / "wave30_manifest.json"
        _write_json(wave30_path, wave30_manifest)

        runtime = {
            "schema_name": "wave64_production_runtime_proof",
            "proof_kind": "production_runtime",
            "engine": "runtime_engine",
            "model": "runtime_model",
            "model_version": "2026.07",
            "model_sha256": self._model_hash("runtime"),
            "visual_contact_manifest_sha256": _sha256(visual_path),
            "wave22_force_event_manifest_sha256": _sha256(force_path),
            "wave30_audio_event_manifest_sha256": _sha256(wave30_path),
            "wave31_force_event_manifest_sha256": None,
            "ordered_event_audio_bindings": [
                {"force_event_id": "force_001", "audio_event_id": "audio_001", "wav_sha256": mapped_wav["sha256"]}
            ],
            "runtime_executed": True,
            "decode_succeeded": True,
        }
        runtime_path = self.tmpdir / "runtime_proof.json"
        _write_json(runtime_path, runtime)

        review = {
            "schema_name": "wave64_av_alignment_review_proof",
            "proof_kind": "av_alignment_review",
            "reviewer_id": "reviewer_001",
            "review_method": "frame_by_frame",
            "engine": "review_engine",
            "model": "review_model",
            "model_version": "2026.07",
            "model_sha256": self._model_hash("review"),
            "visual_contact_manifest_sha256": _sha256(visual_path),
            "wave22_force_event_manifest_sha256": _sha256(force_path),
            "wave30_audio_event_manifest_sha256": _sha256(wave30_path),
            "wave31_force_event_manifest_sha256": None,
            "results": [
                {
                    "force_event_id": "force_001",
                    "audio_event_id": "audio_001",
                    "visual_contact_present": True,
                    "ownership_match": True,
                    "material_family_match": True,
                    "force_loudness_match": True,
                    "timing_aligned": True,
                    "foley_present": True,
                    "false_event_absent": True,
                }
            ],
        }
        review_path = self.tmpdir / "av_review_proof.json"
        _write_json(review_path, review)

        bundle = {
            "schema_name": "wave64_production_alignment_bundle",
            "proof_kind": "production_alignment_authority",
            "bundle_version": 1,
            "bundle_id": "bundle_001",
            "authority_id": "authority_wave64",
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": False,
            "visual_contact_manifest_sha256": _sha256(visual_path),
            "wave22_force_event_manifest_sha256": _sha256(force_path),
            "wave30_audio_event_manifest_sha256": _sha256(wave30_path),
            "wave31_force_event_manifest_sha256": None,
            "runtime_proof_sha256": _sha256(runtime_path),
            "av_review_proof_sha256": _sha256(review_path),
            "owned_event_audio_bindings": [
                {"force_event_id": "force_001", "audio_event_id": "audio_001", "wav_sha256": mapped_wav["sha256"]}
            ],
            "visual_take_artifact_sha256": visual_take["sha256"],
            "contact_evidence_artifact_sha256": contact_ev["sha256"],
        }
        bundle_path = self.tmpdir / "bundle.json"
        _write_json(bundle_path, bundle)

        request = {
            "schema_name": "wave64_foley_force_alignment_request",
            "request_version": 1,
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": synthetic,
            "visual_contact_manifest_binding": {"path": str(visual_path.resolve()), "sha256": _sha256(visual_path)},
            "wave22_force_event_manifest_binding": {"path": str(force_path.resolve()), "sha256": _sha256(force_path)},
            "wave30_audio_event_manifest_binding": {"path": str(wave30_path.resolve()), "sha256": _sha256(wave30_path)},
            "wave31_force_event_manifest_binding": None,
            "runtime_proof_binding": {"path": str(runtime_path.resolve()), "sha256": _sha256(runtime_path)},
            "av_review_proof_binding": {"path": str(review_path.resolve()), "sha256": _sha256(review_path)},
            "production_alignment_bundle_binding": {"path": str(bundle_path.resolve()), "sha256": _sha256(bundle_path)},
            "thresholds": {
                "min_force_confidence": 0.7,
                "max_frame_drift": 2,
                "max_seconds_drift": 0.08,
                "max_wav_duration_drift_seconds": 0.05,
                "max_clipping_ratio": 0.0003,
                "min_rms_ratio": 0.005,
            },
        }
        return {
            "request": request,
            "paths": {
                "visual": visual_path,
                "force": force_path,
                "wave30": wave30_path,
                "runtime": runtime_path,
                "review": review_path,
                "bundle": bundle_path,
                "mapped_wav": Path(mapped_wav["path"]),
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

    def test_synthetic_blocked_baseline(self) -> None:
        case = self._build_case(synthetic=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_runtime_proof"]["status"], "BLOCKED")
        self.assertFalse(report["overall_pass"])

    def test_coherent_non_synthetic_blocked_by_empty_allowlist(self) -> None:
        case = self._build_case(synthetic=False)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        report = self._assert_report_schema(output)
        self.assertIn("production alignment bundle not allowlisted in authority registry", report["blockers"])

    def test_wave22_is_synthetic_mismatch_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        force = json.loads(case["paths"]["force"].read_text(encoding="utf-8"))
        force["is_synthetic"] = True
        _write_json(case["paths"]["force"], force)
        self._sync_proof_and_bundle_hashes(case, force_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_wave30_is_synthetic_mismatch_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["is_synthetic"] = True
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_wave30_event_synthetic_state_mismatch_fails(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_events"][0]["synthetic_state"]["synthetic_origin"] = "synthetic_fixture"
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")

    def test_wave30_audio_event_count_mismatch_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_event_count"] = 99
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_required_lanes_must_cover_matched_event_lanes(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_events"][0]["routing"]["lane"] = "foley_specialized"
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")
        self.assertTrue(any("required_lanes missing matched lanes" in item for item in report["blockers"]))

    def test_mapped_event_type_mismatch_fails(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_events"][0]["event_type"] = "body_foley"
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")
        self.assertEqual(report["gates"]["production_alignment_authority"]["status"], "FAIL")

    def test_mapped_layer_mismatch_fails(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_events"][0]["layer"] = "body_foley"
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")

    def test_subject_binding_owner_mismatch_fails_event_binding(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_events"][0]["subject_binding"]["character_id"] = "unknown_character"
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")

    def test_unknown_material_pair_fails_closed(self) -> None:
        case = self._build_case(synthetic=False)
        force = json.loads(case["paths"]["force"].read_text(encoding="utf-8"))
        force["force_events"][0]["source_material"] = "glass"
        force["force_events"][0]["target_material"] = "rubber"
        _write_json(case["paths"]["force"], force)
        visual = json.loads(case["paths"]["visual"].read_text(encoding="utf-8"))
        visual["contact_edges"][0]["source_material"] = "glass"
        visual["contact_edges"][0]["target_material"] = "rubber"
        _write_json(case["paths"]["visual"], visual)
        self._sync_proof_and_bundle_hashes(case, force_changed=True, visual_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")
        self.assertTrue(any("unknown material pair" in item for item in report["blockers"]))

    def test_av_sync_frame_rate_mismatch_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["av_sync_binding"]["frame_rate"] = 30.0
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_event_frame_rate_mismatch_fails_alignment_gate(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_events"][0]["expected_video_frame_range"]["frame_rate"] = 30.0
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["frame_to_audio_alignment"]["status"], "FAIL")

    def test_missing_gold_mask_authority_blocks_av_and_production_authority(self) -> None:
        case = self._build_case(synthetic=False)
        visual = json.loads(case["paths"]["visual"].read_text(encoding="utf-8"))
        visual["contact_authority"]["gold_mask_dependency_status"] = "missing"
        visual["contact_authority"]["evidence_authority_class"] = "manual_review"
        _write_json(case["paths"]["visual"], visual)
        self._sync_proof_and_bundle_hashes(case, visual_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["av_event_alignment_review"]["status"], "BLOCKED")
        self.assertEqual(report["gates"]["production_alignment_authority"]["status"], "BLOCKED")
        self.assertIn("Blocked_Gold_Mask_Authority_Missing", report["blockers"])

    def test_body_contact_cannot_bypass_gold_mask_dependency_as_not_applicable(self) -> None:
        case = self._build_case(synthetic=False)
        visual = json.loads(case["paths"]["visual"].read_text(encoding="utf-8"))
        visual["contact_authority"]["gold_mask_dependency_status"] = "not_applicable"
        visual["contact_authority"]["evidence_authority_class"] = "manual_review"
        _write_json(case["paths"]["visual"], visual)
        self._sync_proof_and_bundle_hashes(case, visual_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_body_material_edge_cannot_declare_non_body_contact(self) -> None:
        case = self._build_case(synthetic=False)
        visual = json.loads(case["paths"]["visual"].read_text(encoding="utf-8"))
        visual["contact_authority"] = {
            "authority_scope": "non_body_contact",
            "gold_mask_dependency_status": "not_applicable",
            "evidence_authority_class": "manual_review",
            "production_trust_claim": False,
        }
        _write_json(case["paths"]["visual"], visual)
        self._sync_proof_and_bundle_hashes(case, visual_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_self_reported_trust_cannot_replace_bundle(self) -> None:
        case = self._build_case(synthetic=False)
        visual = json.loads(case["paths"]["visual"].read_text(encoding="utf-8"))
        visual["contact_authority"]["production_trust_claim"] = True
        _write_json(case["paths"]["visual"], visual)
        self._sync_proof_and_bundle_hashes(case, visual_changed=True)
        case["request"]["production_alignment_bundle_binding"] = None
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertIn("self-reported production trust cannot replace allowlisted production bundle", report["blockers"])

    def test_visual_take_signature_mismatch_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        visual = json.loads(case["paths"]["visual"].read_text(encoding="utf-8"))
        visual_take_path = Path(visual["visual_take_artifact"]["path"])
        visual_take_path.write_bytes(b"not-a-real-png")
        visual["visual_take_artifact"]["sha256"] = _sha256(visual_take_path)
        visual["visual_take_artifact"]["bytes"] = visual_take_path.stat().st_size
        _write_json(case["paths"]["visual"], visual)
        self._sync_proof_and_bundle_hashes(case, visual_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_contact_evidence_must_be_parseable_json(self) -> None:
        case = self._build_case(synthetic=False)
        visual = json.loads(case["paths"]["visual"].read_text(encoding="utf-8"))
        evidence_path = Path(visual["contact_evidence_artifact"]["path"])
        evidence_path.write_text("{not_json", encoding="utf-8")
        visual["contact_evidence_artifact"]["sha256"] = _sha256(evidence_path)
        visual["contact_evidence_artifact"]["bytes"] = evidence_path.stat().st_size
        _write_json(case["paths"]["visual"], visual)
        self._sync_proof_and_bundle_hashes(case, visual_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_missing_runtime_blocked(self) -> None:
        case = self._build_case(synthetic=False)
        case["request"]["runtime_proof_binding"] = None
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_runtime_proof"]["status"], "BLOCKED")

    def test_missing_review_blocked(self) -> None:
        case = self._build_case(synthetic=False)
        case["request"]["av_review_proof_binding"] = None
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["av_event_alignment_review"]["status"], "BLOCKED")

    def test_missing_bundle_blocked(self) -> None:
        case = self._build_case(synthetic=False)
        case["request"]["production_alignment_bundle_binding"] = None
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_alignment_authority"]["status"], "BLOCKED")

    def test_wrong_material_pair_family_fails_event_binding(self) -> None:
        case = self._build_case(synthetic=False)
        force = json.loads(case["paths"]["force"].read_text(encoding="utf-8"))
        force["force_events"][0]["expected_foley_family"] = "prop_foley"
        _write_json(case["paths"]["force"], force)
        self._refresh_binding(case["request"], "wave22_force_event_manifest_binding", case["paths"]["force"])
        runtime = json.loads(case["paths"]["runtime"].read_text(encoding="utf-8"))
        runtime["wave22_force_event_manifest_sha256"] = _sha256(case["paths"]["force"])
        _write_json(case["paths"]["runtime"], runtime)
        self._refresh_binding(case["request"], "runtime_proof_binding", case["paths"]["runtime"])
        review = json.loads(case["paths"]["review"].read_text(encoding="utf-8"))
        review["wave22_force_event_manifest_sha256"] = _sha256(case["paths"]["force"])
        _write_json(case["paths"]["review"], review)
        self._refresh_binding(case["request"], "av_review_proof_binding", case["paths"]["review"])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["wave22_force_event_manifest_sha256"] = _sha256(case["paths"]["force"])
        bundle["runtime_proof_sha256"] = _sha256(case["paths"]["runtime"])
        bundle["av_review_proof_sha256"] = _sha256(case["paths"]["review"])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_binding(case["request"], "production_alignment_bundle_binding", case["paths"]["bundle"])
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")

    def test_force_intensity_mismatch_fails_event_binding(self) -> None:
        case = self._build_case(synthetic=False)
        force = json.loads(case["paths"]["force"].read_text(encoding="utf-8"))
        force["force_events"][0]["audio_force_class"] = "impact_thud"
        _write_json(case["paths"]["force"], force)
        self._sync_proof_and_bundle_hashes(case, force_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")

    def test_loudness_hint_mismatch_fails(self) -> None:
        case = self._build_case(synthetic=False)
        force = json.loads(case["paths"]["force"].read_text(encoding="utf-8"))
        force["force_events"][0]["loudness_hint"] = "very_high"
        _write_json(case["paths"]["force"], force)
        self._sync_proof_and_bundle_hashes(case, force_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")

    def test_rms_mismatch_fails(self) -> None:
        case = self._build_case(synthetic=False, amplitude_ratio=0.0001)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")

    def test_clipping_fails(self) -> None:
        case = self._build_case(synthetic=False, amplitude_ratio=1.0)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")

    def test_low_confidence_fails(self) -> None:
        case = self._build_case(synthetic=False)
        force = json.loads(case["paths"]["force"].read_text(encoding="utf-8"))
        force["force_events"][0]["confidence"] = 0.1
        _write_json(case["paths"]["force"], force)
        self._sync_proof_and_bundle_hashes(case, force_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")

    def test_frame_drift_fails(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_events"][0]["expected_video_frame_range"]["start_frame"] = 40
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["frame_to_audio_alignment"]["status"], "FAIL")

    def test_request_cannot_loosen_registry_frame_drift_ceiling(self) -> None:
        case = self._build_case(synthetic=False)
        case["request"]["thresholds"]["max_frame_drift"] = 120
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_events"][0]["expected_video_frame_range"]["start_frame"] = 13
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["frame_to_audio_alignment"]["status"], "FAIL")

    def test_seconds_and_origin_drift_fails(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_events"][0]["start_seconds"] += 1.0
        wave30["audio_events"][0]["end_seconds"] += 1.0
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["frame_to_audio_alignment"]["status"], "FAIL")

    def test_wav_duration_drift_fails(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_events"][0]["end_seconds"] = wave30["audio_events"][0]["start_seconds"] + 2.0
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["frame_to_audio_alignment"]["status"], "FAIL")

    def test_missing_required_event_fails_foley_presence(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_events"] = [wave30["audio_events"][1]]
        wave30["audio_event_count"] = 1
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["foley_presence"]["status"], "FAIL")

    def test_silent_zero_event_allowed(self) -> None:
        case = self._build_case(synthetic=False)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "PASS")

    def test_too_many_events_for_edge_fails(self) -> None:
        case = self._build_case(synthetic=False)
        force = json.loads(case["paths"]["force"].read_text(encoding="utf-8"))
        extra = copy.deepcopy(force["force_events"][0])
        extra["event_id"] = "force_002"
        force["force_events"].append(extra)
        _write_json(case["paths"]["force"], force)
        self._sync_proof_and_bundle_hashes(case, force_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["event_binding_check"]["status"], "FAIL")

    def test_extra_unmatched_foley_rejected(self) -> None:
        case = self._build_case(synthetic=False)
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        extra = copy.deepcopy(wave30["audio_events"][0])
        extra["audio_event_id"] = "audio_extra"
        extra["source_event_id"] = "unknown_force"
        wave30["audio_events"].append(extra)
        wave30["audio_event_count"] = 3
        _write_json(case["paths"]["wave30"], wave30)
        self._sync_proof_and_bundle_hashes(case, wave30_changed=True)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["false_event_reject"]["status"], "FAIL")

    def test_ownership_mismatch_in_review_fails(self) -> None:
        case = self._build_case(synthetic=False)
        review = json.loads(case["paths"]["review"].read_text(encoding="utf-8"))
        review["results"][0]["ownership_match"] = False
        _write_json(case["paths"]["review"], review)
        self._refresh_binding(case["request"], "av_review_proof_binding", case["paths"]["review"])
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["av_event_alignment_review"]["status"], "FAIL")
        self.assertEqual(report["gates"]["production_alignment_authority"]["status"], "FAIL")

    def test_duplicate_force_ids_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        force = json.loads(case["paths"]["force"].read_text(encoding="utf-8"))
        force["force_events"][0]["event_id"] = "force_dup"
        dup = copy.deepcopy(force["force_events"][0])
        force["force_events"].append(dup)
        _write_json(case["paths"]["force"], force)
        self._refresh_binding(case["request"], "wave22_force_event_manifest_binding", case["paths"]["force"])
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_unknown_contact_id_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        force = json.loads(case["paths"]["force"].read_text(encoding="utf-8"))
        force["force_events"][0]["contact_edge_id"] = "edge_unknown"
        _write_json(case["paths"]["force"], force)
        self._refresh_binding(case["request"], "wave22_force_event_manifest_binding", case["paths"]["force"])
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_unrelated_dialogue_is_ignored(self) -> None:
        case = self._build_case(synthetic=False)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["metrics"]["evaluated_wave30_event_count"], 1)

    def test_tampered_hash_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        case["request"]["wave22_force_event_manifest_binding"]["sha256"] = "0" * 64
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_malformed_wav_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        case["paths"]["mapped_wav"].write_bytes(b"not-a-wav")
        wave30 = json.loads(case["paths"]["wave30"].read_text(encoding="utf-8"))
        wave30["audio_events"][0]["artifact"]["bytes"] = case["paths"]["mapped_wav"].stat().st_size
        wave30["audio_events"][0]["artifact"]["sha256"] = _sha256(case["paths"]["mapped_wav"])
        _write_json(case["paths"]["wave30"], wave30)
        self._refresh_binding(case["request"], "wave30_audio_event_manifest_binding", case["paths"]["wave30"])
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_unknown_key_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        case["request"]["unexpected"] = True
        request_path = self.tmpdir / "request_bad.json"
        output_path = self.tmpdir / "report.json"
        _write_json(request_path, case["request"])
        result = _run_eval(request_path, output_path)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_nonfinite_and_range_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        request_path = self.tmpdir / "request_nonfinite.json"
        output_path = self.tmpdir / "report.json"
        text = json.dumps(case["request"], indent=2, sort_keys=True)
        text = text.replace('"min_force_confidence": 0.7', '"min_force_confidence": NaN')
        request_path.write_text(text, encoding="utf-8")
        result = _run_eval(request_path, output_path)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_root_escape_root_override_output_collision(self) -> None:
        case = self._build_case(synthetic=False)
        case["request"]["visual_contact_manifest_binding"]["path"] = "/tmp/outside.json"
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

        case2 = self._build_case(synthetic=False)
        request_path = self.tmpdir / "request2.json"
        output_path = self.tmpdir / "report2.json"
        self._write_request_and_validate_schema(request_path, case2["request"])
        bad_root_result = _run_eval(request_path, output_path, root=self.tmpdir)
        self.assertEqual(bad_root_result.returncode, 1)

        collision = _run_eval(request_path, request_path)
        self.assertEqual(collision.returncode, 1)

    def test_bundle_proof_hash_mismatch_fails(self) -> None:
        case = self._build_case(synthetic=False)
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["runtime_proof_sha256"] = "f" * 64
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_binding(case["request"], "production_alignment_bundle_binding", case["paths"]["bundle"])
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        report = self._assert_report_schema(output)
        self.assertEqual(report["gates"]["production_alignment_authority"]["status"], "FAIL")

    def test_atomic_output_preservation(self) -> None:
        case = self._build_case(synthetic=False)
        request_path = self.tmpdir / "request_atomic.json"
        output_path = self.tmpdir / "report_atomic.json"
        self._write_request_and_validate_schema(request_path, case["request"])
        original = {"keep": True}
        _write_json(output_path, original)
        bad = copy.deepcopy(case["request"])
        bad["wave22_force_event_manifest_binding"]["sha256"] = "a" * 64
        _write_json(request_path, bad)
        result = _run_eval(request_path, output_path)
        self.assertEqual(result.returncode, 1)
        observed = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(observed, original)

    def test_request_and_report_schema_validation(self) -> None:
        case = self._build_case(synthetic=False)
        result, output = self._run_case(case["request"])
        self.assertEqual(result.returncode, 2)
        _ = self._assert_report_schema(output)


if __name__ == "__main__":
    unittest.main()
