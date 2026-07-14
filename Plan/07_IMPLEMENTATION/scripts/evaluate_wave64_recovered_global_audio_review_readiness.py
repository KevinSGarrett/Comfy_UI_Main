#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import wave
from datetime import datetime
from pathlib import Path
from typing import Any


ROW031_RECOVERED_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/"
    "AUDIO_STRICT_REVIEW_RECOVERED_READINESS_20260714T092355-0500.json"
)
ROW032_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/global_audio_review_not_local_only.json"
)
ROW032_ITEM_REPORT = Path(
    "Plan/Items/Reports/ITEM-W64-032_global_audio_review_not_local_only.json"
)
ROW032_GATE_RULES = Path(
    "Plan/10_REGISTRIES/wave64_global_audio_review_gate_rules.json"
)
ROW032_PRODUCER = Path(
    "Plan/07_IMPLEMENTATION/scripts/produce_wave64_global_audio_review_request.py"
)
ROW032_EVALUATOR = Path(
    "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_global_audio_review.py"
)
EXPECTED_CANDIDATE_CLASSES = {
    "procedural_diagnostic": "diagnostic_full_mix_candidate",
    "returned_runtime_provisional": "provisional_returned_runtime_mix",
}
MISSING_REQUIRED_BINDINGS = (
    "baseline_run_id",
    "candidate_run_id",
    "review_run_id",
    "baseline_row031_strict_report_binding",
    "candidate_row031_strict_report_binding",
    "baseline_wave30_event_manifest_binding",
    "candidate_wave30_event_manifest_binding",
    "baseline_wave30_mix_manifest_binding",
    "candidate_wave30_mix_manifest_binding",
    "baseline_wave30_qa_report_binding",
    "candidate_wave30_qa_report_binding",
    "localized_change_declaration",
)
UNRESOLVED_COMPARISON_SEMANTICS = (
    "same_scene_baseline_candidate_identity",
    "change_kind",
    "audio_change_expected",
    "target_audio_event_ids",
    "allowed_change_windows",
    "capture_mode",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(root: Path, relative: Path) -> Path:
    root = root.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {relative}") from exc
    return path


def relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def file_binding(root: Path, relative: Path) -> dict[str, Any]:
    path = project_path(root, relative)
    if not path.is_file():
        raise ValueError(f"required file missing: {relative}")
    return {
        "path": relative_path(root, path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def probe_wav(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        sample_rate = handle.getframerate()
        return {
            "channels": handle.getnchannels(),
            "sample_width_bytes": handle.getsampwidth(),
            "sample_rate_hz": sample_rate,
            "frame_count": frames,
            "duration_seconds": round(frames / sample_rate, 6),
            "compression_type": handle.getcomptype(),
            "decode_probe_succeeded": True,
        }


def verify_candidate(root: Path, name: str, candidate: dict[str, Any]) -> dict[str, Any]:
    if candidate.get("authority_class") != EXPECTED_CANDIDATE_CLASSES[name]:
        raise ValueError(f"candidate authority class changed: {name}")
    if candidate.get("eligible_as_mix_wav_binding") is not True:
        raise ValueError(f"candidate no longer mix-binding eligible: {name}")
    if candidate.get("eligible_as_prompt_alignment_proof") is not False:
        raise ValueError(f"candidate improperly claims prompt proof: {name}")
    if candidate.get("eligible_as_playback_review_proof") is not False:
        raise ValueError(f"candidate improperly claims playback proof: {name}")
    relative = Path(str(candidate.get("path", "")))
    binding = file_binding(root, relative)
    if binding["sha256"] != candidate.get("sha256"):
        raise ValueError(f"candidate hash mismatch: {name}")
    if binding["bytes"] != candidate.get("bytes"):
        raise ValueError(f"candidate byte-size mismatch: {name}")
    binding.update(probe_wav(project_path(root, relative)))
    binding.update(
        {
            "authority_class": candidate["authority_class"],
            "copied_not_generated": candidate.get("copied_not_generated") is True,
            "eligible_as_row032_mix_wav_binding_candidate": True,
            "eligible_as_row031_strict_report": False,
            "eligible_as_wave30_lineage": False,
            "eligible_as_global_playback_authority": False,
        }
    )
    return binding


def build_evidence(root: Path, timestamp: str) -> dict[str, Any]:
    root = root.resolve()
    row031 = load_json(project_path(root, ROW031_RECOVERED_EVIDENCE))
    row032 = load_json(project_path(root, ROW032_EVIDENCE))
    item_report = load_json(project_path(root, ROW032_ITEM_REPORT))
    rules = load_json(project_path(root, ROW032_GATE_RULES))

    if row031.get("status_decision") != "Blocked_Strict_Audio_Production_Review_Proof_Missing":
        raise ValueError("Row031 recovered readiness status changed; reassess Row032")
    if row031.get("mapping_decision", {}).get("eligible_for_strict_request") is not False:
        raise ValueError("Row031 recovered media became strict-request eligible; reassess Row032")
    if row032.get("status_decision") != "Blocked_Global_Audio_Production_Review_Proof_Missing":
        raise ValueError("Row032 status changed; reassess recovered mapping")
    if item_report.get("status") != "Blocked_Global_Audio_Production_Review_Proof_Missing":
        raise ValueError("Row032 item status changed; reassess recovered mapping")

    production_rules = rules.get("production_rules", {})
    if production_rules.get("approved_production_baselines") != []:
        raise ValueError("Row032 production baseline allowlist changed; reassess mapping")
    if production_rules.get("approved_production_bundles") != []:
        raise ValueError("Row032 production bundle allowlist changed; reassess mapping")
    authority = row032.get("current_authority", {})
    if authority.get("approved_production_baseline_count") != 0:
        raise ValueError("Row032 approved production baseline count changed")
    if authority.get("approved_production_bundle_count") != 0:
        raise ValueError("Row032 approved production bundle count changed")

    source_candidates = row031.get("recovered_mix_candidates")
    if not isinstance(source_candidates, dict) or set(source_candidates) != set(
        EXPECTED_CANDIDATE_CLASSES
    ):
        raise ValueError("Row031 recovered candidate set changed")
    candidates = {
        name: verify_candidate(root, name, source_candidates[name])
        for name in sorted(source_candidates)
    }

    stamp = timestamp.replace("-", "").replace(":", "")
    return {
        "schema_version": "1.0",
        "evidence_id": f"W64-GLOBAL-AUDIO-RECOVERED-READINESS-{stamp}",
        "timestamp": timestamp,
        "tracker_id": "TRK-W64-032",
        "item_id": "ITEM-W64-032",
        "status_decision": "Blocked_Global_Audio_Production_Review_Proof_Missing",
        "source_bindings": {
            "row031_recovered_readiness": file_binding(root, ROW031_RECOVERED_EVIDENCE),
            "row032_current_evidence": file_binding(root, ROW032_EVIDENCE),
            "row032_item_report": file_binding(root, ROW032_ITEM_REPORT),
            "row032_gate_rules": file_binding(root, ROW032_GATE_RULES),
            "row032_request_producer": file_binding(root, ROW032_PRODUCER),
            "row032_evaluator": file_binding(root, ROW032_EVALUATOR),
        },
        "recovered_mix_candidates": candidates,
        "mapping_decision": {
            "reusable_mix_wav_candidate_count": len(candidates),
            "baseline_candidate_pair_selected": False,
            "missing_required_bindings": list(MISSING_REQUIRED_BINDINGS),
            "unresolved_comparison_semantics": list(UNRESOLVED_COMPARISON_SEMANTICS),
            "eligible_for_strict_request": False,
            "strict_producer_invoked": False,
            "strict_evaluator_invoked": False,
            "skip_reason": (
                "Fail closed before request production: the recovered WAVs do not provide "
                "same-scene baseline/candidate identity, strict Row031 reports, Wave30 "
                "event/mix/QA lineage, or a truthful localized-change declaration."
            ),
        },
        "authority_state": {
            "approved_production_baseline_count": 0,
            "approved_production_bundle_count": 0,
            "diagnostic_mix_promoted_to_baseline": False,
            "provisional_mix_promoted_to_candidate": False,
            "legacy_review_promoted_to_full_duration_playback": False,
            "recovered_wav_pair_claimed_as_comparable_change_pair": False,
        },
        "boundaries": {
            "existing_audio_reused": True,
            "generation_executed": False,
            "audio_modified_or_remixed": False,
            "comparison_identity_invented": False,
            "legacy_provisional_result_promoted": False,
            "aws_contacted": False,
            "ec2_started": False,
            "mask_or_wave71_touched": False,
            "jira_mutated": False,
        },
        "result": "blocked_recovered_mixes_not_global_audio_review_request_eligible",
        "next_action": (
            "Retain both WAVs as hash-bound diagnostic lineage. Do not form a strict Row032 "
            "request until one same-scene baseline/candidate pair has exact Wave30 lineage, "
            "strict Row031 reports, localized-change semantics, full-duration playback, and "
            "approved production authorities; proceed to Row033 without promoting Row032."
        ),
    }


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise ValueError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="C:/Comfy_UI_Main")
    parser.add_argument("--output", required=True)
    parser.add_argument("--tracker-output", required=True)
    parser.add_argument(
        "--timestamp", default=datetime.now().astimezone().isoformat(timespec="seconds")
    )
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        output = project_path(root, Path(args.output))
        tracker_output = project_path(root, Path(args.tracker_output))
        if output == tracker_output:
            raise ValueError("output and tracker output must differ")
        evidence = build_evidence(root, args.timestamp)
        atomic_write(output, evidence)
        atomic_write(tracker_output, evidence)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(
        json.dumps(
            {
                "status": evidence["status_decision"],
                "mix_candidates": evidence["mapping_decision"][
                    "reusable_mix_wav_candidate_count"
                ],
                "eligible_for_strict_request": evidence["mapping_decision"][
                    "eligible_for_strict_request"
                ],
                "generation_executed": evidence["boundaries"]["generation_executed"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
