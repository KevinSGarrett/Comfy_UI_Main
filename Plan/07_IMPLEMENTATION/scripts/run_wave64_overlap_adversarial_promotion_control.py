#!/usr/bin/env python3
"""Render a deterministic overlap diagnostic and exercise fail-closed speech controls."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


TARGET_RATE = 24000
TRANSCRIPT = "We hold the frame steady and move on the beat."
EXPECTED_SOURCE_HASHES = {
    "kokoro": "a212653c029f5677b97bba8c769186fc11d29b561b4ca19a2344ff294a5fdd56",
    "qwen": "ff8325a1c2f8613d599af69284f5c4693d996a581230ccbbbb1aeba7affa9815",
}


class ControlError(RuntimeError):
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
        raise ControlError(f"required artifact is missing: {path}")
    observed = sha256_file(path)
    if expected_sha256 and observed != expected_sha256.lower():
        raise ControlError(f"artifact SHA-256 mismatch: {path}")
    return {"path": str(path), "sha256": observed, "bytes": path.stat().st_size}


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ControlError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ControlError(f"JSON root must be an object: {path}")
    return value


def write_json_new(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ControlError(f"refusing to overwrite immutable artifact: {path}")
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=True, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return bind(path)


def read_mono(path: Path) -> tuple[np.ndarray, int]:
    audio, rate = sf.read(str(path), dtype="float32", always_2d=True)
    if audio.size == 0 or rate <= 0 or not np.isfinite(audio).all():
        raise ControlError(f"invalid decoded audio: {path}")
    return audio.mean(axis=1).astype(np.float64), int(rate)


def resample(audio: np.ndarray, source_rate: int, target_rate: int = TARGET_RATE) -> np.ndarray:
    if source_rate == target_rate:
        return audio.copy()
    divisor = math.gcd(source_rate, target_rate)
    return resample_poly(audio, target_rate // divisor, source_rate // divisor).astype(np.float64)


def _write_pcm24(path: Path, audio: np.ndarray) -> dict[str, Any]:
    if path.exists():
        raise ControlError(f"refusing to overwrite immutable artifact: {path}")
    if not np.isfinite(audio).all() or float(np.max(np.abs(audio))) >= 0.999:
        raise ControlError("overlap render is non-finite or would clip")
    sf.write(str(path), audio, TARGET_RATE, subtype="PCM_24")
    return {**bind(path), "sample_rate_hz": TARGET_RATE, "channels": 2, "samples_per_channel": int(audio.shape[0]), "subtype": "PCM_24"}


def render_overlap(kokoro_path: Path, qwen_path: Path, output_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    kokoro, kokoro_rate = read_mono(kokoro_path)
    qwen, qwen_rate = read_mono(qwen_path)
    kokoro = resample(kokoro, kokoro_rate)
    qwen = resample(qwen, qwen_rate)
    qwen_start = int(round(1.1 * TARGET_RATE))
    total = max(kokoro.size, qwen_start + qwen.size)
    stem_a = np.zeros((total, 2), dtype=np.float64)
    stem_b = np.zeros((total, 2), dtype=np.float64)
    gain_a = np.full(kokoro.size, 0.42, dtype=np.float64)
    overlap_end = min(kokoro.size, qwen_start + qwen.size)
    gain_a[qwen_start:overlap_end] = 0.22
    stem_a[: kokoro.size, 0] = kokoro * gain_a
    stem_a[: kokoro.size, 1] = kokoro * gain_a * 0.25
    stem_b[qwen_start : qwen_start + qwen.size, 0] = qwen * 0.42 * 0.25
    stem_b[qwen_start : qwen_start + qwen.size, 1] = qwen * 0.42
    mix = stem_a + stem_b
    output_dir.mkdir(parents=True, exist_ok=False)
    bindings = {
        "kokoro_left_stem": _write_pcm24(output_dir / "kokoro_left_stem_pcm24_stereo.wav", stem_a),
        "qwen_right_priority_stem": _write_pcm24(output_dir / "qwen_right_priority_stem_pcm24_stereo.wav", stem_b),
        "overlap_mix": _write_pcm24(output_dir / "kokoro_qwen_overlap_mix_pcm24_stereo.wav", mix),
    }
    decoded = {}
    for name, record in bindings.items():
        decoded[name], observed_rate = sf.read(record["path"], dtype="float64", always_2d=True)
        if observed_rate != TARGET_RATE:
            raise ControlError("written overlap artifact sample rate drift")
    residual = decoded["overlap_mix"] - decoded["kokoro_left_stem"] - decoded["qwen_right_priority_stem"]
    overlap_samples = max(0, overlap_end - qwen_start)
    a_left = float(np.sqrt(np.mean(stem_a[:, 0] ** 2)))
    a_right = float(np.sqrt(np.mean(stem_a[:, 1] ** 2)))
    b_left = float(np.sqrt(np.mean(stem_b[:, 0] ** 2)))
    b_right = float(np.sqrt(np.mean(stem_b[:, 1] ** 2)))
    metrics = {
        "sample_rate_hz": TARGET_RATE,
        "samples_per_channel": total,
        "duration_seconds": round(total / TARGET_RATE, 9),
        "kokoro_start_sample": 0,
        "qwen_start_sample": qwen_start,
        "overlap_start_sample": qwen_start,
        "overlap_end_sample": overlap_end,
        "overlap_samples": overlap_samples,
        "priority_duck_db": round(20.0 * math.log10(0.22 / 0.42), 6),
        "kokoro_left_separation_db": round(20.0 * math.log10(max(a_left, 1e-12) / max(a_right, 1e-12)), 6),
        "qwen_right_separation_db": round(20.0 * math.log10(max(b_right, 1e-12) / max(b_left, 1e-12)), 6),
        "mix_peak_absolute": round(float(np.max(np.abs(mix))), 9),
        "mix_clipping_ratio": round(float(np.mean(np.abs(mix) >= 0.999)), 9),
        "decoded_sample_sum_max_residual": round(float(np.max(np.abs(residual))), 9),
    }
    gates = {
        "source_ownership_from_isolated_stems_pass": True,
        "overlap_interval_present_pass": overlap_samples > int(0.5 * TARGET_RATE),
        "priority_duck_pass": metrics["priority_duck_db"] <= -5.0,
        "spatial_separation_pass": metrics["kokoro_left_separation_db"] >= 10.0 and metrics["qwen_right_separation_db"] >= 10.0,
        "sample_sum_integrity_pass": metrics["decoded_sample_sum_max_residual"] <= 0.000001,
        "technical_clipping_pass": metrics["mix_clipping_ratio"] == 0.0,
        "independent_diarization_pass": False,
        "independent_overlap_intelligibility_pass": False,
        "human_playback_review_pass": False,
        "production_authority_pass": False,
    }
    return bindings, {"metrics": metrics, "gates": gates}


def evaluate_defect_matrix(records: dict[str, dict[str, Any]], bindings: dict[str, dict[str, Any]]) -> dict[str, Any]:
    kokoro = records["kokoro"]
    qwen = records["qwen"]
    cosy = records["cosyvoice2"]
    chatterbox = records["chatterbox"]
    parler = records["parler"]
    cases = [
        {
            "fixture_id": "kokoro_automated_positive_control",
            "candidate_sha256": bindings["kokoro_wav"]["sha256"],
            "documented_classification": kokoro.get("status"),
            "expected_classification": "PASS_AUTOMATED_CANDIDATE_ELIGIBLE_HUMAN_PLAYBACK_REQUIRED",
            "expected_defects": ["missing_human_playback_review", "missing_production_authority"],
            "detected_defects": sorted([
                *(["missing_human_playback_review"] if kokoro.get("acceptance", {}).get("human_playback_review_pass") is False else []),
                *(["missing_production_authority"] if kokoro.get("acceptance", {}).get("production_authority_pass") is False else []),
            ]),
        },
        {
            "fixture_id": "qwen_raw_timing_and_authority_negative_control",
            "candidate_sha256": bindings["qwen_wav"]["sha256"],
            "documented_classification": qwen.get("classification"),
            "expected_classification": "PASS_QWEN3_CLONE_CHAIN_SPECIFIC_IDENTITY_PRODUCTION_AUTHORITY_BLOCKED",
            "expected_defects": ["raw_dialogue_timing_fail", "missing_independent_playback", "missing_production_reference_authority"],
            "detected_defects": sorted([
                *(["raw_dialogue_timing_fail"] if qwen.get("gates", {}).get("raw_dialogue_timing_pass") is False else []),
                *(["missing_independent_playback"] if qwen.get("gates", {}).get("independent_playback_review_pass") is False else []),
                *(["missing_production_reference_authority"] if qwen.get("gates", {}).get("production_reference_authority_pass") is False else []),
            ]),
        },
    ]
    for name, record, expected_classification in (
        ("cosyvoice2", cosy, "FAIL_COSYVOICE2_DIALOGUE_TIMING"),
        ("chatterbox", chatterbox, "FAIL_CHATTERBOX_DIALOGUE_TIMING"),
    ):
        gates = record.get("gates", {})
        cases.append({
            "fixture_id": f"{name}_timing_taxonomy_authority_negative_control",
            "candidate_sha256": bindings[f"{name}_wav"]["sha256"],
            "documented_classification": record.get("classification"),
            "expected_classification": expected_classification,
            "expected_defects": ["dialogue_timing_fail", "unsupported_emotion_taxonomy", "unmeasured_intensity", "missing_independent_playback", "missing_production_authority"],
            "detected_defects": sorted([
                *(["dialogue_timing_fail"] if gates.get("dialogue_timing_pass") is False else []),
                *(["unsupported_emotion_taxonomy"] if gates.get("target_emotion_taxonomy_supported") is False else []),
                *(["unmeasured_intensity"] if gates.get("target_intensity_taxonomy_status") == "unmeasured_no_calibrated_intensity_evaluator" else []),
                *(["missing_independent_playback"] if gates.get("independent_playback_review_pass") is False else []),
                *(["missing_production_authority"] if gates.get("production_proof_authority_pass") is False else []),
            ]),
        })
    expected_parler = ["missing emotion_proof", "missing playback_review_proof", "missing production_proof_bundle_binding", "missing speaker_proof"]
    cases.append({
        "fixture_id": "parler_evidence_completeness_negative_control",
        "candidate_sha256": bindings["parler_wav"]["sha256"],
        "documented_classification": "overall_pass_false",
        "expected_classification": "overall_pass_false",
        "expected_defects": expected_parler,
        "detected_defects": sorted(set(parler.get("blockers", [])) & set(expected_parler)),
    })
    for case in cases:
        case["classification_match_pass"] = case["documented_classification"] == case["expected_classification"]
        case["defect_set_match_pass"] = set(case["expected_defects"]) == set(case["detected_defects"])
        case["detection_pass"] = case["classification_match_pass"] and case["defect_set_match_pass"]
    coverage = {
        "timing": True,
        "authority": True,
        "control_taxonomy": True,
        "evidence_completeness": True,
        "hallucination": False,
        "repetition": False,
        "truncation_defect": False,
        "difficult_text": False,
        "identity_drift": False,
        "noise": False,
        "reverb": False,
        "multilingual": False,
    }
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_speech_immutable_adversarial_defect_matrix",
        "cases": cases,
        "known_fixture_detection_rate": round(sum(case["detection_pass"] for case in cases) / len(cases), 6),
        "known_fixture_detection_pass": all(case["detection_pass"] for case in cases),
        "coverage": coverage,
        "full_required_category_coverage_pass": all(coverage.values()),
        "candidate_media_mutated": False,
        "rejected_candidates_regenerated": False,
        "row_complete": False,
    }


def _load_promotion_module(root: Path):
    path = root / "Plan/07_IMPLEMENTATION/scripts/manage_wave64_speech_promotion.py"
    spec = importlib.util.spec_from_file_location("wave64_speech_promotion", path)
    if not spec or not spec.loader:
        raise ControlError("unable to load promotion control")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_blocked_request(candidate_id: str, artifact: dict[str, Any], character_version: str, authority: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "character_version": character_version,
        "artifact": artifact,
        "authority": {
            "identity_policy": authority.get("identity_policy"),
            "reference_id": authority.get("reference_id"),
            "reference_sha256": authority.get("reference_sha256"),
            "model_id": authority.get("model_id"),
            "approved_use": authority.get("approved_use"),
            "rights_valid": authority.get("rights_valid"),
            "production_authorized": authority.get("production_authorized", False),
            "reference_revoked": False,
            "model_revoked": False,
        },
        "evaluation": {
            "record_sha256": authority.get("evaluation_sha256"),
            "hard_gates_pass": authority.get("hard_gates_pass", False),
            "ranking_complete": authority.get("ranking_complete", False),
        },
        "review": {
            "playback_review_pass": False,
            "playback_record_sha256": None,
            "final_production_authority_pass": False,
            "production_record_sha256": None,
            "roles_are_distinct": False,
            "artifact_sha256": artifact["sha256"],
        },
        "rollback": {"action": "restore_previous_active_or_none"},
        "content_based_suppression": False,
    }


def exercise_promotion_control(module: Any, output_dir: Path, candidate_requests: list[dict[str, Any]]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    decisions = []
    for request in candidate_requests:
        blockers = module.validate_promotion_request(request)
        decisions.append({
            "candidate_id": request["candidate_id"],
            "artifact_sha256": request["artifact"]["sha256"],
            "decision": "refused",
            "status": "BLOCKED",
            "blockers": blockers,
            "ledger_mutated": False,
        })
    if not all(item["blockers"] for item in decisions):
        raise ControlError("a current candidate unexpectedly passed promotion authority")

    probe_path = output_dir / "promotion_control_probe.bin"
    probe_path.write_bytes(b"W64_PROMOTION_CONTROL_PROBE_V1\n")
    probe_binding = bind(probe_path)
    probe_request = {
        "schema_version": "1.0",
        "candidate_id": "W64-CONTROL-PROBE-NOT-MEDIA",
        "character_version": "CONTROL-PROBE-1",
        "artifact": probe_binding,
        "authority": {
            "identity_policy": "synthetic_control_probe",
            "reference_id": "CONTROL-REFERENCE",
            "reference_sha256": "1" * 64,
            "model_id": "CONTROL-MODEL",
            "approved_use": "promotion_control_test_only",
            "rights_valid": True,
            "production_authorized": True,
            "reference_revoked": False,
            "model_revoked": False,
        },
        "evaluation": {"record_sha256": "2" * 64, "hard_gates_pass": True, "ranking_complete": True},
        "review": {
            "playback_review_pass": True,
            "playback_record_sha256": "3" * 64,
            "final_production_authority_pass": True,
            "production_record_sha256": "4" * 64,
            "roles_are_distinct": True,
            "artifact_sha256": probe_binding["sha256"],
        },
        "rollback": {"action": "restore_previous_active_or_none"},
        "content_based_suppression": False,
    }
    ledger_path = output_dir / "promotion_control_probe_ledger.json"
    ledger = module.PromotionLedger(ledger_path)
    first = ledger.promote(probe_request)
    replay = ledger.promote(probe_request)
    invalidated = ledger.revoke(reference_ids={"CONTROL-REFERENCE"})
    revoked_replay = ledger.promote(probe_request)
    rollback_request = json.loads(json.dumps(probe_request))
    rollback_request["candidate_id"] = "W64-CONTROL-PROBE-ROLLBACK-NOT-MEDIA"
    rollback_request["authority"]["reference_id"] = "CONTROL-REFERENCE-ROLLBACK"
    rollback_request["authority"]["reference_sha256"] = "5" * 64
    rollback_first = ledger.promote(rollback_request)
    rollback = ledger.rollback("W64-CONTROL-PROBE-ROLLBACK-NOT-MEDIA")
    rollback_replay = ledger.rollback("W64-CONTROL-PROBE-ROLLBACK-NOT-MEDIA")
    return {
        "current_candidate_decisions": decisions,
        "all_current_candidates_refused_pass": all(item["decision"] == "refused" and item["ledger_mutated"] is False for item in decisions),
        "synthetic_non_media_control_probe": {
            "probe_artifact": probe_binding,
            "ledger": bind(ledger_path),
            "atomic_write_pass": first.get("ledger_mutated") is True,
            "idempotent_replay_pass": replay.get("idempotent_replay") is True and replay.get("ledger_mutated") is False,
            "revocation_invalidation_pass": (
                invalidated == ["W64-CONTROL-PROBE-NOT-MEDIA"]
                and revoked_replay.get("decision") == "refused"
                and "authority_reference_revoked_by_ledger" in revoked_replay.get("blockers", [])
            ),
            "rollback_pass": (
                rollback_first.get("decision") == "promoted"
                and rollback.get("decision") == "rolled_back"
                and rollback_replay.get("idempotent_replay") is True
            ),
            "production_candidate": False,
            "media_promotion_performed": False,
        },
        "production_promotion_performed": False,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = args.project_root.resolve()
    paths = {
        "kokoro_wav": args.kokoro_wav.resolve(),
        "qwen_wav": args.qwen_wav.resolve(),
        "cosyvoice2_wav": args.cosyvoice2_wav.resolve(),
        "chatterbox_wav": args.chatterbox_wav.resolve(),
        "parler_wav": args.parler_wav.resolve(),
        "kokoro_evaluation": args.kokoro_evaluation.resolve(),
        "qwen_evaluation": args.qwen_evaluation.resolve(),
        "cosyvoice2_evaluation": args.cosyvoice2_evaluation.resolve(),
        "chatterbox_evaluation": args.chatterbox_evaluation.resolve(),
        "parler_evaluation": args.parler_evaluation.resolve(),
    }
    expected = {
        "kokoro_wav": EXPECTED_SOURCE_HASHES["kokoro"],
        "qwen_wav": EXPECTED_SOURCE_HASHES["qwen"],
    }
    bindings = {name: bind(path, expected.get(name)) for name, path in paths.items()}
    source_hashes_before = {name: record["sha256"] for name, record in bindings.items()}
    records = {
        "kokoro": load_object(paths["kokoro_evaluation"]),
        "qwen": load_object(paths["qwen_evaluation"]),
        "cosyvoice2": load_object(paths["cosyvoice2_evaluation"]),
        "chatterbox": load_object(paths["chatterbox_evaluation"]),
        "parler": load_object(paths["parler_evaluation"]),
    }
    overlap_dir = args.output_dir.resolve()
    overlap_bindings, overlap = render_overlap(paths["kokoro_wav"], paths["qwen_wav"], overlap_dir)
    defect_matrix = evaluate_defect_matrix(records, bindings)
    defect_binding = write_json_new(overlap_dir / "immutable_adversarial_defect_matrix.json", defect_matrix)
    promotion_module = _load_promotion_module(root)
    candidate_requests = [
        build_blocked_request("KOKORO-C01-L001-01", bindings["kokoro_wav"], "C01-PENDING", {
            "identity_policy": "designed_synthetic_voice", "reference_id": "KOKORO-AF-HEART", "model_id": "KOKORO-0.9.4",
            "approved_use": "automated_audition_only", "rights_valid": True, "production_authorized": False,
            "reference_sha256": None, "evaluation_sha256": bindings["kokoro_evaluation"]["sha256"], "hard_gates_pass": True, "ranking_complete": True,
        }),
        build_blocked_request("W64-QWEN3-BASE-ICL-CLONE-SEED-12401", bindings["qwen_wav"], "C01-PENDING", {
            "identity_policy": "chain_specific_public_domain_reference", "reference_id": "LIBRIVOX-EVAL", "model_id": "QWEN3-TTS-BASE-1.7B",
            "approved_use": "chain_specific_evaluation_only", "rights_valid": True, "production_authorized": False,
            "reference_sha256": "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932",
            "evaluation_sha256": bindings["qwen_evaluation"]["sha256"], "hard_gates_pass": False, "ranking_complete": False,
        }),
        build_blocked_request("W64-COSYVOICE2-ZERO-SHOT-L001", bindings["cosyvoice2_wav"], "C01-PENDING", {
            "identity_policy": "evaluation_reference_only", "reference_id": "LIBRIVOX-EVAL", "model_id": "COSYVOICE2",
            "approved_use": "evaluation_only", "rights_valid": True, "production_authorized": False,
            "reference_sha256": "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932",
            "evaluation_sha256": bindings["cosyvoice2_evaluation"]["sha256"], "hard_gates_pass": False, "ranking_complete": False,
        }),
        build_blocked_request("W64-CHATTERBOX-L001", bindings["chatterbox_wav"], "C01-PENDING", {
            "identity_policy": "evaluation_reference_only", "reference_id": "LIBRIVOX-EVAL", "model_id": "CHATTERBOX",
            "approved_use": "evaluation_only", "rights_valid": True, "production_authorized": False,
            "reference_sha256": "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932",
            "evaluation_sha256": bindings["chatterbox_evaluation"]["sha256"], "hard_gates_pass": False, "ranking_complete": False,
        }),
        build_blocked_request("W64-PARLER-L001", bindings["parler_wav"], "C01-PENDING", {
            "identity_policy": "profile_candidate_not_authorized", "reference_id": "PARLER-PROFILE", "model_id": "PARLER-TTS",
            "approved_use": "evaluation_only", "rights_valid": True, "production_authorized": False,
            "reference_sha256": None, "evaluation_sha256": bindings["parler_evaluation"]["sha256"], "hard_gates_pass": False, "ranking_complete": False,
        }),
    ]
    promotion = exercise_promotion_control(promotion_module, overlap_dir, candidate_requests)
    promotion_binding = write_json_new(overlap_dir / "promotion_gate_decisions.json", promotion)
    source_hashes_after = {name: sha256_file(path) for name, path in paths.items()}
    if source_hashes_before != source_hashes_after:
        raise ControlError("an immutable source changed during the control run")
    manifest = {
        "schema_version": "1.0",
        "artifact_type": "wave64_rows140_142_144_runtime_manifest",
        "classification": "W64_ROWS140_142_144_CONTROLS_EXECUTED_PRODUCTION_BLOCKED",
        "sources": bindings,
        "source_transcript": TRANSCRIPT,
        "overlap_artifacts": overlap_bindings,
        "overlap": overlap,
        "adversarial_matrix": {**defect_matrix, "binding": defect_binding},
        "promotion_control": {**promotion, "binding": promotion_binding},
        "source_hashes_unchanged": True,
        "boundaries": {
            "candidate_regenerated": False,
            "candidate_media_mutated": False,
            "human_review_fabricated": False,
            "production_promotion_performed": False,
            "ec2_started": False,
            "s3_mutated": False,
            "mask_or_wave71_touched": False,
            "jira_mutated": False,
            "content_based_suppression": False,
        },
        "row_complete": False,
    }
    manifest_binding = write_json_new(overlap_dir / "wave64_rows140_142_144_runtime_manifest.json", manifest)
    return {"classification": manifest["classification"], "manifest": manifest_binding, "row_complete": False}


def _root_path(root: Path, relative: str) -> Path:
    return (root / relative).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output-dir", type=Path, required=True)
    root = Path(__file__).resolve().parents[3]
    defaults = {
        "kokoro_wav": "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_kokoro_audition_20260715T131034-0500/L001_C01_kokoro_speed_1.00_pcm3s.wav",
        "qwen_wav": "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_qwen3_tts_base_icl_clone_20260715T195516-0500/qwen3_tts_base_icl_clone_seed12401.wav",
        "cosyvoice2_wav": "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_cosyvoice2_corrected_reference_20260715T064000-0500/L001_C01_cosyvoice2_zero_shot.wav",
        "chatterbox_wav": "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_chatterbox_dialogue_20260715T092901-0500/L001_C01_chatterbox.wav",
        "parler_wav": "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_parler_tts_proof_20260714T185510-0500/L001_C01_parler_tts_conformed.wav",
        "kokoro_evaluation": "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_kokoro_audition_20260715T131034-0500/kokoro_audition_evaluation.json",
        "qwen_evaluation": "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_qwen3_tts_base_icl_clone_20260715T195516-0500/qwen3_tts_base_icl_clone_seed12401.evaluation.json",
        "cosyvoice2_evaluation": "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_cosyvoice2_corrected_reference_20260715T064000-0500/cosyvoice2_candidate_evaluation.json",
        "chatterbox_evaluation": "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_chatterbox_dialogue_20260715T092901-0500/chatterbox_candidate_evaluation.json",
        "parler_evaluation": "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_parler_tts_proof_20260714T185510-0500/strict_evidence.json",
    }
    for name, relative in defaults.items():
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, default=_root_path(root, relative))
    args = parser.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        print(json.dumps({"classification": "W64_ROWS140_142_144_CONTROL_RUN_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
