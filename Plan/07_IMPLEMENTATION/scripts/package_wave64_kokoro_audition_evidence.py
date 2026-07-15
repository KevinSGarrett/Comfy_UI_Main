#!/usr/bin/env python3
"""Package the Wave64 Kokoro automated-eligible audition without promoting it."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REQUEST_SCHEMA = PROJECT_ROOT / "Plan/08_SCHEMAS/wave64_human_audio_review_request.schema.json"
EXPECTED_SELECTED_SHA256 = "a212653c029f5677b97bba8c769186fc11d29b561b4ca19a2344ff294a5fdd56"
EXPECTED_MANIFEST_SHA256 = "9fe8faa0a5739298800c6ba32e176afd4ca5147fe4903e57c4617ac17a4f130e"
EXPECTED_EVALUATION_SHA256 = "8faf279222b4cb84fd88e2ac40e7ac2825e4771edc4f9763d3b30fbea64abbf3"
EXPECTED_REQUEST_SHA256 = "1f770e84bf076b8bfddbc73bc726ffdd86612b18f0c872e6f1b0f032acfd35e1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind(path: Path, expected: str, label: str) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"{label} is missing: {resolved}")
    actual = sha256(resolved)
    if actual != expected:
        raise ValueError(f"{label} SHA-256 mismatch")
    return {"path": str(resolved), "sha256": actual, "bytes": resolved.stat().st_size}


def load_bound(path: Path, expected: str, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    artifact = bind(path, expected, label)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return payload, artifact


def verify_request(request: dict[str, Any], selected: dict[str, Any], evaluation_binding: dict[str, Any]) -> None:
    schema = json.loads(REQUEST_SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(request))
    if errors:
        raise ValueError(f"human playback request schema failed: {errors[0].message}")
    if request["artifact_binding"]["sha256"] != selected["sha256"]:
        raise ValueError("human playback request does not bind the selected candidate")
    if request["expected"]["emotion_class"] is not None:
        raise ValueError("human playback request force-maps an unsupported emotion class")
    if request["expected"]["delivery_style"] != "focused" or request["expected"]["intensity"] != "controlled":
        raise ValueError("human playback request style contract drift")
    evidence_hashes = {row["sha256"] for row in request["automated_evidence_bindings"]}
    if evaluation_binding["sha256"] not in evidence_hashes:
        raise ValueError("human playback request does not bind the automated evaluation")
    disclosed_paths = [request["artifact_binding"]["path"]] + [
        row["path"] for row in request["automated_evidence_bindings"]
    ]
    if request["blinding"]["engine_identity_hidden_initial_pass"] and any(
        "kokoro" in path.lower() for path in disclosed_paths
    ):
        raise ValueError("human playback request claims engine blinding while bound paths disclose Kokoro")


def package(args: argparse.Namespace) -> dict[str, Any]:
    selected = bind(Path(args.selected_candidate), EXPECTED_SELECTED_SHA256, "selected candidate")
    manifest, manifest_binding = load_bound(
        Path(args.audition_manifest), EXPECTED_MANIFEST_SHA256, "audition manifest"
    )
    evaluation, evaluation_binding = load_bound(
        Path(args.evaluation), EXPECTED_EVALUATION_SHA256, "audition evaluation"
    )
    request, request_binding = load_bound(
        Path(args.human_request), EXPECTED_REQUEST_SHA256, "human playback request"
    )
    verify_request(request, selected, evaluation_binding)
    selected_eval = evaluation.get("selected_candidate")
    if evaluation.get("status") != "PASS_AUTOMATED_CANDIDATE_ELIGIBLE_HUMAN_PLAYBACK_REQUIRED":
        raise ValueError("evaluation is not automated-eligible")
    if not isinstance(selected_eval, dict) or selected_eval.get("artifact_binding", {}).get("sha256") != selected["sha256"]:
        raise ValueError("evaluation selected-candidate binding mismatch")
    if evaluation.get("acceptance", {}).get("automated_candidate_eligibility_pass") is not True:
        raise ValueError("evaluation eligibility gate is not true")
    if evaluation.get("acceptance", {}).get("human_playback_review_pass") is not False:
        raise ValueError("evaluation incorrectly claims human playback completion")
    if manifest.get("acceptance", {}).get("no_retry_pass") is not True:
        raise ValueError("audition manifest does not prove the no-retry boundary")
    if len(manifest.get("candidates", [])) != 3:
        raise ValueError("audition manifest candidate count drift")
    selected_rows = [
        row for row in evaluation.get("candidates", [])
        if row.get("candidate_id") == selected_eval["candidate_id"]
    ]
    if len(selected_rows) != 1:
        raise ValueError("evaluation selected candidate metrics are missing or ambiguous")
    selected_metrics = selected_rows[0].get("metrics", {})
    contract = manifest.get("control_contract", {})

    artifact_dir = Path(args.artifact_dir).resolve()
    durable_files = {}
    for path in sorted(artifact_dir.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file():
            durable_files[path.name] = {
                "path": str(path),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_kokoro_audition_automated_eligibility_evidence",
        "execution_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "PASS_AUTOMATED_CANDIDATE_ELIGIBLE_HUMAN_PLAYBACK_REQUIRED",
        "classification": "KOKORO_C01_DESIGNED_SYNTHETIC_BASELINE_AUTOMATED_ELIGIBLE",
        "artifact_bindings": {
            "selected_candidate": selected,
            "audition_manifest": manifest_binding,
            "automated_evaluation": evaluation_binding,
            "human_playback_review_request": request_binding,
            "durable_bundle": durable_files,
        },
        "selected_candidate": {
            "candidate_id": selected_eval["candidate_id"],
            "speed": selected_eval["speed"],
            "sha256": selected["sha256"],
            "bytes": selected["bytes"],
            "duration_seconds": 3.0,
            "sample_rate_hz": 24000,
            "sample_count": 72000,
            "transcript": selected_metrics["asr_transcript"],
            "normalized_wer": selected_metrics["normalized_wer"],
            "dnsmos_ovrl": selected_metrics["dnsmos"]["OVRL"],
            "synthetic_voice_continuity_min_similarity": selected_metrics[
                "synthetic_voice_continuity_min_similarity"
            ],
            "identity_policy": contract["voice_identity_policy"],
            "voice": contract["voice"],
            "engine": contract["engine"],
            "engine_version": contract["engine_version"],
            "model_revision": contract["model_revision"],
        },
        "runtime_observation": {
            "execution_device": "local_cpu",
            "kokoro": "0.9.4",
            "torch": "2.12.1+cpu",
            "en_core_web_sm": "3.8.0",
            "first_run_language_payload_install_observed": True,
            "media_generation_count": 3,
            "evaluation_retry_count": 1,
            "evaluation_retry_reason": "first invocation stopped in PowerShell argument preparation before Python launched",
            "candidate_regeneration_performed": False,
        },
        "acceptance": {
            "immutable_three_candidate_batch_pass": True,
            "exact_timing_pass": True,
            "exact_content_asr_pass": True,
            "dnsmos_calibrated_floor_pass": True,
            "synthetic_voice_continuity_pass": True,
            "automated_candidate_eligibility_pass": True,
            "human_playback_request_schema_pass": True,
            "human_playback_review_pass": False,
            "delivery_style_human_review_pass": False,
            "intensity_human_review_pass": False,
            "production_review_authority_pass": False,
            "final_voice_certification_pass": False,
            "row_complete": False,
        },
        "remaining_blockers": [
            {
                "classification": "Blocked_Human_Audio_Playback_Review_Missing",
                "reason": "The selected exact hash passed automated gates and has a prepared review request, but no human playback record or validated playback proof exists yet.",
            },
            {
                "classification": "Blocked_Audio_Production_Review_Authority_Missing",
                "reason": "A distinct final-production authority and allowlisted production review bundle remain absent.",
            },
        ],
        "affected_rows": [
            "TRK-W64-025",
            "ITEM-W64-025",
            "TRK-W64-026",
            "ITEM-W64-026",
            "TRK-W64-027",
            "ITEM-W64-027",
            "TRK-W64-031",
            "ITEM-W64-031",
        ],
        "boundaries": {
            "human_reference_identity_claimed": False,
            "emotion_class_forced_mapping_performed": False,
            "human_playback_review_claimed": False,
            "production_promotion_claimed": False,
            "rejected_candidates_rerun": False,
            "ec2_started": False,
            "s3_mutated": False,
            "mask_truth_consumed": False,
            "wave71_activated": False,
            "jira_mutated": False,
        },
        "row_complete": False,
    }


def write_mirrors(payload: dict[str, Any], paths: list[Path]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
    if any(sha256(path) != digest for path in paths):
        raise ValueError("evidence mirrors diverged")
    return digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--selected-candidate", required=True)
    parser.add_argument("--audition-manifest", required=True)
    parser.add_argument("--evaluation", required=True)
    parser.add_argument("--human-request", required=True)
    parser.add_argument("--evidence-output", required=True)
    parser.add_argument("--tracker-output", required=True)
    args = parser.parse_args()
    try:
        payload = package(args)
        digest = write_mirrors(payload, [Path(args.evidence_output), Path(args.tracker_output)])
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"status": payload["status"], "sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
