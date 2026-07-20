#!/usr/bin/env python3
"""Offline TRK-W64-124 multi-ref continuity / listening authority proof packager.

Binds the immutable Qwen Base ICL clone, adjacent continuity-matrix diagnostic,
two disjoint public-domain source references (when present), a started or measured
multi-ref drift/leakage matrix, and a prepared human listening request. Classifies
remaining blockers by named class and exact codes. Never claims production COMPLETE,
fabricates listening authority, steals :8188, touches Row075, decodes full-library
PCM, writes sound CSV rows, or invents voice references.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DEFAULT = Path(__file__).resolve().parents[3]
TRACKER_ID = "TRK-W64-124"
ITEM_ID = "ITEM-W64-124"
EXPECTED_ROW124_CLASSIFICATION = "PASS_QWEN3_CLONE_CHAIN_SPECIFIC_IDENTITY_PRODUCTION_AUTHORITY_BLOCKED"
EXPECTED_CANDIDATE_SHA256 = "ff8325a1c2f8613d599af69284f5c4693d996a581230ccbbbb1aeba7affa9815"
EXPECTED_REFERENCE_SHA256 = "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932"
EXPECTED_SECOND_REFERENCE_SHA256 = "ac013d29e84309abd52c49720fe1a9caf2550fd83ce2f8e248be6e4329145f48"
EXPECTED_CONTINUITY_CLASSIFICATION = "PASS_CONTINUITY_PILOT_PRODUCTION_AUTHORITY_BLOCKED"
ROW_STATUS = "Blocked_Production_Voice_Authority_And_Multi_Reference_Validation_Pending"
PROOF_TIER = "OFFLINE_PROOF_BOUNDED"
EVIDENCE_STAMP = "20260720C"
REQUIRED_MATRIX_CHECK_IDS = (
    "same_character_multi_source_identity",
    "cross_line_drift",
    "non_target_speaker_leakage_rejection",
    "reference_separation_from_candidate",
)

DURABLE_CANDIDATE = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "w64_qwen3_tts_base_icl_clone_20260715T195516-0500/"
    "qwen3_tts_base_icl_clone_seed12401.wav"
)
DURABLE_CANDIDATE_EVAL = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "w64_qwen3_tts_base_icl_clone_20260715T195516-0500/"
    "qwen3_tts_base_icl_clone_seed12401.evaluation.json"
)
DURABLE_CANDIDATE_MANIFEST = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "w64_qwen3_tts_base_icl_clone_20260715T195516-0500/"
    "qwen3_tts_base_icl_clone_seed12401.manifest.json"
)
CONTINUITY_EVAL = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "w64_qwen3_tts_continuity_20260715T224100-0500/"
    "wave64_qwen3_tts_continuity_matrix_evaluation.json"
)
FIRST_REFERENCE = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "w64_chatterbox_dialogue_20260715T092901-0500/"
    "librivox_reference_5.0s.wav"
)
SECOND_REFERENCE = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "w64_cv3_speaker_identity_20260715T030600-0500/"
    "librivox_reference_excerpt.wav"
)
CV3_CALIBRATION_MANIFEST = Path(
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "w64_cv3_speaker_identity_20260715T030600-0500/"
    "calibration_manifest.json"
)
VOICE_REF_INTAKE = Path(
    "Plan/Instructions/QA/Evidence/Audio_Asset_Intake/"
    "W64_VOICE_REFERENCE_INTAKE_LIBRIVOX_CHRIS_GORINGE_20260715.json"
)
OPENSLR_VALIDATION_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/"
    "W64_OPENSLR31_SPEAKER_IDENTITY_VALIDATION_20260715T035744-0500.json"
)
ROW124_QA = Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW124.json")
ROW124_TRACKER = Path("Plan/Tracker/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW124.json")
PREPARE_SCRIPT = Path("Plan/07_IMPLEMENTATION/scripts/prepare_wave64_human_audio_review.py")

REF1_WINDOW = (0.0, 5.0)
REF2_WINDOW = (20.4, 21.8)
CLASS_F_BLOCKER_CODE = "GENUINE_SECOND_INDEPENDENT_SOURCE_REFERENCE_ABSENT"
CLASS_A_BLOCKER_CODE = "SECOND_SOURCE_REFERENCE_AUTHORITY_UNBOUND"


class ProofError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind(path: Path, expected_sha256: str | None = None, label: str = "file") -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise ProofError(f"{label} is missing: {path}")
    observed = sha256_file(path)
    if expected_sha256 and observed != expected_sha256.lower():
        raise ProofError(f"{label} SHA-256 mismatch: {observed}")
    return {
        "path": str(path).replace("\\", "/"),
        "repo_relative": None,
        "sha256": observed,
        "bytes": path.stat().st_size,
    }


def display_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ProofError(f"JSON root must be an object: {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any], *, immutable: bool = False) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        if existing == text:
            return bind(path)
        if immutable:
            raise ProofError(f"immutable output already exists with different content: {path}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return bind(path)


def load_prepare_module(root: Path):
    path = root / PREPARE_SCRIPT
    spec = importlib.util.spec_from_file_location("wave64_prepare_human_audio_review_row124", path)
    if not spec or not spec.loader:
        raise ProofError(f"unable to load prepare module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def windows_disjoint(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return a[1] <= b[0] or b[1] <= a[0]


def verify_row124_evidence(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("runtime_classification") != EXPECTED_ROW124_CLASSIFICATION:
        raise ProofError("Row124 runtime classification drift")
    if row.get("row_complete") is not False:
        raise ProofError("Row124 incorrectly claims row_complete")
    gates = row.get("automated_gates") or {}
    if gates.get("chain_specific_speaker_identity_pass") is not True:
        raise ProofError("Row124 chain-specific identity gate missing")
    if gates.get("raw_dialogue_timing_pass") is not False:
        raise ProofError("Row124 timing fail-closed boundary drifted")
    if gates.get("independent_playback_review_pass") is not False:
        raise ProofError("Row124 listening authority incorrectly claimed")
    if gates.get("production_reference_authority_pass") is not False:
        raise ProofError("Row124 production reference authority incorrectly claimed")
    if gates.get("final_voice_certification_pass") is not False:
        raise ProofError("Row124 final voice certification incorrectly claimed")
    if gates.get("row_complete") is not False:
        raise ProofError("Row124 automated_gates.row_complete incorrectly claimed")
    row_meta = row.get("row") or {}
    if row_meta.get("tracker_id") != TRACKER_ID or row_meta.get("item_id") != ITEM_ID:
        raise ProofError("Row124 tracker/item identity drift")
    if row_meta.get("status") != ROW_STATUS:
        raise ProofError("Row124 status drift")
    durable = row.get("durable_artifacts") or {}
    candidate = durable.get("candidate") or {}
    if candidate.get("sha256") != EXPECTED_CANDIDATE_SHA256:
        raise ProofError("Row124 durable candidate hash drift")
    return {
        "chain_specific_identity_pass": True,
        "candidate_asr_pass": gates.get("candidate_asr_pass") is True,
        "technical_audio_pass": gates.get("technical_audio_pass") is True,
        "raw_dialogue_timing_pass": False,
        "independent_playback_review_pass": False,
        "production_reference_authority_pass": False,
        "final_voice_certification_pass": False,
        "row_complete": False,
    }


def verify_continuity_diagnostic(evaluation: dict[str, Any]) -> dict[str, Any]:
    if evaluation.get("classification") != EXPECTED_CONTINUITY_CLASSIFICATION:
        raise ProofError("continuity evaluation classification drift")
    summary = evaluation.get("continuity_summary") or {}
    row_gates = evaluation.get("row_gates") or {}
    row131 = row_gates.get("131") or {}
    independent_refs = int(row131.get("independent_source_reference_count") or 0)
    if independent_refs != 1:
        raise ProofError(
            "adjacent continuity diagnostic must remain one-source historical truth; "
            f"observed {independent_refs}"
        )
    if row131.get("false_acceptance_measured") is not False:
        raise ProofError("continuity diagnostic incorrectly claims false-acceptance measurement")
    if any((row_gates.get(key) or {}).get("row_complete") is not False for key in ("131", "132", "133")):
        raise ProofError("continuity rows incorrectly claim completion")
    if (row_gates.get("132") or {}).get("independent_playback_review_pass") is not False:
        raise ProofError("continuity diagnostic incorrectly claims independent playback")
    line_count = int(summary.get("line_count") or 0)
    scene_count = int(summary.get("scene_count") or 0)
    if line_count < 2 or scene_count < 2:
        raise ProofError("continuity diagnostic does not provide multi-line/multi-scene support")
    return {
        "classification": evaluation.get("classification"),
        "line_count": line_count,
        "scene_count": scene_count,
        "independent_source_reference_count": independent_refs,
        "calibrated_embedding_route_count": int(row131.get("calibrated_embedding_route_count") or 0),
        "false_acceptance_measured": False,
        "multi_line_continuity_diagnostic_bound": True,
        "multi_source_reference_authority": False,
        "independent_playback_review_pass": False,
        "note": (
            "Adjacent Rows131-133 continuity matrix is multi-line/multi-scene under one source "
            "reference. Row124 multi-source binding is evaluated separately via disjoint source "
            "reference intake, not by reinterpreting this adjacent diagnostic."
        ),
    }


def bind_independent_source_references(root: Path) -> dict[str, Any]:
    """Bind two genuine disjoint LibriVox Chris Goringe source windows, or Class F/A stop."""
    first_path = root / FIRST_REFERENCE
    second_path = root / SECOND_REFERENCE
    intake_path = root / VOICE_REF_INTAKE
    cv3_path = root / CV3_CALIBRATION_MANIFEST

    if not first_path.is_file():
        return {
            "independent_source_reference_count": 0,
            "class_f_blocker": CLASS_F_BLOCKER_CODE,
            "class_a_blocker": CLASS_A_BLOCKER_CODE,
            "stop": True,
            "reason": "first genuine source reference wav missing; refusing to invent voices",
            "references": [],
        }

    first_binding = bind(first_path, EXPECTED_REFERENCE_SHA256, "first source reference wav")
    first_binding["repo_relative"] = display_relative(root, first_path)
    intake = load_json(intake_path)
    intake_source = intake.get("source") or {}
    if intake_source.get("sha256") != EXPECTED_REFERENCE_SHA256:
        raise ProofError("voice reference intake hash drift")
    segment = intake.get("segment") or {}
    ref1_window = (
        float(segment.get("start_seconds", REF1_WINDOW[0])),
        float(segment.get("end_seconds", REF1_WINDOW[1])),
    )
    if ref1_window != REF1_WINDOW:
        raise ProofError(f"first reference window drift: {ref1_window}")

    if not second_path.is_file():
        return {
            "independent_source_reference_count": 1,
            "class_f_blocker": CLASS_F_BLOCKER_CODE,
            "class_a_blocker": CLASS_A_BLOCKER_CODE,
            "stop": True,
            "reason": (
                "second genuine independent source reference wav absent under durable pulled-back "
                "artifacts; Class F/A recorded; refusing to invent voices"
            ),
            "references": [
                {
                    "reference_id": "REF-LIBRIVOX-CHRIS-GORINGE-001",
                    "role": "primary_source_reference",
                    "binding": first_binding,
                    "speaker_name": "Chris Goringe",
                    "source_family": "LibriVox_The_Raven",
                    "window_seconds": {"start": ref1_window[0], "end": ref1_window[1]},
                    "production_authorized": False,
                    "invented": False,
                }
            ],
        }

    second_binding = bind(second_path, EXPECTED_SECOND_REFERENCE_SHA256, "second source reference wav")
    second_binding["repo_relative"] = display_relative(root, second_path)
    cv3 = load_json(cv3_path)
    chain = cv3.get("chain_specific_evaluation") or {}
    chain_binding = chain.get("binding") or {}
    ref2_window = (
        float(chain_binding.get("source_excerpt_start_seconds", -1)),
        float(chain_binding.get("source_excerpt_end_seconds", -1)),
    )
    if ref2_window != REF2_WINDOW:
        raise ProofError(f"second reference window drift: {ref2_window}")
    chain_excerpt = chain.get("reference_excerpt") or {}
    if chain_excerpt.get("sha256") != EXPECTED_SECOND_REFERENCE_SHA256:
        raise ProofError("CV3 calibration excerpt hash drift")
    if first_binding["sha256"] == second_binding["sha256"]:
        raise ProofError("second reference is not independent (identical hash)")
    if not windows_disjoint(ref1_window, ref2_window):
        raise ProofError("second reference window overlaps first; not disjoint/independent")

    parent_source = chain_binding.get("source") or {}
    references = [
        {
            "reference_id": "REF-LIBRIVOX-CHRIS-GORINGE-001",
            "role": "primary_source_reference",
            "binding": first_binding,
            "speaker_name": "Chris Goringe",
            "source_family": "LibriVox_The_Raven",
            "window_seconds": {"start": ref1_window[0], "end": ref1_window[1]},
            "transcript": "Once upon a midnight dreary, while I pondered, weak and weary.",
            "rights": "Public Domain Mark 1.0",
            "production_authorized": False,
            "invented": False,
            "provenance": {
                "intake_record": display_relative(root, intake_path),
                "intake_record_id": intake.get("record_id"),
            },
        },
        {
            "reference_id": "REF-LIBRIVOX-CHRIS-GORINGE-002-EXCERPT-20P4",
            "role": "second_independent_source_reference",
            "binding": second_binding,
            "speaker_name": "Chris Goringe",
            "source_family": "LibriVox_The_Raven",
            "window_seconds": {"start": ref2_window[0], "end": ref2_window[1]},
            "rights": "Public Domain Mark 1.0",
            "production_authorized": False,
            "invented": False,
            "disjoint_from_primary": True,
            "provenance": {
                "cv3_calibration_manifest": display_relative(root, cv3_path),
                "parent_source_sha256": parent_source.get("sha256"),
                "parent_source_bytes": parent_source.get("bytes"),
                "claim_scope": chain.get("claim_scope"),
            },
        },
    ]
    return {
        "independent_source_reference_count": 2,
        "class_f_blocker": None,
        "class_a_blocker": None,
        "stop": False,
        "reason": (
            "Bound two hash-distinct, temporally disjoint Chris Goringe LibriVox source windows; "
            "not invented; still non-production evaluation references"
        ),
        "references": references,
        "disjointness": {
            "method": "temporal_window_non_overlap_plus_distinct_sha256",
            "primary_window_seconds": {"start": ref1_window[0], "end": ref1_window[1]},
            "second_window_seconds": {"start": ref2_window[0], "end": ref2_window[1]},
            "windows_disjoint": True,
            "hashes_distinct": True,
        },
    }


def build_drift_leakage_matrix_start(
    root: Path,
    *,
    references: list[dict[str, Any]],
    candidate_sha256: str,
    stamp: str,
) -> dict[str, Any]:
    openslr_path = root / OPENSLR_VALIDATION_EVIDENCE
    openslr_binding = None
    if openslr_path.is_file():
        openslr_binding = bind(openslr_path, label="OpenSLR31 validation evidence")
        openslr_binding["repo_relative"] = display_relative(root, openslr_path)

    ref_hashes = [item["binding"]["sha256"] for item in references]
    separation_pass = all(h != candidate_sha256 for h in ref_hashes) and len(set(ref_hashes)) == len(ref_hashes)
    same_speaker = (
        len(references) >= 2
        and all(item.get("speaker_name") == "Chris Goringe" for item in references)
        and all(item.get("source_family") == "LibriVox_The_Raven" for item in references)
        and all(item.get("invented") is False for item in references)
    )
    checks = [
        {
            "id": "same_character_multi_source_identity",
            "status": "PASS_STRUCTURAL_OFFLINE" if same_speaker else "FAIL",
            "measurement": "structural_speaker_and_source_family_concordance",
            "note": (
                "Both bound references attribute Chris Goringe / LibriVox The Raven. "
                "Embedding-level same-character confirmation remains for measured evaluation."
            ),
        },
        {
            "id": "cross_line_drift",
            "status": "PENDING_MEASURED_EVALUATION",
            "measurement": "calibrated_speaker_embedding_cross_line_drift",
            "note": "Matrix started; measured cross-line drift not executed in this offline slice.",
        },
        {
            "id": "non_target_speaker_leakage_rejection",
            "status": "PENDING_MEASURED_EVALUATION",
            "measurement": "calibrated_non_target_rejector_against_openslr31_authority",
            "planned_rejector_authority": (
                openslr_binding["repo_relative"] if openslr_binding else None
            ),
            "note": (
                "OpenSLR31 validation evidence bound as planned rejector authority only. "
                "No non-target acceptance/rejection scores claimed in this offline start."
            ),
        },
        {
            "id": "reference_separation_from_candidate",
            "status": "PASS_STRUCTURAL_OFFLINE" if separation_pass else "FAIL",
            "measurement": "sha256_inequality_refs_vs_candidate",
            "note": "Candidate wav hash is distinct from both source reference hashes.",
        },
    ]
    complete = all(check["status"].startswith("PASS") for check in checks)
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_speech_row124_multi_ref_drift_leakage_matrix",
        "evidence_id": f"TRK-W64-124_MULTI_REF_DRIFT_LEAKAGE_MATRIX_{stamp}",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "status": (
            "COMPLETE_OFFLINE_STRUCTURAL_AND_MEASURED"
            if complete
            else "STARTED_OFFLINE_STRUCTURAL_PENDING_MEASURED_EVALUATION"
        ),
        "matrix_started": True,
        "matrix_complete": complete,
        "proof_tier": PROOF_TIER,
        "references_bound": [
            {
                "reference_id": item["reference_id"],
                "sha256": item["binding"]["sha256"],
                "window_seconds": item["window_seconds"],
                "role": item["role"],
            }
            for item in references
        ],
        "candidate_sha256": candidate_sha256,
        "openslr_rejector_authority": openslr_binding,
        "checks": checks,
        "check_summary": {
            "checked": len(checks),
            "passed_structural": sum(1 for check in checks if check["status"] == "PASS_STRUCTURAL_OFFLINE"),
            "pending_measured": sum(1 for check in checks if check["status"] == "PENDING_MEASURED_EVALUATION"),
            "failed": sum(1 for check in checks if check["status"] == "FAIL"),
        },
        "boundaries": {
            "offline_only": True,
            "gpu_used": False,
            "comfyui_8188_used": False,
            "row075_touched": False,
            "sound_csv_written": False,
            "speech_csv_written": False,
            "invented_voices": False,
            "production_promotion_claimed": False,
            "listening_authority_granted": False,
            "tip_sha_chain": False,
        },
        "row_complete": False,
    }


def load_measured_matrix(path: Path, *, stamp: str, candidate_sha256: str) -> dict[str, Any]:
    matrix = load_json(path)
    if matrix.get("artifact_type") != "wave64_speech_row124_multi_ref_drift_leakage_matrix":
        raise ProofError("measured matrix artifact_type mismatch")
    if matrix.get("tracker_id") != TRACKER_ID or matrix.get("item_id") != ITEM_ID:
        raise ProofError("measured matrix tracker/item identity drift")
    if matrix.get("evidence_id") != f"TRK-W64-124_MULTI_REF_DRIFT_LEAKAGE_MATRIX_{stamp}":
        raise ProofError("measured matrix evidence_id/stamp mismatch")
    if matrix.get("candidate_sha256") != candidate_sha256:
        raise ProofError("measured matrix candidate hash drift")
    if matrix.get("proof_tier") != PROOF_TIER:
        raise ProofError("measured matrix proof_tier drift")
    if matrix.get("row_complete") is not False:
        raise ProofError("measured matrix incorrectly claims row_complete")
    boundaries = matrix.get("boundaries") or {}
    if boundaries.get("comfyui_8188_used") is not False:
        raise ProofError("measured matrix used :8188")
    if boundaries.get("sound_csv_written") is not False:
        raise ProofError("measured matrix wrote sound CSV")
    if boundaries.get("row075_touched") is not False:
        raise ProofError("measured matrix touched Row075")
    if boundaries.get("listening_authority_granted") is not False:
        raise ProofError("measured matrix incorrectly grants listening authority")
    if boundaries.get("production_promotion_claimed") is not False:
        raise ProofError("measured matrix incorrectly claims production promotion")
    checks = matrix.get("checks") or []
    check_ids = [item.get("id") for item in checks]
    if check_ids != list(REQUIRED_MATRIX_CHECK_IDS):
        raise ProofError(f"measured matrix check set drift: {check_ids}")
    if matrix.get("matrix_complete") is not True:
        raise ProofError("measured matrix is not complete")
    if not all(str(item.get("status", "")).startswith("PASS") for item in checks):
        raise ProofError("measured matrix contains non-passing checks")
    if int((matrix.get("check_summary") or {}).get("pending_measured") or 0) != 0:
        raise ProofError("measured matrix still reports pending measured checks")
    return matrix


def classify_blockers(
    *,
    independent_source_reference_count: int,
    listening_request_prepared: bool,
    raw_dialogue_timing_pass: bool,
    production_reference_authority_pass: bool,
    matrix_complete: bool,
    class_f_blocker: str | None = None,
    class_a_blocker: str | None = None,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    multi_ref_codes: list[str] = []
    multi_ref_cleared: list[str] = []
    if independent_source_reference_count < 2:
        multi_ref_codes.append("INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO")
        if class_f_blocker:
            multi_ref_codes.append(class_f_blocker)
        if class_a_blocker:
            multi_ref_codes.append(class_a_blocker)
    else:
        multi_ref_cleared.append("INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO")
    if not matrix_complete:
        multi_ref_codes.append("MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE")
    elif independent_source_reference_count >= 2:
        multi_ref_cleared.append("MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE")
    if independent_source_reference_count < 2:
        summary = (
            "Only one independent source reference is bound; multi-reference drift/leakage "
            "validation remains incomplete despite multi-line continuity diagnostics."
        )
        if class_f_blocker or class_a_blocker:
            summary = (
                "Second genuine independent source reference absent (Class F/A). "
                "Do not invent voices. Multi-reference drift/leakage matrix cannot advance."
            )
    elif not matrix_complete:
        summary = (
            "Two disjoint independent source references are bound; multi-reference drift/leakage "
            "matrix is started with offline structural checks but measured evaluation remains incomplete."
        )
    else:
        summary = (
            "Two disjoint independent source references are bound and the multi-reference "
            "drift/leakage matrix completed at OFFLINE_PROOF_BOUNDED with measured ERes2Net "
            "scores. Production voice authority and listening authority remain separately blocked."
        )
    blockers.append(
        {
            "class": "MULTI_REFERENCE_CONTINUITY",
            "codes": multi_ref_codes,
            "cleared_by_this_packet": multi_ref_cleared,
            "summary": summary,
        }
    )
    blockers.append(
        {
            "class": "PRODUCTION_VOICE_AUTHORITY",
            "codes": ["PRODUCTION_CHARACTER_REFERENCE_AUTHORITY_ABSENT"],
            "cleared_by_this_packet": [],
            "summary": (
                "The public-domain evaluation references are not a locked production character "
                "identity authority."
            ),
            "production_reference_authority_pass": production_reference_authority_pass,
        }
    )
    listening_codes = ["INDEPENDENT_PLAYBACK_REVIEW_ABSENT", "FINAL_VOICE_CERTIFICATION_PENDING"]
    cleared = []
    if listening_request_prepared:
        cleared.append("LISTENING_REVIEW_REQUEST_UNPREPARED")
    else:
        listening_codes.insert(0, "LISTENING_REVIEW_REQUEST_UNPREPARED")
    blockers.append(
        {
            "class": "LISTENING_AUTHORITY",
            "codes": listening_codes,
            "cleared_by_this_packet": cleared,
            "summary": (
                "Independent human playback review and final voice certification remain pending. "
                "Preparing a hash-bound listening request does not grant listening authority."
            ),
        }
    )
    timing_codes = [] if raw_dialogue_timing_pass else ["RAW_DIALOGUE_TIMING_OUT_OF_TOLERANCE"]
    blockers.append(
        {
            "class": "DIALOGUE_TIMING",
            "codes": timing_codes,
            "cleared_by_this_packet": [],
            "summary": (
                "Raw dialogue timing is outside the 3.000±0.080s contract and keeps production "
                "listening authority blocked."
                if timing_codes
                else "Raw dialogue timing gate currently passes."
            ),
        }
    )
    return blockers


def flatten_blocker_codes(blockers: list[dict[str, Any]]) -> list[str]:
    codes: list[str] = []
    for blocker in blockers:
        for code in blocker.get("codes") or []:
            if code not in codes:
                codes.append(code)
    return codes


def build_listening_request(
    root: Path,
    candidate: Path,
    automated_evidence: list[Path],
    *,
    independent_source_reference_count: int,
) -> dict[str, Any]:
    prepare = load_prepare_module(root)
    args = argparse.Namespace(
        artifact=str(candidate),
        media_type="audio",
        review_id="W64-ROW124-QWEN3-BASE-ICL-CLONE-LISTENING-001",
        expected_transcript="We hold the frame steady and move on the beat.",
        character_id="UNASSIGNED_REFERENCE_POOL",
        voice_profile_id="voice_unassigned_public_domain_eval_ref_v1",
        emotion_class=None,
        delivery_style="focused",
        intensity="controlled",
        pace_wpm=187.498,
        duration_target_seconds=3.0,
        sync_required=False,
        engine_identity_hidden_initial_pass=True,
        automated_evidence=[str(path) for path in automated_evidence],
    )
    request = prepare.build_request(args)
    ineligible = [
        "RAW_DIALOGUE_TIMING_OUT_OF_TOLERANCE",
        "PRODUCTION_CHARACTER_REFERENCE_AUTHORITY_ABSENT",
    ]
    if independent_source_reference_count < 2:
        ineligible.append("INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO")
    else:
        ineligible.append("MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE")
    request["authority_boundary"] = {
        "listening_request_prepared": True,
        "independent_playback_review_pass": False,
        "production_listening_authority": False,
        "fabricated_human_decision_prohibited": True,
        "reason_production_ineligible": ineligible,
    }
    return request


def build_class_fa_stop_packet(
    root: Path,
    *,
    stamp: str,
    source_bind: dict[str, Any],
    gate_snapshot: dict[str, Any],
    continuity: dict[str, Any],
) -> dict[str, Any]:
    blockers = classify_blockers(
        independent_source_reference_count=source_bind["independent_source_reference_count"],
        listening_request_prepared=True,
        raw_dialogue_timing_pass=gate_snapshot["raw_dialogue_timing_pass"],
        production_reference_authority_pass=False,
        matrix_complete=False,
        class_f_blocker=source_bind.get("class_f_blocker"),
        class_a_blocker=source_bind.get("class_a_blocker"),
    )
    return {
        "schema_version": "1.0",
        "artifact_type": "wave64_speech_row124_multi_ref_listening_current_delta",
        "evidence_id": f"TRK-W64-124_MULTI_REF_LISTENING_CURRENT_DELTA_{stamp}",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "proof_tier": PROOF_TIER,
        "highest_proof_tier_achieved": PROOF_TIER,
        "status": "BLOCKED_CLASS_F_A_SECOND_GENUINE_REFERENCE_ABSENT",
        "decision": {
            "status": "blocked",
            "row_complete": False,
            "product_completion": False,
            "production_promotion_claimed": False,
            "listening_authority_granted": False,
            "multi_source_reference_authority": False,
            "safe_next_action": (
                "Class F/A stop: acquire a genuine second disjoint source reference for the same "
                "speaker/character without inventing voices, then restart multi-ref drift/leakage "
                "matrix binding. Do not steal :8188, touch Row075, write sound CSV, or claim COMPLETE."
            ),
        },
        "class_f_a_stop": {
            "stopped": True,
            "class_f_blocker": source_bind.get("class_f_blocker"),
            "class_a_blocker": source_bind.get("class_a_blocker"),
            "reason": source_bind.get("reason"),
            "invented_voices": False,
        },
        "independent_source_references": source_bind,
        "continuity_diagnostic": continuity,
        "gate_snapshot": gate_snapshot,
        "blocker_classes": blockers,
        "blocker_codes": flatten_blocker_codes(blockers),
        "row_complete": False,
        "boundaries": {
            "offline_only": True,
            "gpu_used": False,
            "comfyui_8188_used": False,
            "row075_touched": False,
            "full_library_pcm_decoded": False,
            "sound_csv_written": False,
            "speech_csv_written": False,
            "media_mutated": False,
            "subjective_review_fabricated": False,
            "production_promotion_claimed": False,
            "content_based_suppression": False,
            "aws_or_ec2_used": False,
            "tip_sha_chain": False,
            "invented_voices": False,
        },
    }


def build_proof_packet(
    root: Path,
    *,
    stamp: str = EVIDENCE_STAMP,
    write_outputs: bool = True,
    measured_matrix_path: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    row124_path = root / ROW124_QA
    continuity_path = root / CONTINUITY_EVAL
    candidate_path = root / DURABLE_CANDIDATE
    candidate_eval_path = root / DURABLE_CANDIDATE_EVAL
    candidate_manifest_path = root / DURABLE_CANDIDATE_MANIFEST

    row124_binding = bind(row124_path, label="Row124 evidence")
    row124_binding["repo_relative"] = display_relative(root, row124_path)
    row124 = load_json(row124_path)
    gate_snapshot = verify_row124_evidence(row124)

    candidate_binding = bind(candidate_path, EXPECTED_CANDIDATE_SHA256, "durable candidate wav")
    candidate_binding["repo_relative"] = display_relative(root, candidate_path)
    candidate_eval_binding = bind(candidate_eval_path, label="durable candidate evaluation")
    candidate_eval_binding["repo_relative"] = display_relative(root, candidate_eval_path)
    candidate_manifest_binding = bind(candidate_manifest_path, label="durable candidate manifest")
    candidate_manifest_binding["repo_relative"] = display_relative(root, candidate_manifest_path)

    continuity_binding = bind(continuity_path, label="continuity evaluation")
    continuity_binding["repo_relative"] = display_relative(root, continuity_path)
    continuity = verify_continuity_diagnostic(load_json(continuity_path))

    durable_manifest = load_json(candidate_manifest_path)
    reference_meta = durable_manifest.get("reference") or {}
    if reference_meta.get("sha256") != EXPECTED_REFERENCE_SHA256:
        raise ProofError("clone reference hash drift")
    if reference_meta.get("production_authorized") is not False:
        raise ProofError("clone reference incorrectly claims production authorization")

    source_bind = bind_independent_source_references(root)
    if source_bind.get("stop"):
        packet = build_class_fa_stop_packet(
            root,
            stamp=stamp,
            source_bind=source_bind,
            gate_snapshot=gate_snapshot,
            continuity=continuity,
        )
        if write_outputs:
            delta_rel = (
                f"Plan/Instructions/QA/Evidence/Wave64/"
                f"TRK-W64-124_MULTI_REF_LISTENING_CURRENT_DELTA_{stamp}.json"
            )
            tracker_delta_rel = (
                f"Plan/Tracker/Evidence/Audio_Asset_Intake/"
                f"TRK-W64-124_MULTI_REF_LISTENING_CURRENT_DELTA_{stamp}.json"
            )
            delta_binding = write_json_atomic(root / delta_rel, packet, immutable=True)
            write_json_atomic(root / tracker_delta_rel, packet, immutable=True)
            packet["outputs"] = {
                "current_delta": delta_rel,
                "current_delta_sha256": delta_binding["sha256"],
                "tracker_current_delta": tracker_delta_rel,
            }
        return packet

    if measured_matrix_path is not None:
        matrix = load_measured_matrix(
            Path(measured_matrix_path).resolve(),
            stamp=stamp,
            candidate_sha256=EXPECTED_CANDIDATE_SHA256,
        )
    else:
        matrix = build_drift_leakage_matrix_start(
            root,
            references=source_bind["references"],
            candidate_sha256=EXPECTED_CANDIDATE_SHA256,
            stamp=stamp,
        )
    matrix_complete = bool(matrix.get("matrix_complete"))
    independent_count = int(source_bind["independent_source_reference_count"])

    listening_request = build_listening_request(
        root,
        candidate_path,
        [candidate_eval_path, row124_path, continuity_path],
        independent_source_reference_count=independent_count,
    )
    listening_rel = (
        f"Plan/Instructions/QA/Evidence/Audio_Asset_Intake/"
        f"TRK-W64-124_LISTENING_REVIEW_REQUEST_{stamp}.json"
    )
    delta_rel = f"Plan/Instructions/QA/Evidence/Wave64/TRK-W64-124_MULTI_REF_LISTENING_CURRENT_DELTA_{stamp}.json"
    tracker_delta_rel = (
        f"Plan/Tracker/Evidence/Audio_Asset_Intake/"
        f"TRK-W64-124_MULTI_REF_LISTENING_CURRENT_DELTA_{stamp}.json"
    )
    matrix_rel = (
        f"Plan/Instructions/QA/Evidence/Audio_Asset_Intake/"
        f"TRK-W64-124_MULTI_REF_DRIFT_LEAKAGE_MATRIX_{stamp}.json"
    )
    tracker_matrix_rel = (
        f"Plan/Tracker/Evidence/Audio_Asset_Intake/"
        f"TRK-W64-124_MULTI_REF_DRIFT_LEAKAGE_MATRIX_{stamp}.json"
    )

    blockers = classify_blockers(
        independent_source_reference_count=independent_count,
        listening_request_prepared=True,
        raw_dialogue_timing_pass=gate_snapshot["raw_dialogue_timing_pass"],
        production_reference_authority_pass=gate_snapshot["production_reference_authority_pass"],
        matrix_complete=matrix_complete,
    )
    blocker_codes = flatten_blocker_codes(blockers)
    multi_ref_cleared = next(
        item["cleared_by_this_packet"] for item in blockers if item["class"] == "MULTI_REFERENCE_CONTINUITY"
    )

    checks = [
        {"name": "R124-P001_row124_identity_asr_technical_bound", "result": "pass"},
        {"name": "R124-P002_continuity_multi_line_diagnostic_bound", "result": "pass"},
        {
            "name": "R124-P003_independent_source_reference_count_ge_2",
            "result": "pass" if independent_count >= 2 else "fail",
            **(
                {}
                if independent_count >= 2
                else {"blocker_code": "INDEPENDENT_SOURCE_REFERENCE_COUNT_BELOW_TWO"}
            ),
        },
        {
            "name": "R124-P004_multi_ref_drift_leakage_matrix_complete",
            "result": "pass" if matrix_complete else "fail",
            **(
                {}
                if matrix_complete
                else {"blocker_code": "MULTI_REF_DRIFT_LEAKAGE_MATRIX_INCOMPLETE"}
            ),
        },
        {
            "name": "R124-P005_production_character_reference_authority",
            "result": "fail",
            "blocker_code": "PRODUCTION_CHARACTER_REFERENCE_AUTHORITY_ABSENT",
        },
        {"name": "R124-P006_listening_review_request_prepared", "result": "pass"},
        {
            "name": "R124-P007_independent_playback_review_pass",
            "result": "fail",
            "blocker_code": "INDEPENDENT_PLAYBACK_REVIEW_ABSENT",
        },
        {
            "name": "R124-P008_raw_dialogue_timing_pass",
            "result": "fail",
            "blocker_code": "RAW_DIALOGUE_TIMING_OUT_OF_TOLERANCE",
        },
        {"name": "R124-P009_no_product_complete_claim", "result": "pass"},
        {"name": "R124-P010_no_sound_csv_write", "result": "pass"},
        {"name": "R124-P011_row075_left_alone", "result": "pass"},
        {"name": "R124-P012_no_comfy_8188_runtime", "result": "pass"},
        {
            "name": "R124-P013_second_source_reference_bound_disjoint",
            "result": "pass" if independent_count >= 2 else "fail",
        },
        {
            "name": "R124-P014_multi_ref_drift_leakage_matrix_started",
            "result": "pass" if matrix.get("matrix_started") else "fail",
        },
    ]
    check_summary = {
        "checked": len(checks),
        "passed": sum(1 for check in checks if check["result"] == "pass"),
        "failed": sum(1 for check in checks if check["result"] == "fail"),
    }

    if matrix_complete:
        packet_status = "BLOCKED_PRODUCTION_VOICE_AND_LISTENING_AUTHORITY_PENDING"
        safe_next_action = (
            "Retain OFFLINE_PROOF_BOUNDED packet. Measured multi-ref drift/leakage matrix is "
            "complete against the two bound disjoint LibriVox references plus OpenSLR31 "
            "rejectors. Clear raw timing or document an approved timing waiver, then execute "
            "independent human listening against the prepared request. Do not steal :8188, "
            "touch Row075, decode full-library PCM, write sound CSV, invent voices, or claim "
            "COMPLETE / PRODUCTION_VOICE_AUTHORITY / LISTENING_AUTHORITY."
        )
    else:
        packet_status = "BLOCKED_MULTI_REF_MATRIX_INCOMPLETE_AND_LISTENING_AUTHORITY_PENDING"
        safe_next_action = (
            "Retain OFFLINE_PROOF_BOUNDED packet. Complete measured multi-ref drift/leakage "
            "matrix evaluation against the two bound disjoint LibriVox references, clear raw "
            "timing or document an approved timing waiver, then execute independent human "
            "listening against the prepared request. Do not steal :8188, touch Row075, decode "
            "full-library PCM, write sound CSV, invent voices, or claim COMPLETE / "
            "PRODUCTION_VOICE_AUTHORITY / LISTENING_AUTHORITY."
        )

    created_at = datetime.now(timezone.utc).isoformat()
    packet = {
        "schema_version": "1.0",
        "artifact_type": "wave64_speech_row124_multi_ref_listening_current_delta",
        "evidence_id": f"TRK-W64-124_MULTI_REF_LISTENING_CURRENT_DELTA_{stamp}",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "created_at": created_at,
        "proof_tier": PROOF_TIER,
        "highest_proof_tier_achieved": PROOF_TIER,
        "status": packet_status,
        "decision": {
            "status": "blocked",
            "row_complete": False,
            "product_completion": False,
            "production_promotion_claimed": False,
            "listening_authority_granted": False,
            "multi_source_reference_authority": False,
            "safe_next_action": safe_next_action,
        },
        "bindings": {
            "row124_evidence": row124_binding,
            "candidate_wav": candidate_binding,
            "candidate_evaluation": candidate_eval_binding,
            "candidate_manifest": candidate_manifest_binding,
            "continuity_evaluation": continuity_binding,
            "reference_sha256": EXPECTED_REFERENCE_SHA256,
            "second_reference_sha256": EXPECTED_SECOND_REFERENCE_SHA256,
            "reference_path_resolved": FIRST_REFERENCE.as_posix(),
            "second_reference_path_resolved": SECOND_REFERENCE.as_posix(),
            "listening_review_request": listening_rel,
            "multi_ref_drift_leakage_matrix": matrix_rel,
            "packager_script": display_relative(
                root,
                root
                / "Plan/07_IMPLEMENTATION/scripts/package_wave64_speech_row124_multi_ref_listening_proof.py",
            ),
        },
        "independent_source_references": source_bind,
        "continuity_diagnostic": continuity,
        "gate_snapshot": gate_snapshot,
        "multi_ref_continuity_contract": {
            "required_independent_source_references": 2,
            "observed_independent_source_references": independent_count,
            "required_checks": list(REQUIRED_MATRIX_CHECK_IDS),
            "adjacent_multi_line_matrix_bound": True,
            "multi_source_authority_satisfied": False,
            "drift_leakage_matrix_started": True,
            "drift_leakage_matrix_complete": matrix_complete,
        },
        "multi_ref_drift_leakage_matrix": {
            "evidence_id": matrix["evidence_id"],
            "status": matrix["status"],
            "matrix_started": True,
            "matrix_complete": matrix_complete,
            "check_summary": matrix["check_summary"],
        },
        "listening_authority": {
            "review_request_prepared": True,
            "review_id": listening_request["review_id"],
            "independent_playback_review_pass": False,
            "production_listening_authority": False,
            "human_decision_fabricated": False,
        },
        "blocker_classes": blockers,
        "blocker_codes": blocker_codes,
        "checks": checks,
        "check_summary": check_summary,
        "boundaries": {
            "offline_only": True,
            "gpu_used": False,
            "comfyui_8188_used": False,
            "row075_touched": False,
            "full_library_pcm_decoded": False,
            "sound_csv_written": False,
            "speech_csv_written": False,
            "media_mutated": False,
            "subjective_review_fabricated": False,
            "production_promotion_claimed": False,
            "content_based_suppression": False,
            "aws_or_ec2_used": False,
            "tip_sha_chain": False,
            "invented_voices": False,
        },
        "row_complete": False,
    }

    if not write_outputs:
        packet["listening_review_request_payload"] = listening_request
        packet["multi_ref_drift_leakage_matrix_payload"] = matrix
        return packet

    listening_binding = write_json_atomic(root / listening_rel, listening_request, immutable=True)
    listening_binding["repo_relative"] = listening_rel
    packet["bindings"]["listening_review_request_binding"] = listening_binding

    matrix_binding = write_json_atomic(root / matrix_rel, matrix, immutable=True)
    matrix_binding["repo_relative"] = matrix_rel
    write_json_atomic(root / tracker_matrix_rel, matrix, immutable=True)
    packet["bindings"]["multi_ref_drift_leakage_matrix_binding"] = matrix_binding

    delta_binding = write_json_atomic(root / delta_rel, packet, immutable=True)
    delta_binding["repo_relative"] = delta_rel
    write_json_atomic(root / tracker_delta_rel, packet, immutable=True)

    updated_row = dict(row124)
    cleared_partial = ["LISTENING_REVIEW_REQUEST_UNPREPARED"]
    cleared_partial.extend(multi_ref_cleared)
    updated_row["multi_ref_listening_proof"] = {
        "proof_tier": PROOF_TIER,
        "status": packet["status"],
        "evidence_id": packet["evidence_id"],
        "current_delta": delta_rel,
        "listening_review_request": listening_rel,
        "multi_ref_drift_leakage_matrix": matrix_rel,
        "independent_source_reference_count": independent_count,
        "blocker_classes": blockers,
        "blocker_codes": blocker_codes,
        "cleared_partial": cleared_partial,
        "continuity_diagnostic_bound": True,
        "second_source_reference_bound": True,
        "drift_leakage_matrix_started": True,
        "drift_leakage_matrix_complete": matrix_complete,
        "row_complete": False,
        "product_completion": False,
        "production_voice_authority_claimed": False,
        "listening_authority_claimed": False,
    }
    row_meta = dict(updated_row.get("row") or {})
    row_meta["status"] = ROW_STATUS
    row_meta["pass_like"] = False
    row_meta["blockers"] = [
        f"{blocker['class']}: {', '.join(blocker['codes'])}" for blocker in blockers if blocker["codes"]
    ]
    updated_row["row"] = row_meta
    updated_row["row_complete"] = False
    updated_row["automated_gates"] = {
        **(updated_row.get("automated_gates") or {}),
        "independent_playback_review_pass": False,
        "production_reference_authority_pass": False,
        "final_voice_certification_pass": False,
        "row_complete": False,
    }
    write_json_atomic(root / ROW124_QA, updated_row, immutable=False)
    write_json_atomic(root / ROW124_TRACKER, updated_row, immutable=False)

    packet["outputs"] = {
        "current_delta": delta_rel,
        "current_delta_sha256": delta_binding["sha256"],
        "tracker_current_delta": tracker_delta_rel,
        "listening_review_request": listening_rel,
        "listening_review_request_sha256": listening_binding["sha256"],
        "multi_ref_drift_leakage_matrix": matrix_rel,
        "multi_ref_drift_leakage_matrix_sha256": matrix_binding["sha256"],
        "tracker_multi_ref_drift_leakage_matrix": tracker_matrix_rel,
        "row124_qa": ROW124_QA.as_posix(),
        "row124_tracker": ROW124_TRACKER.as_posix(),
    }
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT_DEFAULT)
    parser.add_argument("--stamp", default=EVIDENCE_STAMP)
    parser.add_argument(
        "--measured-matrix",
        type=Path,
        default=None,
        help="Optional hash-bound measured drift/leakage matrix JSON to adopt",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        packet = build_proof_packet(
            args.project_root.resolve(),
            stamp=args.stamp,
            write_outputs=not args.dry_run,
            measured_matrix_path=args.measured_matrix,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "classification": "ROW124_MULTI_REF_LISTENING_PROOF_FAILED",
                    "error": str(exc),
                    "yield_if_gpu_required": True,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": packet["status"],
                "proof_tier": packet["proof_tier"],
                "blocker_codes": packet["blocker_codes"],
                "blocker_classes": [
                    {"class": item["class"], "codes": item["codes"], "cleared": item.get("cleared_by_this_packet")}
                    for item in packet["blocker_classes"]
                ],
                "independent_source_reference_count": (
                    (packet.get("independent_source_references") or {}).get(
                        "independent_source_reference_count"
                    )
                ),
                "outputs": packet.get("outputs"),
                "row_complete": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
