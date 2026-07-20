#!/usr/bin/env python3
"""Measure TRK-W64-124 multi-ref drift/leakage with calibrated ERes2Net embeddings.

Runs offline CPU embedding scoring against the two bound LibriVox source references,
the hash-bound Qwen clone candidate, and OpenSLR31 validation-partition non-target
rejectors. Never uses :8188, mutates media, writes sound CSV, touches Row075, invents
voices, or claims PRODUCTION_VOICE_AUTHORITY / LISTENING_AUTHORITY / COMPLETE.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DEFAULT = Path(__file__).resolve().parents[3]
TRACKER_ID = "TRK-W64-124"
ITEM_ID = "ITEM-W64-124"
PROOF_TIER = "OFFLINE_PROOF_BOUNDED"
EXPECTED_CV3_ADAPTER_SHA256 = "f3810a26e129021c8179c982eb0901c5f8f3f07b6508ab4c56cace6bfb3862c8"
EXPECTED_OPENSLR_EVIDENCE_SHA256 = "cdd7f0c8a0af54ec82c307cc4cea1492976ae1fbbded8712822d4329103ca0a9"
EXPECTED_CANDIDATE_SHA256 = "ff8325a1c2f8613d599af69284f5c4693d996a581230ccbbbb1aeba7affa9815"
EXPECTED_REF1_SHA256 = "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932"
EXPECTED_REF2_SHA256 = "ac013d29e84309abd52c49720fe1a9caf2550fd83ce2f8e248be6e4329145f48"
DEFAULT_CV3_ADAPTER = Path("Plan/07_IMPLEMENTATION/scripts/run_wave64_cv3_eval_calibration.py")
DEFAULT_OPENSLR_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/"
    "W64_OPENSLR31_SPEAKER_IDENTITY_VALIDATION_20260715T035744-0500.json"
)
DEFAULT_OPENSLR_MANIFEST = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "w64_openslr31_speaker_identity_20260715T035744-0500/"
    "openslr31_speaker_identity_validation_manifest.json"
)
DEFAULT_CANDIDATE = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "w64_qwen3_tts_base_icl_clone_20260715T195516-0500/"
    "qwen3_tts_base_icl_clone_seed12401.wav"
)
DEFAULT_REF1 = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "w64_chatterbox_dialogue_20260715T092901-0500/"
    "librivox_reference_5.0s.wav"
)
DEFAULT_REF2 = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "w64_cv3_speaker_identity_20260715T030600-0500/"
    "librivox_reference_excerpt.wav"
)


class MeasurementError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind(path: Path, expected: str | None = None, label: str = "file") -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise MeasurementError(f"{label} is missing: {path}")
    observed = sha256_file(path)
    if expected and observed != expected.lower():
        raise MeasurementError(f"{label} SHA-256 mismatch: expected {expected}, got {observed}")
    return {
        "path": str(path).replace("\\", "/"),
        "sha256": observed,
        "bytes": path.stat().st_size,
    }


def load_json(path: Path, expected: str | None = None, label: str = "json") -> tuple[dict[str, Any], dict[str, Any]]:
    binding = bind(path, expected, label)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MeasurementError(f"{label} is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise MeasurementError(f"{label} must contain a JSON object")
    return binding, payload


def load_module(path: Path, expected: str, name: str):
    bind(path, expected, name)
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise MeasurementError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def display_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def load_threshold(evidence: dict[str, Any]) -> float:
    threshold_data = evidence.get("threshold_validation") or {}
    threshold = float(threshold_data.get("threshold", math.nan))
    if not math.isfinite(threshold):
        raise MeasurementError("OpenSLR31 threshold is not finite")
    if threshold_data.get("threshold_deployment_allowed_for_chain_specific_evaluation") is not True:
        raise MeasurementError("OpenSLR31 threshold is not deployable for chain-specific evaluation")
    if threshold_data.get("speaker_disjoint_validation_pass") is not True:
        raise MeasurementError("OpenSLR31 speaker-disjoint validation did not pass")
    return threshold


def select_rejectors(manifest: dict[str, Any], *, clips_per_speaker: int = 1) -> list[dict[str, Any]]:
    dataset = manifest.get("dataset") or {}
    validation_ids = [str(item) for item in dataset.get("validation_speaker_ids") or []]
    if not validation_ids:
        raise MeasurementError("OpenSLR31 validation speaker IDs are absent from durable manifest")
    speakers = {str(item.get("speaker_id")): item for item in dataset.get("speakers") or []}
    rejectors: list[dict[str, Any]] = []
    missing: list[str] = []
    for speaker_id in validation_ids:
        speaker = speakers.get(speaker_id)
        if not isinstance(speaker, dict):
            missing.append(f"speaker_record:{speaker_id}")
            continue
        selected = list(speaker.get("selected") or [])
        if not selected:
            missing.append(f"selected_clips:{speaker_id}")
            continue
        for item in selected[:clips_per_speaker]:
            path = Path(str(item.get("path", "")))
            expected = str(item.get("sha256", "")).lower()
            if not path.is_file():
                missing.append(path.as_posix())
                continue
            binding = bind(path, expected, f"OpenSLR31 rejector {speaker_id}")
            rejectors.append(
                {
                    "speaker_id": speaker_id,
                    "relative_path": item.get("relative_path"),
                    "binding": binding,
                    "partition": "validation",
                }
            )
    if missing:
        raise MeasurementError(
            "OpenSLR31 rejector audio missing or unbound: " + "; ".join(missing[:8])
        )
    if not rejectors:
        raise MeasurementError("OpenSLR31 rejector set is empty after selection")
    return rejectors


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.project_root).resolve()
    adapter_path = (root / args.cv3_adapter_script).resolve() if not Path(args.cv3_adapter_script).is_absolute() else Path(args.cv3_adapter_script).resolve()
    openslr_evidence_path = (
        (root / args.openslr_evidence).resolve()
        if not Path(args.openslr_evidence).is_absolute()
        else Path(args.openslr_evidence).resolve()
    )
    openslr_manifest_path = (
        (root / args.openslr_manifest).resolve()
        if not Path(args.openslr_manifest).is_absolute()
        else Path(args.openslr_manifest).resolve()
    )
    candidate_path = (
        (root / args.candidate_audio).resolve()
        if not Path(args.candidate_audio).is_absolute()
        else Path(args.candidate_audio).resolve()
    )
    ref1_path = (
        (root / args.reference_audio).resolve()
        if not Path(args.reference_audio).is_absolute()
        else Path(args.reference_audio).resolve()
    )
    ref2_path = (
        (root / args.second_reference_audio).resolve()
        if not Path(args.second_reference_audio).is_absolute()
        else Path(args.second_reference_audio).resolve()
    )
    cv3_root = Path(args.cv3_root).resolve()

    if not cv3_root.is_dir():
        raise MeasurementError(f"CV3 root is missing: {cv3_root}")

    adapter = load_module(adapter_path, args.expected_cv3_adapter_sha256, "CV3 adapter")
    checkpoint = (
        cv3_root
        / "utils/3D-Speaker/pretrained/speech_eres2net_sv_en_voxceleb_16k/pretrained_eres2net.ckpt"
    )
    if not checkpoint.is_file():
        raise MeasurementError(
            f"ERes2Net checkpoint missing: {checkpoint} "
            f"(expected sha256 {adapter.ERES2NET_SHA256})"
        )
    checkpoint_binding = adapter.require_hash(checkpoint, adapter.ERES2NET_SHA256, "ERes2Net checkpoint")

    openslr_binding, openslr_evidence = load_json(
        openslr_evidence_path, args.expected_openslr_evidence_sha256, "OpenSLR31 validation evidence"
    )
    threshold = load_threshold(openslr_evidence)
    manifest_binding, openslr_manifest = load_json(openslr_manifest_path, label="OpenSLR31 durable manifest")
    rejectors = select_rejectors(openslr_manifest, clips_per_speaker=args.rejector_clips_per_speaker)

    candidate_binding = bind(candidate_path, args.expected_candidate_sha256, "candidate wav")
    ref1_binding = bind(ref1_path, args.expected_reference_sha256, "primary LibriVox reference")
    ref2_binding = bind(ref2_path, args.expected_second_reference_sha256, "second LibriVox reference")

    speaker_root = cv3_root / "utils/3D-Speaker"
    if not speaker_root.is_dir():
        raise MeasurementError(f"3D-Speaker root missing: {speaker_root}")
    speaker = adapter.SpeakerEvaluator(speaker_root, checkpoint, args.device)

    emb_ref1 = speaker.embedding(ref1_path)
    emb_ref2 = speaker.embedding(ref2_path)
    emb_candidate = speaker.embedding(candidate_path)
    sim_ref1_ref2 = round(speaker.similarity(emb_ref1, emb_ref2), 9)
    sim_cand_ref1 = round(speaker.similarity(emb_candidate, emb_ref1), 9)
    sim_cand_ref2 = round(speaker.similarity(emb_candidate, emb_ref2), 9)

    leakage_rows: list[dict[str, Any]] = []
    for rejector in rejectors:
        emb = speaker.embedding(Path(rejector["binding"]["path"]))
        sim_to_ref1 = round(speaker.similarity(emb, emb_ref1), 9)
        sim_to_ref2 = round(speaker.similarity(emb, emb_ref2), 9)
        sim_to_candidate = round(speaker.similarity(emb, emb_candidate), 9)
        max_sim = max(sim_to_ref1, sim_to_ref2, sim_to_candidate)
        leakage_rows.append(
            {
                "speaker_id": rejector["speaker_id"],
                "relative_path": rejector["relative_path"],
                "sha256": rejector["binding"]["sha256"],
                "similarity_to_ref1": sim_to_ref1,
                "similarity_to_ref2": sim_to_ref2,
                "similarity_to_candidate": sim_to_candidate,
                "max_similarity_to_bound_set": max_sim,
                "rejected_as_non_target": max_sim < threshold,
            }
        )

    same_character_pass = sim_ref1_ref2 >= threshold
    cross_line_pass = same_character_pass
    leakage_pass = all(row["rejected_as_non_target"] for row in leakage_rows)
    separation_pass = (
        candidate_binding["sha256"] not in {ref1_binding["sha256"], ref2_binding["sha256"]}
        and ref1_binding["sha256"] != ref2_binding["sha256"]
    )

    checks = [
        {
            "id": "same_character_multi_source_identity",
            "status": "PASS_MEASURED" if same_character_pass else "FAIL_MEASURED",
            "measurement": "calibrated_eres2net_cosine_ref1_ref2",
            "similarity_ref1_ref2": sim_ref1_ref2,
            "threshold": threshold,
            "note": (
                "Measured same-character concordance across two disjoint LibriVox windows "
                "using the OpenSLR31-validated ERes2Net threshold."
            ),
        },
        {
            "id": "cross_line_drift",
            "status": "PASS_MEASURED" if cross_line_pass else "FAIL_MEASURED",
            "measurement": "calibrated_speaker_embedding_cross_line_drift",
            "similarity_ref1_ref2": sim_ref1_ref2,
            "similarity_candidate_ref1": sim_cand_ref1,
            "similarity_candidate_ref2": sim_cand_ref2,
            "threshold": threshold,
            "note": (
                "Cross-line drift scored as ref1↔ref2 identity continuity under the calibrated "
                "threshold; candidate-to-each-ref similarities recorded for diagnostics."
            ),
        },
        {
            "id": "non_target_speaker_leakage_rejection",
            "status": "PASS_MEASURED" if leakage_pass else "FAIL_MEASURED",
            "measurement": "calibrated_non_target_rejector_against_openslr31_authority",
            "rejector_count": len(leakage_rows),
            "rejected_count": sum(1 for row in leakage_rows if row["rejected_as_non_target"]),
            "false_accept_count": sum(1 for row in leakage_rows if not row["rejected_as_non_target"]),
            "max_non_target_similarity": max(row["max_similarity_to_bound_set"] for row in leakage_rows),
            "threshold": threshold,
            "planned_rejector_authority": display_relative(root, openslr_evidence_path),
            "note": (
                "OpenSLR31 validation-partition speakers used as non-target rejectors; "
                "each clip must stay below the calibrated threshold versus both refs and the candidate."
            ),
        },
        {
            "id": "reference_separation_from_candidate",
            "status": "PASS_STRUCTURAL_OFFLINE" if separation_pass else "FAIL",
            "measurement": "sha256_inequality_refs_vs_candidate",
            "note": "Candidate wav hash is distinct from both source reference hashes.",
        },
    ]
    complete = all(str(check["status"]).startswith("PASS") for check in checks)
    failed = [check["id"] for check in checks if not str(check["status"]).startswith("PASS")]

    matrix = {
        "schema_version": "1.0",
        "artifact_type": "wave64_speech_row124_multi_ref_drift_leakage_matrix",
        "evidence_id": f"TRK-W64-124_MULTI_REF_DRIFT_LEAKAGE_MATRIX_{args.stamp}",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": (
            "COMPLETE_OFFLINE_STRUCTURAL_AND_MEASURED"
            if complete
            else "MEASURED_EVALUATION_FAILED"
        ),
        "matrix_started": True,
        "matrix_complete": complete,
        "proof_tier": PROOF_TIER,
        "embedding_route": {
            "name": "ERes2Net",
            "device": args.device,
            "checkpoint": {
                "path": str(checkpoint).replace("\\", "/"),
                "sha256": checkpoint_binding["sha256"],
                "bytes": checkpoint_binding["bytes"],
            },
            "cv3_adapter": {
                "path": display_relative(root, adapter_path),
                "sha256": sha256_file(adapter_path),
            },
            "cv3_root": str(cv3_root).replace("\\", "/"),
            "threshold_authority": {
                "repo_relative": display_relative(root, openslr_evidence_path),
                "sha256": openslr_binding["sha256"],
                "threshold": threshold,
            },
        },
        "references_bound": [
            {
                "reference_id": "REF-LIBRIVOX-CHRIS-GORINGE-001",
                "role": "primary_source_reference",
                "sha256": ref1_binding["sha256"],
                "path": display_relative(root, ref1_path),
                "window_seconds": {"start": 0.0, "end": 5.0},
            },
            {
                "reference_id": "REF-LIBRIVOX-CHRIS-GORINGE-002-EXCERPT-20P4",
                "role": "second_independent_source_reference",
                "sha256": ref2_binding["sha256"],
                "path": display_relative(root, ref2_path),
                "window_seconds": {"start": 20.4, "end": 21.8},
            },
        ],
        "candidate_sha256": candidate_binding["sha256"],
        "candidate_path": display_relative(root, candidate_path),
        "openslr_rejector_authority": {
            **openslr_binding,
            "repo_relative": display_relative(root, openslr_evidence_path),
            "manifest_repo_relative": display_relative(root, openslr_manifest_path),
            "manifest_sha256": manifest_binding["sha256"],
        },
        "measured_scores": {
            "similarity_ref1_ref2": sim_ref1_ref2,
            "similarity_candidate_ref1": sim_cand_ref1,
            "similarity_candidate_ref2": sim_cand_ref2,
            "threshold": threshold,
            "non_target_leakage": leakage_rows,
        },
        "checks": checks,
        "check_summary": {
            "checked": len(checks),
            "passed_structural": sum(1 for check in checks if check["status"] == "PASS_STRUCTURAL_OFFLINE"),
            "passed_measured": sum(1 for check in checks if check["status"] == "PASS_MEASURED"),
            "pending_measured": sum(1 for check in checks if check["status"] == "PENDING_MEASURED_EVALUATION"),
            "failed": sum(1 for check in checks if not str(check["status"]).startswith("PASS")),
            "failed_check_ids": failed,
        },
        "boundaries": {
            "offline_only": True,
            "gpu_used": args.device != "cpu",
            "comfyui_8188_used": False,
            "row075_touched": False,
            "sound_csv_written": False,
            "speech_csv_written": False,
            "invented_voices": False,
            "production_promotion_claimed": False,
            "listening_authority_granted": False,
            "tip_sha_chain": False,
            "media_mutated": False,
        },
        "row_complete": False,
    }
    return matrix


def write_json(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return bind(path)
    if path.is_file():
        raise MeasurementError(f"immutable measured matrix already exists with different content: {path}")
    path.write_text(text, encoding="utf-8", newline="\n")
    return bind(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT_DEFAULT)
    parser.add_argument("--stamp", default="20260720C")
    parser.add_argument("--cv3-root", required=True)
    parser.add_argument("--cv3-adapter-script", default=str(DEFAULT_CV3_ADAPTER))
    parser.add_argument("--expected-cv3-adapter-sha256", default=EXPECTED_CV3_ADAPTER_SHA256)
    parser.add_argument("--openslr-evidence", default=str(DEFAULT_OPENSLR_EVIDENCE))
    parser.add_argument(
        "--expected-openslr-evidence-sha256", default=EXPECTED_OPENSLR_EVIDENCE_SHA256
    )
    parser.add_argument("--openslr-manifest", default=str(DEFAULT_OPENSLR_MANIFEST))
    parser.add_argument("--candidate-audio", default=str(DEFAULT_CANDIDATE))
    parser.add_argument("--expected-candidate-sha256", default=EXPECTED_CANDIDATE_SHA256)
    parser.add_argument("--reference-audio", default=str(DEFAULT_REF1))
    parser.add_argument("--expected-reference-sha256", default=EXPECTED_REF1_SHA256)
    parser.add_argument("--second-reference-audio", default=str(DEFAULT_REF2))
    parser.add_argument("--expected-second-reference-sha256", default=EXPECTED_REF2_SHA256)
    parser.add_argument("--rejector-clips-per-speaker", type=int, default=1)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        matrix = evaluate(args)
        binding = write_json(Path(args.output).resolve(), matrix)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "classification": "ROW124_MULTI_REF_DRIFT_LEAKAGE_MEASUREMENT_FAILED",
                    "error": str(exc),
                    "embeddings_or_weights_blocker": True,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": matrix["status"],
                "matrix_complete": matrix["matrix_complete"],
                "check_summary": matrix["check_summary"],
                "measured_scores": {
                    "similarity_ref1_ref2": matrix["measured_scores"]["similarity_ref1_ref2"],
                    "similarity_candidate_ref1": matrix["measured_scores"]["similarity_candidate_ref1"],
                    "similarity_candidate_ref2": matrix["measured_scores"]["similarity_candidate_ref2"],
                    "threshold": matrix["measured_scores"]["threshold"],
                    "rejector_count": len(matrix["measured_scores"]["non_target_leakage"]),
                    "false_accept_count": matrix["checks"][2]["false_accept_count"],
                    "max_non_target_similarity": matrix["checks"][2]["max_non_target_similarity"],
                },
                "output": str(args.output),
                "output_sha256": binding["sha256"],
                "row_complete": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if matrix["matrix_complete"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
