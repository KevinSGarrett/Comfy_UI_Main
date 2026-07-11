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
SCRIPT_PATH = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave30_voice_dialogue_continuity.py"
REQUEST_SCHEMA_PATH = REPO_ROOT / "Plan/08_SCHEMAS/wave30_voice_dialogue_continuity_request.schema.json"
EVIDENCE_SCHEMA_PATH = REPO_ROOT / "Plan/08_SCHEMAS/wave30_voice_dialogue_continuity_evidence.schema.json"
REGISTRY_PATH = REPO_ROOT / "Plan/10_REGISTRIES/wave30_voice_proof_authority_registry.json"
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
    seconds: float = 0.25,
    sample_rate: int = 16000,
    sample_width: int = 2,
    amplitude_ratio: float = 0.5,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(sample_rate * seconds)
    channels = 1
    if sample_width == 1:
        max_sample = 127
    else:
        max_sample = (1 << (8 * sample_width - 1)) - 1
    amplitude = int(max_sample * amplitude_ratio)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(sample_width)
        handle.setframerate(sample_rate)
        frames = bytearray()
        for i in range(frame_count):
            value = int(amplitude * math.sin(2.0 * math.pi * 220.0 * (i / sample_rate)))
            frames.extend(_pack_sample(value, sample_width))
        handle.writeframes(bytes(frames))
    return {
        "path": str(path.resolve()),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "seconds": frame_count / float(sample_rate),
    }


