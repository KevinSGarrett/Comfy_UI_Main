#!/usr/bin/env python3
"""Evaluate the immutable Wave64 Kokoro audition without creating new speech."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import soundfile as sf


EXPECTED_TEXT = "We hold the frame steady and move on the beat."
EXPECTED_SPEEDS = (1.00, 1.15, 1.30)
EXPECTED_SAMPLE_RATE_HZ = 24000
EXPECTED_SAMPLE_COUNT = 72000
EXPECTED_DURATION_SECONDS = 3.0
EXPECTED_CANDIDATE_COUNT = 3


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding(path: Path, expected_sha256: str | None = None, label: str = "artifact") -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"{label} is missing: {resolved}")
    actual = sha256(resolved)
    if expected_sha256 and actual != expected_sha256.lower():
        raise ValueError(f"{label} SHA-256 mismatch")
    return {"path": str(resolved), "sha256": actual, "bytes": resolved.stat().st_size}


def load_json(path: Path, expected_sha256: str | None, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    bound = binding(path, expected_sha256, label)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain one JSON object")
    return payload, bound


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ValueError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_manifest(manifest: dict[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
    if manifest.get("artifact_type") != "wave64_kokoro_dialogue_audition_manifest":
        raise ValueError("unexpected audition manifest type")
    contract = manifest.get("control_contract")
    candidates = manifest.get("candidates")
    if not isinstance(contract, dict) or not isinstance(candidates, list):
        raise ValueError("audition manifest is structurally incomplete")
    if contract.get("text") != EXPECTED_TEXT:
        raise ValueError("audition text mismatch")
    if tuple(float(value) for value in contract.get("speeds", [])) != EXPECTED_SPEEDS:
        raise ValueError("audition speed contract mismatch")
    if contract.get("candidate_count") != EXPECTED_CANDIDATE_COUNT or len(candidates) != EXPECTED_CANDIDATE_COUNT:
        raise ValueError("audition must contain exactly three candidates")
    prohibited = {
        "retry_allowed": False,
        "adaptive_speed_tuning_allowed": False,
        "truncation_allowed": False,
        "time_stretch_allowed": False,
        "loudness_normalization_allowed": False,
    }
    for key, expected in prohibited.items():
        if contract.get(key) is not expected:
            raise ValueError(f"audition contract violates {key}")
    if contract.get("emotion_class") is not None:
        raise ValueError("focused delivery must not be force-mapped to an emotion class")

    verified: list[dict[str, Any]] = []
    expected_ordinals = list(range(1, EXPECTED_CANDIDATE_COUNT + 1))
    if [row.get("ordinal") for row in candidates] != expected_ordinals:
        raise ValueError("candidate ordinals are not immutable and contiguous")
    for row, expected_speed in zip(candidates, EXPECTED_SPEEDS, strict=True):
        if float(row.get("speed")) != expected_speed or row.get("retry_count") != 0:
            raise ValueError("candidate speed or retry count mismatch")
        if any(row.get(key) is not False for key in ("speech_truncated", "time_stretched", "loudness_normalized")):
            raise ValueError("candidate contains prohibited media mutation")
        packaged = row.get("packaged_audio")
        raw = row.get("raw_audio")
        if not isinstance(packaged, dict) or not isinstance(raw, dict):
            raise ValueError("candidate lacks raw or packaged binding")
        packaged_path = Path(packaged["path"])
        raw_path = Path(raw["path"])
        packaged_binding = binding(packaged_path, packaged["sha256"], "packaged candidate")
        raw_binding = binding(raw_path, raw["sha256"], "raw candidate")
        if packaged_binding["bytes"] != packaged["bytes"] or raw_binding["bytes"] != raw["bytes"]:
            raise ValueError("candidate byte count mismatch")
        info = sf.info(packaged_path)
        if info.samplerate != EXPECTED_SAMPLE_RATE_HZ or info.channels != 1 or info.frames != EXPECTED_SAMPLE_COUNT:
            raise ValueError("packaged candidate does not satisfy exact PCM timing")
        if row.get("raw_sample_count") + row.get("padding_samples") != EXPECTED_SAMPLE_COUNT:
            raise ValueError("padding lineage does not reconcile to 72,000 samples")
        verified.append({**row, "packaged_path": packaged_path, "raw_path": raw_path})
    return verified


def speaker_threshold(openslr: dict[str, Any]) -> float:
    validation = openslr.get("threshold_validation")
    if not isinstance(validation, dict):
        raise ValueError("OpenSLR31 evidence lacks threshold validation")
    if validation.get("speaker_disjoint_validation_pass") is not True:
        raise ValueError("OpenSLR31 speaker threshold is not validated")
    if validation.get("threshold_deployment_allowed_for_chain_specific_evaluation") is not True:
        raise ValueError("OpenSLR31 threshold deployment is not allowed")
    return float(validation["threshold"])


def metric_gate(
    *,
    wer: float,
    dnsmos_ovrl: float,
    dnsmos_floor: float,
    continuity_similarity: float,
    continuity_threshold: float,
    timing_pass: bool,
    max_wer: float,
) -> dict[str, bool]:
    return {
        "exact_timing_pass": timing_pass,
        "asr_wer_pass": wer <= max_wer,
        "dnsmos_calibrated_floor_pass": dnsmos_ovrl >= dnsmos_floor,
        "synthetic_voice_continuity_pass": continuity_similarity >= continuity_threshold,
    }


def select_candidate(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = [row for row in rows if all(row["gates"].values())]
    if not eligible:
        return None
    return sorted(eligible, key=lambda row: (-float(row["metrics"]["dnsmos"]["OVRL"]), int(row["ordinal"])))[0]


def build(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = Path(args.audition_manifest).resolve()
    manifest, manifest_binding = load_json(
        manifest_path, args.expected_audition_manifest_sha256, "audition manifest"
    )
    candidates = verify_manifest(manifest, manifest_path)
    cv3, cv3_binding = load_json(Path(args.cv3_evidence), args.expected_cv3_evidence_sha256, "CV3 evidence")
    openslr, openslr_binding = load_json(
        Path(args.openslr_evidence), args.expected_openslr_evidence_sha256, "OpenSLR31 evidence"
    )
    emotion, emotion_binding = load_json(
        Path(args.emotion_evidence), args.expected_emotion_evidence_sha256, "emotion2vec evidence"
    )
    if cv3.get("acceptance", {}).get("whisper_path_executed") is not True:
        raise ValueError("CV3 Whisper calibration is not executable authority")
    if cv3.get("acceptance", {}).get("dnsmos_path_executed") is not True:
        raise ValueError("CV3 DNSMOS calibration is not executable authority")
    if emotion.get("calibration", {}).get("model_execution_pass") is not True:
        raise ValueError("emotion2vec calibration evidence is incomplete")
    labels = emotion.get("calibration", {}).get("reference_labels", [])
    if "focused" in labels:
        raise ValueError("focused unexpectedly appears as a calibrated emotion class")

    adapter_path = Path(args.cv3_adapter_script).resolve()
    adapter_binding = binding(adapter_path, args.expected_cv3_adapter_sha256, "CV3 adapter")
    cv3_module = load_module(adapter_path, "wave64_cv3_for_kokoro")
    source = cv3.get("source_authority")
    if not isinstance(source, dict):
        raise ValueError("CV3 evidence lacks source authority")
    whisper_dir = Path(source["whisper"]["path"]).resolve().parent
    cv3_root = Path(source["dnsmos_source"]["path"]).resolve().parents[2]
    speaker_root = cv3_root / "utils/3D-Speaker"
    speaker_checkpoint = Path(source["speaker_checkpoint"]["path"]).resolve()
    dnsmos_source = Path(source["dnsmos_source"]["path"]).resolve()
    dnsmos_dir = Path(source["dnsmos_models"]["sig_bak_ovr.onnx"]["path"]).resolve().parent

    whisper = cv3_module.WhisperEvaluator(whisper_dir, Path(args.transformers_overlay).resolve(), args.device)
    speaker = cv3_module.SpeakerEvaluator(speaker_root, speaker_checkpoint, args.device)
    dnsmos = cv3_module.DNSMOSEvaluator(dnsmos_source, dnsmos_dir)
    embeddings = {row["candidate_id"]: speaker.embedding(row["packaged_path"]) for row in candidates}
    threshold = speaker_threshold(openslr)
    pairwise: list[dict[str, Any]] = []
    for left, right in combinations(candidates, 2):
        similarity = speaker.similarity(embeddings[left["candidate_id"]], embeddings[right["candidate_id"]])
        pairwise.append(
            {
                "left_candidate_id": left["candidate_id"],
                "right_candidate_id": right["candidate_id"],
                "similarity": similarity,
                "threshold": threshold,
                "pass": similarity >= threshold,
            }
        )

    calibration_mos = [float(row["dnsmos"]["OVRL"]) for row in cv3["calibration"]["samples"]]
    dnsmos_floor = min(calibration_mos)
    evaluated: list[dict[str, Any]] = []
    for row in candidates:
        transcript = whisper.transcribe(row["packaged_path"])
        wer = cv3_module.normalized_wer(EXPECTED_TEXT, transcript)
        mos = dnsmos.score(row["packaged_path"])
        similarities = [
            pair["similarity"]
            for pair in pairwise
            if row["candidate_id"] in (pair["left_candidate_id"], pair["right_candidate_id"])
        ]
        continuity_min = min(similarities)
        gates = metric_gate(
            wer=wer,
            dnsmos_ovrl=float(mos["OVRL"]),
            dnsmos_floor=dnsmos_floor,
            continuity_similarity=continuity_min,
            continuity_threshold=threshold,
            timing_pass=True,
            max_wer=args.max_wer,
        )
        evaluated.append(
            {
                "candidate_id": row["candidate_id"],
                "ordinal": row["ordinal"],
                "speed": row["speed"],
                "artifact_binding": binding(row["packaged_path"], row["packaged_audio"]["sha256"]),
                "raw_artifact_binding": binding(row["raw_path"], row["raw_audio"]["sha256"]),
                "metrics": {
                    "asr_transcript": transcript,
                    "normalized_wer": wer,
                    "dnsmos": mos,
                    "dnsmos_reference_percentile": cv3_module.percentile_rank(calibration_mos, float(mos["OVRL"])),
                    "synthetic_voice_continuity_min_similarity": continuity_min,
                    "raw_duration_seconds": row["raw_sample_count"] / EXPECTED_SAMPLE_RATE_HZ,
                    "packaged_duration_seconds": EXPECTED_DURATION_SECONDS,
                    "pace_wpm_from_raw_speech": len(EXPECTED_TEXT.rstrip(".").split()) * 60.0
                    / (row["raw_sample_count"] / EXPECTED_SAMPLE_RATE_HZ),
                },
                "gates": gates,
                "automated_eligibility_pass": all(gates.values()),
            }
        )

    selected = select_candidate(evaluated)
    selected_summary = None
    if selected:
        selected_summary = {
            "candidate_id": selected["candidate_id"],
            "ordinal": selected["ordinal"],
            "speed": selected["speed"],
            "artifact_binding": selected["artifact_binding"],
            "selection_rule": "highest_DNSMOS_OVRL_among_automated_eligible_then_lowest_ordinal",
            "automated_eligibility_pass": True,
            "human_playback_review_required": True,
        }

    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_kokoro_audition_evaluation",
        "execution_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "PASS_AUTOMATED_CANDIDATE_ELIGIBLE_HUMAN_PLAYBACK_REQUIRED" if selected else "BLOCKED_NO_AUTOMATED_ELIGIBLE_CANDIDATE",
        "classification": "KOKORO_AUDITION_AUTOMATED_EVALUATION_COMPLETE",
        "bindings": {
            "audition_manifest": manifest_binding,
            "runner": manifest["runner"],
            "control_contract": manifest["control_contract"]["binding"],
            "cv3_evidence": cv3_binding,
            "openslr31_evidence": openslr_binding,
            "emotion2vec_evidence": emotion_binding,
            "cv3_adapter": adapter_binding,
        },
        "thresholds": {
            "max_normalized_wer": args.max_wer,
            "dnsmos_ovrl_calibrated_reference_floor": dnsmos_floor,
            "synthetic_voice_continuity_similarity": threshold,
        },
        "pairwise_synthetic_voice_continuity": pairwise,
        "candidates": evaluated,
        "selected_candidate": selected_summary,
        "acceptance": {
            "immutable_batch_lineage_pass": True,
            "all_three_candidates_evaluated": len(evaluated) == EXPECTED_CANDIDATE_COUNT,
            "automated_candidate_eligibility_pass": selected is not None,
            "emotion_class_not_applicable_without_force_mapping": True,
            "delivery_style_human_review_pass": False,
            "intensity_human_review_pass": False,
            "human_playback_review_pass": False,
            "production_authority_pass": False,
        },
        "remaining_blockers": [
            "Independent human playback review of exact content, intelligibility, character match, delivery style, intensity, pacing, pronunciation, naturalness, and technical cleanliness is required.",
            "A distinct final-production authority remains required after playback review.",
        ],
        "boundaries": {
            "speaker_metric_claim_scope": "synthetic voice continuity across the immutable speed batch only",
            "human_reference_identity_claimed": False,
            "emotion_class_forced_mapping_performed": False,
            "candidate_regenerated": False,
            "ec2_started": False,
            "s3_mutated": False,
            "mask_truth_consumed": False,
            "wave71_activated": False,
            "jira_mutated": False,
            "promotion_claimed": False,
        },
        "row_complete": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audition-manifest", required=True)
    parser.add_argument("--expected-audition-manifest-sha256", required=True)
    parser.add_argument("--cv3-evidence", required=True)
    parser.add_argument("--expected-cv3-evidence-sha256", required=True)
    parser.add_argument("--openslr-evidence", required=True)
    parser.add_argument("--expected-openslr-evidence-sha256", required=True)
    parser.add_argument("--emotion-evidence", required=True)
    parser.add_argument("--expected-emotion-evidence-sha256", required=True)
    parser.add_argument("--cv3-adapter-script", required=True)
    parser.add_argument("--expected-cv3-adapter-sha256", required=True)
    parser.add_argument("--transformers-overlay", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--max-wer", type=float, default=0.2)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()
    try:
        if output_dir.exists():
            raise ValueError(f"output directory already exists: {output_dir}")
        result = build(args)
        output_dir.mkdir(parents=True, exist_ok=False)
        output = output_dir / "kokoro_audition_evaluation.json"
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"status": result["status"], "evaluation": binding(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
