#!/usr/bin/env python3
"""Package the Wave64 playback abstention and rejected replacement take."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ORIGINAL_CANDIDATE_SHA256 = "18b6d51cca9d9c5541bac621c09fd9059f521d8969ba5b25fa881c9284180c73"
EXPECTED_REPLACEMENT_SEED = 64028


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"required artifact is missing: {path}")
    return {"path": str(path.resolve()), "sha256": sha256(path), "bytes": path.stat().st_size}


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def validate_inputs(
    original_execution_path: Path,
    replacement_runtime_path: Path,
    replacement_proof_dir: Path,
) -> dict[str, Any]:
    original = load_json(original_execution_path, "original playback execution")
    if original.get("classification") != "MODEL_BACKED_PLAYBACK_REVIEW_ABSTAINED_UNSUPPORTED_REQUIRED_CATEGORY":
        raise ValueError("original playback execution classification mismatch")
    if original.get("status") != "BLOCKED" or original.get("proof_emitted") is not False:
        raise ValueError("original playback execution must be blocked with no proof emitted")
    original_candidate = original.get("bindings", {}).get("candidate_audio", {})
    if original_candidate.get("sha256") != ORIGINAL_CANDIDATE_SHA256:
        raise ValueError("original playback execution candidate hash mismatch")
    defects = original.get("decision", {}).get("defects", [])
    if not any(isinstance(defect, dict) and defect.get("code") == "CRITICAL_CONTENT_MISMATCH" for defect in defects):
        raise ValueError("original playback execution is missing the critical content mismatch")
    if original.get("decision", {}).get("unsupported_required_categories") != [
        "stylistic_fit.target_emotion",
        "stylistic_fit.target_intensity",
    ]:
        raise ValueError("original playback execution unsupported-category boundary mismatch")

    runtime = load_json(replacement_runtime_path, "replacement runtime manifest")
    if runtime.get("runtime", {}).get("seed") != EXPECTED_REPLACEMENT_SEED:
        raise ValueError("replacement runtime seed mismatch")
    if runtime.get("runtime", {}).get("runtime_executed") is not True:
        raise ValueError("replacement runtime did not execute")
    runtime_output = runtime.get("output")
    if not isinstance(runtime_output, dict):
        raise ValueError("replacement runtime output is missing")
    raw_wav = Path(str(runtime_output.get("path", ""))).resolve()
    raw_binding = binding(raw_wav)
    if raw_binding["sha256"] != runtime_output.get("sha256") or raw_binding["bytes"] != runtime_output.get("bytes"):
        raise ValueError("replacement raw WAV binding mismatch")

    packet_path = replacement_proof_dir / "packet_manifest.json"
    packet = load_json(packet_path, "replacement proof packet")
    if packet.get("result") != "pass" or packet.get("execution_passed") is not True:
        raise ValueError("replacement proof packaging did not complete")
    asr = packet.get("asr")
    if not isinstance(asr, dict) or asr.get("pass") is not False:
        raise ValueError("replacement ASR packet must record a failed intelligibility gate")
    if float(asr.get("normalized_wer")) <= float(asr.get("threshold")):
        raise ValueError("replacement WER does not exceed its threshold")
    conformed_wav = Path(str(packet.get("verified_media", {}).get("media_path", ""))).resolve()
    conformed_binding = binding(conformed_wav)
    if conformed_binding["sha256"] != packet.get("verified_media", {}).get("sha256"):
        raise ValueError("replacement conformed WAV binding mismatch")

    proof_files = {}
    for name in ("packet_manifest.json", "dialogue_contract.json", "voice_profile.json"):
        proof_files[name] = binding(replacement_proof_dir / name)
    proof_files[conformed_wav.name] = conformed_binding
    return {
        "original": original,
        "original_binding": binding(original_execution_path),
        "replacement_runtime": runtime,
        "replacement_runtime_binding": binding(replacement_runtime_path),
        "replacement_raw_wav": raw_binding,
        "replacement_packet": packet,
        "replacement_proof_files": proof_files,
    }


def copy_atomic(source: Path, destination: Path, overwrite: bool) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not overwrite:
        raise ValueError(f"destination exists and overwrite is disabled: {destination}")
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent))
    os.close(descriptor)
    temp_path = Path(temp_name)
    try:
        shutil.copyfile(source, temp_path)
        os.replace(temp_path, destination)
    finally:
        temp_path.unlink(missing_ok=True)
    return binding(destination)


def write_json_atomic(path: Path, payload: dict[str, Any], overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise ValueError(f"destination exists and overwrite is disabled: {path}")
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def package(args: argparse.Namespace) -> dict[str, Any]:
    original_path = Path(args.original_execution).resolve()
    runtime_path = Path(args.replacement_runtime_manifest).resolve()
    proof_dir = Path(args.replacement_proof_dir).resolve()
    artifact_dir = Path(args.artifact_dir).resolve()
    qa_path = Path(args.qa_evidence).resolve()
    tracker_path = Path(args.tracker_evidence).resolve()
    validated = validate_inputs(original_path, runtime_path, proof_dir)

    if artifact_dir.exists() and not args.overwrite:
        raise ValueError(f"artifact directory exists and overwrite is disabled: {artifact_dir}")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    copied = {
        "original_playback_execution": copy_atomic(
            original_path, artifact_dir / "original_model_backed_playback_execution.json", args.overwrite
        ),
        "replacement_runtime_manifest": copy_atomic(
            runtime_path, artifact_dir / "replacement_runtime_manifest.json", args.overwrite
        ),
    }
    raw_source = Path(validated["replacement_raw_wav"]["path"])
    copied["replacement_raw_wav"] = copy_atomic(raw_source, artifact_dir / raw_source.name, args.overwrite)
    for name, source_binding in validated["replacement_proof_files"].items():
        source = Path(source_binding["path"])
        copied[f"replacement_proof_{name}"] = copy_atomic(
            source, artifact_dir / f"replacement_{name}", args.overwrite
        )

    original = validated["original"]
    packet = validated["replacement_packet"]
    evidence = {
        "schema_version": "1.0",
        "artifact_type": "wave64_model_backed_playback_and_replacement_evidence",
        "execution_timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "status": "BLOCKED",
        "classification": "MODEL_BACKED_PLAYBACK_ABSTENTION_AND_REPLACEMENT_INTELLIGIBILITY_REJECTION",
        "tracker_ids": ["TRK-W64-025", "TRK-W64-027", "TRK-W64-031"],
        "item_ids": ["ITEM-W64-025", "ITEM-W64-027", "ITEM-W64-031"],
        "artifact_bindings": copied,
        "original_candidate": {
            "sha256": ORIGINAL_CANDIDATE_SHA256,
            "model_backed_playback_status": original["status"],
            "proof_emitted": original["proof_emitted"],
            "normalized_wer": original["decision"]["normalized_wer"],
            "content_defects": original["decision"]["defects"],
            "unsupported_required_categories": original["decision"]["unsupported_required_categories"],
            "technical_scores": original["decision"]["category_scores"],
        },
        "replacement_candidate": {
            "seed": EXPECTED_REPLACEMENT_SEED,
            "raw_sha256": validated["replacement_raw_wav"]["sha256"],
            "conformed_sha256": packet["verified_media"]["sha256"],
            "speech_truncated": packet["timeline_conformance"]["speech_truncated"],
            "asr_transcript": packet["asr"]["transcript"],
            "normalized_wer": packet["asr"]["normalized_wer"],
            "wer_threshold": packet["asr"]["threshold"],
            "intelligibility_pass": packet["asr"]["pass"],
            "rejected": True,
        },
        "gates": {
            "producer_model_and_calibration_hash_binding_pass": True,
            "original_decode_and_technical_measurement_pass": True,
            "original_exact_content_pass": False,
            "original_stylistic_taxonomy_supported": False,
            "original_playback_proof_emitted": False,
            "replacement_runtime_execution_pass": True,
            "replacement_zero_truncation_pass": packet["timeline_conformance"]["speech_truncated"] is False,
            "replacement_intelligibility_pass": False,
            "independent_playback_review_pass": False,
            "production_review_authority_pass": False,
            "row_complete": False,
            "certification_pass": False,
        },
        "authority_boundary": {
            "playback_producer_allowlisted": True,
            "production_review_authorities_mutated": False,
            "production_review_bundle_allowlist_mutated": False,
            "no_candidate_promoted": True,
            "no_additional_generation_authorized_by_this_evidence": True,
        },
        "next_action": (
            "Keep both candidates rejected. Advance a genuinely perceptual audio-model calibration or bind an independent "
            "reference speaker and supported style taxonomy before generating another dialogue take."
        ),
    }
    write_json_atomic(qa_path, evidence, args.overwrite)
    write_json_atomic(tracker_path, evidence, args.overwrite)
    if sha256(qa_path) != sha256(tracker_path):
        raise ValueError("QA and Tracker evidence mirrors differ")
    return {
        "status": evidence["status"],
        "classification": evidence["classification"],
        "qa_evidence": binding(qa_path),
        "tracker_evidence": binding(tracker_path),
        "artifact_count": len(copied),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-execution", required=True)
    parser.add_argument("--replacement-runtime-manifest", required=True)
    parser.add_argument("--replacement-proof-dir", required=True)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--qa-evidence", required=True)
    parser.add_argument("--tracker-evidence", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        result = package(parse_args())
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