def _run_eval(request_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--root",
            str(REPO_ROOT),
            "--input",
            str(request_path),
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class Wave30VoiceDialogueContinuityStrictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.request_schema = json.loads(REQUEST_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.evidence_schema = json.loads(EVIDENCE_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.request_validator = Draft202012Validator(cls.request_schema)
        cls.evidence_validator = Draft202012Validator(cls.evidence_schema)

    def setUp(self) -> None:
        RUNTIME_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        self.tempdir = tempfile.TemporaryDirectory(dir=RUNTIME_ARTIFACTS_DIR)
        self.tmpdir = Path(self.tempdir.name)
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(registry.get("approved_proof_bundles"), [])

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _model_hash(self, seed: str) -> str:
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    def _proof_line_audio_bindings(self, line1: dict[str, Any], line2: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"line_id": "line_001", "audio_sha256": line1["sha256"]},
            {"line_id": "line_002", "audio_sha256": line2["sha256"]},
        ]

    def _refresh_proof_binding(self, request: dict[str, Any], key: str, proof_path: Path) -> None:
        request["proof_bindings"][key] = {"path": str(proof_path.resolve()), "sha256": _sha256(proof_path)}

    def _build_case(
        self,
        *,
        synthetic: bool,
        sample_width: int = 2,
        amplitude_ratio: float = 0.5,
    ) -> dict[str, Any]:
        voice_profile = {
            "voice_profile_id": "voice_char_a_default",
            "character_id": "char_a",
            "character_version": "v1",
            "status": "active",
            "voice_traits": {"accent": "neutral"},
        }
        voice_path = self.tmpdir / "voice_profile.json"
        _write_json(voice_path, voice_profile)

        line1 = _write_pcm_wav(
            self.tmpdir / "line_001.wav",
            seconds=0.20,
            sample_width=sample_width,
            amplitude_ratio=amplitude_ratio,
        )
        line2 = _write_pcm_wav(
            self.tmpdir / "line_002.wav",
            seconds=0.30,
            sample_width=sample_width,
            amplitude_ratio=amplitude_ratio,
        )
        lines = [
            {
                "line_id": "line_001",
                "character_id": "char_a",
                "voice_profile_id": "voice_char_a_default",
                "text": "We need to move carefully.",
                "start_time": 0.00,
                "end_time": line1["seconds"],
                "emotion": "focused",
                "intensity": "low",
                "sync_required": True,
                "output_file": line1["path"],
            },
            {
                "line_id": "line_002",
                "character_id": "char_a",
                "voice_profile_id": "voice_char_a_default",
                "text": "Stay close and keep quiet.",
                "start_time": 0.20,
                "end_time": 0.20 + line2["seconds"],
                "emotion": "calm",
                "intensity": "low",
                "sync_required": True,
                "output_file": line2["path"],
            },
        ]
        contract_path = self.tmpdir / "dialogue_contract.json"
        _write_json(
            contract_path,
            {
                "schema_name": "wave30_voice_dialogue_contract",
                "dialogue_contract_version": 1,
                "lines": lines,
            },
        )
        contract_sha = _sha256(contract_path)
        voice_sha = _sha256(voice_path)

        asr_path = self.tmpdir / "asr_proof.json"
        _write_json(
            asr_path,
            {
                "schema_name": "wave30_asr_proof",
                "proof_kind": "asr",
                "engine": "asr_engine",
                "model": "asr_model",
                "model_version": "2026.07",
                "model_sha256": self._model_hash("asr"),
                "dialogue_contract_sha256": contract_sha,
                "voice_profile_sha256": voice_sha,
                "line_results": [
                    {
                        "line_id": "line_001",
                        "audio_sha256": line1["sha256"],
                        "transcript": "We need to move carefully.",
                        "start_time": lines[0]["start_time"],
                        "end_time": lines[0]["end_time"],
                    },
                    {
                        "line_id": "line_002",
                        "audio_sha256": line2["sha256"],
                        "transcript": "Stay close and keep quiet.",
                        "start_time": lines[1]["start_time"],
                        "end_time": lines[1]["end_time"],
                    },
                ],
            },
        )

        speaker_path = self.tmpdir / "speaker_proof.json"
        _write_json(
            speaker_path,
            {
                "schema_name": "wave30_speaker_proof",
                "proof_kind": "speaker",
                "engine": "speaker_engine",
                "model": "speaker_model",
                "model_version": "2026.07",
                "model_sha256": self._model_hash("speaker"),
                "dialogue_contract_sha256": contract_sha,
                "voice_profile_sha256": voice_sha,
                "line_results": [
                    {
                        "line_id": "line_001",
                        "character_id": "char_a",
                        "voice_profile_id": "voice_char_a_default",
                        "audio_sha256": line1["sha256"],
                        "speaker_similarity": 0.94,
                        "continuity_with_previous": None,
                    },
                    {
                        "line_id": "line_002",
                        "character_id": "char_a",
                        "voice_profile_id": "voice_char_a_default",
                        "audio_sha256": line2["sha256"],
                        "speaker_similarity": 0.92,
                        "continuity_with_previous": 0.90,
                    },
                ],
            },
        )

        emotion_path = self.tmpdir / "emotion_proof.json"
        _write_json(
            emotion_path,
            {
                "schema_name": "wave30_emotion_proof",
                "proof_kind": "emotion",
                "engine": "emotion_engine",
                "model": "emotion_model",
                "model_version": "2026.07",
                "model_sha256": self._model_hash("emotion"),
                "dialogue_contract_sha256": contract_sha,
                "voice_profile_sha256": voice_sha,
                "line_results": [
                    {
                        "line_id": "line_001",
                        "audio_sha256": line1["sha256"],
                        "predicted_emotion": "focused",
                        "emotion_confidence": 0.95,
                        "predicted_intensity": "low",
                        "intensity_score": 0.93,
                    },
                    {
                        "line_id": "line_002",
                        "audio_sha256": line2["sha256"],
                        "predicted_emotion": "calm",
                        "emotion_confidence": 0.92,
                        "predicted_intensity": "low",
                        "intensity_score": 0.90,
                    },
                ],
            },
        )

        playback_path = self.tmpdir / "playback_proof.json"
        _write_json(
            playback_path,
            {
                "schema_name": "wave30_playback_review_proof",
                "proof_kind": "playback_review",
                "review_method": "audio_playback_review",
                "reviewer_id": "qa_reviewer_01",
                "engine": "review_engine",
                "model": "review_model",
                "model_version": "2026.07",
                "model_sha256": self._model_hash("playback"),
                "dialogue_contract_sha256": contract_sha,
                "voice_profile_sha256": voice_sha,
                "line_audio_bindings": self._proof_line_audio_bindings(line1, line2),
                "voice_identity": True,
                "intelligibility": True,
                "timing": True,
                "emotional_tone": True,
                "continuity": True,
                "noise_free": True,
                "clipping_free": True,
            },
        )

        runtime_path = self.tmpdir / "runtime_proof.json"
        _write_json(
            runtime_path,
            {
                "schema_name": "wave30_production_runtime_proof",
                "proof_kind": "production_runtime",
                "engine": "runtime_engine",
                "model": "runtime_model",
                "model_version": "2026.07",
                "model_sha256": self._model_hash("runtime"),
                "dialogue_contract_sha256": contract_sha,
                "voice_profile_sha256": voice_sha,
                "line_audio_bindings": self._proof_line_audio_bindings(line1, line2),
                "runtime_executed": True,
                "decode_succeeded": True,
            },
        )

        bundle_path = self.tmpdir / "production_bundle.json"
        _write_json(
            bundle_path,
            {
                "schema_name": "wave30_production_proof_bundle",
                "proof_kind": "production_proof_bundle",
                "bundle_version": 1,
                "bundle_id": "bundle-wave64-row027",
                "authority_id": "authority-wave64",
                "run_id": "run_wave64_row027",
                "is_synthetic": False,
                "dialogue_contract_sha256": contract_sha,
                "voice_profile_sha256": voice_sha,
                "line_audio_bindings": self._proof_line_audio_bindings(line1, line2),
                "asr_proof_sha256": _sha256(asr_path),
                "speaker_proof_sha256": _sha256(speaker_path),
                "emotion_proof_sha256": _sha256(emotion_path),
                "playback_review_proof_sha256": _sha256(playback_path),
                "production_runtime_proof_sha256": _sha256(runtime_path),
            },
        )

        request = {
            "schema_name": "wave30_voice_dialogue_continuity_request",
            "request_version": 1,
            "run_id": "run_wave64_row027",
            "is_synthetic": synthetic,
            "voice_profile_binding": {"path": str(voice_path.resolve()), "sha256": voice_sha},
            "dialogue_contract_binding": {"path": str(contract_path.resolve()), "sha256": contract_sha},
            "line_audio_bindings": [
                {"line_id": "line_001", "path": line1["path"], "sha256": line1["sha256"], "bytes": line1["bytes"]},
                {"line_id": "line_002", "path": line2["path"], "sha256": line2["sha256"], "bytes": line2["bytes"]},
            ],
            "proof_bindings": {
                "asr_proof": {"path": str(asr_path.resolve()), "sha256": _sha256(asr_path)},
                "speaker_proof": {"path": str(speaker_path.resolve()), "sha256": _sha256(speaker_path)},
                "emotion_proof": {"path": str(emotion_path.resolve()), "sha256": _sha256(emotion_path)},
                "playback_review_proof": {"path": str(playback_path.resolve()), "sha256": _sha256(playback_path)},
                "production_runtime_proof": {"path": str(runtime_path.resolve()), "sha256": _sha256(runtime_path)},
                "production_proof_bundle_binding": {"path": str(bundle_path.resolve()), "sha256": _sha256(bundle_path)},
            },
            "thresholds": {
                "max_line_duration_delta_seconds": 0.40,
                "max_asr_segment_timing_delta_seconds": 0.35,
                "max_normalized_wer": 0.25,
                "min_speaker_similarity": 0.80,
                "min_cross_line_continuity": 0.75,
                "min_emotion_confidence": 0.70,
                "min_intensity_score": 0.70,
                "max_clipping_ratio": 0.0001,
                "max_silence_ratio": 0.9950,
                "min_rms_ratio": 0.0050,
            },
        }
        return {
            "request": request,
            "paths": {
                "voice": voice_path,
                "contract": contract_path,
                "line1": Path(line1["path"]),
                "line2": Path(line2["path"]),
                "asr": asr_path,
                "speaker": speaker_path,
                "emotion": emotion_path,
                "playback": playback_path,
                "runtime": runtime_path,
                "bundle": bundle_path,
            },
        }

    def _write_request_and_assert_schema(self, request_path: Path, request: dict[str, Any]) -> None:
        _write_json(request_path, request)
        errors = sorted(self.request_validator.iter_errors(request), key=lambda item: list(item.path))
        self.assertFalse(errors, msg=f"request schema errors: {[e.message for e in errors]}")

    def _assert_evidence_schema(self, output_path: Path) -> dict[str, Any]:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        errors = sorted(self.evidence_validator.iter_errors(payload), key=lambda item: list(item.path))
        self.assertFalse(errors, msg=f"evidence schema errors: {[e.message for e in errors]}")
        return payload

    def _eval_case(self, request: dict[str, Any], output_name: str = "evidence.json") -> tuple[subprocess.CompletedProcess[str], Path]:
        request_path = self.tmpdir / "request.json"
        output_path = self.tmpdir / output_name
        self._write_request_and_assert_schema(request_path, request)
        return _run_eval(request_path, output_path), output_path

    def test_synthetic_blocked_baseline(self) -> None:
        case = self._build_case(synthetic=True)
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertFalse(evidence["overall_pass"])
        self.assertEqual(evidence["gates"]["production_runtime_proof"]["status"], "BLOCKED")
        self.assertIn("synthetic input cannot satisfy production runtime proof gate", evidence["blockers"])

    def test_coherent_non_synthetic_blocked_by_empty_authority_registry(self) -> None:
        case = self._build_case(synthetic=False)
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertEqual(evidence["gates"]["production_proof_authority"]["status"], "BLOCKED")
        self.assertIn("production proof bundle not allowlisted in authority registry", evidence["blockers"])
        self.assertFalse(evidence["overall_pass"])

    def test_asr_only_timing_mismatch_regression(self) -> None:
        case = self._build_case(synthetic=False)
        asr = json.loads(case["paths"]["asr"].read_text(encoding="utf-8"))
        asr["line_results"][0]["end_time"] = asr["line_results"][0]["end_time"] + 0.6
        _write_json(case["paths"]["asr"], asr)
        self._refresh_proof_binding(case["request"], "asr_proof", case["paths"]["asr"])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["asr_proof_sha256"] = _sha256(case["paths"]["asr"])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertEqual(evidence["gates"]["dialogue_timing"]["status"], "FAIL")
        self.assertIn("line line_001 ASR end timing delta exceeds threshold", evidence["gates"]["dialogue_timing"]["blockers"])

    def test_transcript_mismatch_fails_intelligibility(self) -> None:
        case = self._build_case(synthetic=False)
        asr = json.loads(case["paths"]["asr"].read_text(encoding="utf-8"))
        asr["line_results"][0]["transcript"] = "Completely unrelated text."
        _write_json(case["paths"]["asr"], asr)
        self._refresh_proof_binding(case["request"], "asr_proof", case["paths"]["asr"])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["asr_proof_sha256"] = _sha256(case["paths"]["asr"])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertEqual(evidence["gates"]["intelligibility_score"]["status"], "FAIL")

    def test_duration_mismatch_fails_dialogue_timing(self) -> None:
        case = self._build_case(synthetic=False)
        contract = json.loads(case["paths"]["contract"].read_text(encoding="utf-8"))
        contract["lines"][0]["end_time"] = contract["lines"][0]["end_time"] + 1.0
        _write_json(case["paths"]["contract"], contract)
        case["request"]["dialogue_contract_binding"]["sha256"] = _sha256(case["paths"]["contract"])
        for key in ("asr", "speaker", "emotion", "playback", "runtime"):
            payload = json.loads(case["paths"][key].read_text(encoding="utf-8"))
            payload["dialogue_contract_sha256"] = _sha256(case["paths"]["contract"])
            _write_json(case["paths"][key], payload)
            binding_key = "playback_review_proof" if key == "playback" else f"{key}_proof"
            if key == "runtime":
                binding_key = "production_runtime_proof"
            self._refresh_proof_binding(case["request"], binding_key, case["paths"][key])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["dialogue_contract_sha256"] = _sha256(case["paths"]["contract"])
        for field, key in (
            ("asr_proof_sha256", "asr"),
            ("speaker_proof_sha256", "speaker"),
            ("emotion_proof_sha256", "emotion"),
            ("playback_review_proof_sha256", "playback"),
            ("production_runtime_proof_sha256", "runtime"),
        ):
            bundle[field] = _sha256(case["paths"][key])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertEqual(evidence["gates"]["dialogue_timing"]["status"], "FAIL")

    def test_speaker_mismatch_fails(self) -> None:
        case = self._build_case(synthetic=False)
        speaker = json.loads(case["paths"]["speaker"].read_text(encoding="utf-8"))
        speaker["line_results"][1]["speaker_similarity"] = 0.10
        _write_json(case["paths"]["speaker"], speaker)
        self._refresh_proof_binding(case["request"], "speaker_proof", case["paths"]["speaker"])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["speaker_proof_sha256"] = _sha256(case["paths"]["speaker"])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertEqual(evidence["gates"]["voice_continuity"]["status"], "FAIL")

    def test_emotion_mismatch_fails(self) -> None:
        case = self._build_case(synthetic=False)
        emotion = json.loads(case["paths"]["emotion"].read_text(encoding="utf-8"))
        emotion["line_results"][0]["predicted_emotion"] = "angry"
        _write_json(case["paths"]["emotion"], emotion)
        self._refresh_proof_binding(case["request"], "emotion_proof", case["paths"]["emotion"])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["emotion_proof_sha256"] = _sha256(case["paths"]["emotion"])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertEqual(evidence["gates"]["emotional_tone"]["status"], "FAIL")

    def test_missing_playback_blocks(self) -> None:
        case = self._build_case(synthetic=False)
        case["request"]["proof_bindings"]["playback_review_proof"] = None
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["playback_review_proof_sha256"] = "0" * 64
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertEqual(evidence["gates"]["audio_review_record"]["status"], "BLOCKED")

    def test_tampered_audio_hash_is_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        case["request"]["line_audio_bindings"][0]["sha256"] = "0" * 64
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_malformed_wav_is_invalid(self) -> None:
        case = self._build_case(synthetic=False)
        case["paths"]["line1"].write_bytes(b"not-a-valid-wav")
        case["request"]["line_audio_bindings"][0]["bytes"] = case["paths"]["line1"].stat().st_size
        case["request"]["line_audio_bindings"][0]["sha256"] = _sha256(case["paths"]["line1"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_request_unknown_key_rejection(self) -> None:
        case = self._build_case(synthetic=False)
        case["request"]["unexpected"] = True
        request_path = self.tmpdir / "request.json"
        output_path = self.tmpdir / "evidence.json"
        _write_json(request_path, case["request"])
        result = _run_eval(request_path, output_path)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_proof_unknown_key_rejection(self) -> None:
        case = self._build_case(synthetic=False)
        asr = json.loads(case["paths"]["asr"].read_text(encoding="utf-8"))
        asr["unexpected"] = True
        _write_json(case["paths"]["asr"], asr)
        self._refresh_proof_binding(case["request"], "asr_proof", case["paths"]["asr"])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["asr_proof_sha256"] = _sha256(case["paths"]["asr"])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_synthetic_proof_claims_blocked(self) -> None:
        case = self._build_case(synthetic=True)
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertIn("synthetic input cannot pass overall gate", evidence["blockers"])
        self.assertFalse(evidence["overall_pass"])

    def test_nonfinite_rejection(self) -> None:
        case = self._build_case(synthetic=False)
        request_path = self.tmpdir / "request.json"
        output_path = self.tmpdir / "evidence.json"
        request_text = json.dumps(case["request"], indent=2, sort_keys=True)
        request_text = request_text.replace('"max_normalized_wer": 0.25', '"max_normalized_wer": NaN')
        request_path.write_text(request_text, encoding="utf-8")
        result = _run_eval(request_path, output_path)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_atomic_output_preservation_on_invalid_input(self) -> None:
        case = self._build_case(synthetic=False)
        request_path = self.tmpdir / "request.json"
        output_path = self.tmpdir / "evidence.json"
        original_output = {"preserve": True}
        _write_json(output_path, original_output)
        bad_request = copy.deepcopy(case["request"])
        bad_request["line_audio_bindings"][0]["sha256"] = "f" * 64
        self._write_request_and_assert_schema(request_path, bad_request)
        result = _run_eval(request_path, output_path)
        self.assertEqual(result.returncode, 1)
        observed = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(observed, original_output)

    def test_output_schema_validation_on_blocked_report(self) -> None:
        case = self._build_case(synthetic=False)
        case["request"]["proof_bindings"]["playback_review_proof"] = None
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["playback_review_proof_sha256"] = "0" * 64
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        self._assert_evidence_schema(output_path)

    def test_root_escape_rejected(self) -> None:
        case = self._build_case(synthetic=False)
        outside_path = Path("/tmp/wave30_outside.json")
        case["request"]["voice_profile_binding"]["path"] = str(outside_path)
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_root_override_rejected(self) -> None:
        case = self._build_case(synthetic=False)
        request_path = self.tmpdir / "request.json"
        output_path = self.tmpdir / "evidence.json"
        self._write_request_and_assert_schema(request_path, case["request"])
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--root",
                str(self.tmpdir),
                "--input",
                str(request_path),
                "--output",
                str(output_path),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("root must match canonical project root", result.stdout)
        self.assertFalse(output_path.exists())

    def test_output_collision_rejected(self) -> None:
        case = self._build_case(synthetic=False)
        request_path = self.tmpdir / "request.json"
        self._write_request_and_assert_schema(request_path, case["request"])
        result = _run_eval(request_path, request_path)
        self.assertEqual(result.returncode, 1)

    def test_exact_line_set_missing_binding_rejected(self) -> None:
        case = self._build_case(synthetic=False)
        case["request"]["line_audio_bindings"] = [case["request"]["line_audio_bindings"][0]]
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_exact_line_set_extra_binding_rejected(self) -> None:
        case = self._build_case(synthetic=False)
        extra = copy.deepcopy(case["request"]["line_audio_bindings"][0])
        extra["line_id"] = "line_999"
        case["request"]["line_audio_bindings"].append(extra)
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_exact_line_set_duplicate_binding_rejected(self) -> None:
        case = self._build_case(synthetic=False)
        duplicate = copy.deepcopy(case["request"]["line_audio_bindings"][0])
        case["request"]["line_audio_bindings"][1] = duplicate
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_duplicate_audio_reuse_rejected(self) -> None:
        case = self._build_case(synthetic=False)
        first = case["request"]["line_audio_bindings"][0]
        case["request"]["line_audio_bindings"][1]["path"] = first["path"]
        case["request"]["line_audio_bindings"][1]["sha256"] = first["sha256"]
        case["request"]["line_audio_bindings"][1]["bytes"] = first["bytes"]
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_duplicate_speaker_line_ids_rejected(self) -> None:
        case = self._build_case(synthetic=False)
        speaker = json.loads(case["paths"]["speaker"].read_text(encoding="utf-8"))
        speaker["line_results"][1]["line_id"] = speaker["line_results"][0]["line_id"]
        _write_json(case["paths"]["speaker"], speaker)
        self._refresh_proof_binding(case["request"], "speaker_proof", case["paths"]["speaker"])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["speaker_proof_sha256"] = _sha256(case["paths"]["speaker"])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_duplicate_emotion_line_ids_rejected(self) -> None:
        case = self._build_case(synthetic=False)
        emotion = json.loads(case["paths"]["emotion"].read_text(encoding="utf-8"))
        emotion["line_results"][1]["line_id"] = emotion["line_results"][0]["line_id"]
        _write_json(case["paths"]["emotion"], emotion)
        self._refresh_proof_binding(case["request"], "emotion_proof", case["paths"]["emotion"])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["emotion_proof_sha256"] = _sha256(case["paths"]["emotion"])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_invalid_metric_ranges_rejected(self) -> None:
        case = self._build_case(synthetic=False)
        speaker = json.loads(case["paths"]["speaker"].read_text(encoding="utf-8"))
        speaker["line_results"][0]["speaker_similarity"] = 1.5
        _write_json(case["paths"]["speaker"], speaker)
        self._refresh_proof_binding(case["request"], "speaker_proof", case["paths"]["speaker"])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["speaker_proof_sha256"] = _sha256(case["paths"]["speaker"])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_decorative_model_hash_rejected(self) -> None:
        case = self._build_case(synthetic=False)
        asr = json.loads(case["paths"]["asr"].read_text(encoding="utf-8"))
        asr["model_sha256"] = "not-a-sha"
        _write_json(case["paths"]["asr"], asr)
        self._refresh_proof_binding(case["request"], "asr_proof", case["paths"]["asr"])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["asr_proof_sha256"] = _sha256(case["paths"]["asr"])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_path.exists())

    def test_empty_normalized_text_and_transcript_block(self) -> None:
        case = self._build_case(synthetic=False)
        contract = json.loads(case["paths"]["contract"].read_text(encoding="utf-8"))
        contract["lines"][0]["text"] = "!!!"
        _write_json(case["paths"]["contract"], contract)
        case["request"]["dialogue_contract_binding"]["sha256"] = _sha256(case["paths"]["contract"])
        asr = json.loads(case["paths"]["asr"].read_text(encoding="utf-8"))
        asr["dialogue_contract_sha256"] = _sha256(case["paths"]["contract"])
        asr["line_results"][0]["transcript"] = "..."
        _write_json(case["paths"]["asr"], asr)
        self._refresh_proof_binding(case["request"], "asr_proof", case["paths"]["asr"])
        for key in ("speaker", "emotion", "playback", "runtime"):
            payload = json.loads(case["paths"][key].read_text(encoding="utf-8"))
            payload["dialogue_contract_sha256"] = _sha256(case["paths"]["contract"])
            _write_json(case["paths"][key], payload)
            binding_key = "playback_review_proof" if key == "playback" else f"{key}_proof"
            if key == "runtime":
                binding_key = "production_runtime_proof"
            self._refresh_proof_binding(case["request"], binding_key, case["paths"][key])
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["dialogue_contract_sha256"] = _sha256(case["paths"]["contract"])
        for field, key in (
            ("asr_proof_sha256", "asr"),
            ("speaker_proof_sha256", "speaker"),
            ("emotion_proof_sha256", "emotion"),
            ("playback_review_proof_sha256", "playback"),
            ("production_runtime_proof_sha256", "runtime"),
        ):
            bundle[field] = _sha256(case["paths"][key])
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(case["request"], "production_proof_bundle_binding", case["paths"]["bundle"])
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertEqual(evidence["gates"]["intelligibility_score"]["status"], "FAIL")
        self.assertIn("line line_001 expected text normalizes to empty tokens", evidence["blockers"])
        self.assertIn("line line_001 ASR transcript normalizes to empty tokens", evidence["blockers"])

    def test_unapproved_proof_bundle_blocked(self) -> None:
        case = self._build_case(synthetic=False)
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertIn("production proof bundle not allowlisted in authority registry", evidence["blockers"])

    def test_proof_bundle_proof_hash_mismatch_blocks(self) -> None:
        case = self._build_case(synthetic=False)
        bundle = json.loads(case["paths"]["bundle"].read_text(encoding="utf-8"))
        bundle["asr_proof_sha256"] = "0" * 64
        _write_json(case["paths"]["bundle"], bundle)
        self._refresh_proof_binding(
            case["request"],
            "production_proof_bundle_binding",
            case["paths"]["bundle"],
        )
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertIn(
            "production proof bundle mismatch for asr_proof_sha256",
            evidence["blockers"],
        )

    def test_pcm_decode_8_16_24_32_bit(self) -> None:
        for width in (1, 2, 3, 4):
            with self.subTest(sample_width=width):
                case = self._build_case(synthetic=True, sample_width=width, amplitude_ratio=0.5)
                result, output_path = self._eval_case(case["request"], output_name=f"evidence_{width}.json")
                self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
                evidence = self._assert_evidence_schema(output_path)
                widths = {item["sample_width_bytes"] for item in evidence["metrics"]["line_audio_metrics"]}
                self.assertEqual(widths, {width})

    def test_computed_clipping_rejection(self) -> None:
        case = self._build_case(synthetic=True, sample_width=2, amplitude_ratio=1.0)
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertEqual(evidence["gates"]["audio_review_record"]["status"], "FAIL")
        self.assertTrue(any("clipping ratio exceeds threshold" in item for item in evidence["blockers"]))

    def test_computed_silence_rejection(self) -> None:
        case = self._build_case(synthetic=True, sample_width=2, amplitude_ratio=0.0)
        result, output_path = self._eval_case(case["request"])
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        evidence = self._assert_evidence_schema(output_path)
        self.assertEqual(evidence["gates"]["audio_review_record"]["status"], "FAIL")
        self.assertTrue(any("silence ratio exceeds threshold" in item for item in evidence["blockers"]))


if __name__ == "__main__":
    unittest.main()
