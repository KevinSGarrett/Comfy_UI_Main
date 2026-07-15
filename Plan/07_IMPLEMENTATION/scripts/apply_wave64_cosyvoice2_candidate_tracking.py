#!/usr/bin/env python3
"""Apply rejected CosyVoice2 candidate evidence to affected Wave64 ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_REL = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "W64_COSYVOICE2_ZERO_SHOT_CANDIDATE_EVALUATION_20260715T052332-0500.json"
)
EVIDENCE_SHA256 = "8a595d6ffd232e1fac6d7700d9cf92b5c354b24fe1d1760aef0973416f73accc"
REPORT_PATHS = (
    "Plan/Items/Reports/ITEM-W64-025_audio_pipeline_build.json",
    "Plan/Items/Reports/ITEM-W64-027_audio_voice_dialogue.json",
    "Plan/Items/Reports/ITEM-W64-031_audio_strict_review.json",
)
TRACKER_PATHS = (
    "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv",
    "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
)
ITEM_PATHS = (
    "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
)
ROW_SPECS = {
    "025": {
        "tracker_id": "TRK-W64-025",
        "item_id": "ITEM-W64-025",
        "status": "Blocked_Audio_Production_Runtime_Proof_Missing",
    },
    "027": {
        "tracker_id": "TRK-W64-027",
        "item_id": "ITEM-W64-027",
        "status": "Blocked_Voice_Dialogue_Production_Proof_Missing",
    },
    "031": {
        "tracker_id": "TRK-W64-031",
        "item_id": "ITEM-W64-031",
        "status": "Blocked_Strict_Audio_Production_Review_Proof_Missing",
    },
}
SUPERSEDED_BLOCKER = "Blocked_Voice_Speaker_Reference_Missing"
CURRENT_BLOCKER = "Blocked_Production_Eligible_Voice_Candidate_Missing"
OLD_NOTE = (
    "Wave64 CosyVoice2 zero-shot candidate 2026-07-15: genuine local CUDA inference bound the "
    "public-domain Chris Goringe reference and passed the chain-specific speaker threshold "
    "(0.39928 >= 0.33446) plus DNSMOS floor. The immutable candidate is rejected: 8.8 seconds "
    "versus 3.0, repetitive non-dialogue ASR at WER 4.8, and unsupported focused/controlled style."
)
NOTE = (
    "Wave64 CosyVoice2 zero-shot candidate 2026-07-15: the PyTorch model stack ran on local CUDA "
    "while the ONNX tokenizer/campplus frontend ran on CPU. The public-domain Chris Goringe reference "
    "was bound and the chain-specific speaker score passed (0.39928 >= 0.33446). DNSMOS OVRL 2.88459 "
    "clears only the worst-reference floor at the 50th percentile and is not quality certification. "
    "The immutable candidate is rejected: 8.8 seconds versus 3.0, WER 4.8 repetitive non-dialogue, "
    "unsupported focused emotion, and unmeasured controlled intensity."
)
COVERAGE_TAGS = (
    "cosyvoice2_pytorch_model_stack_cuda_executed",
    "cosyvoice2_onnx_frontend_cpu_executed",
    "cosyvoice2_reference_bound_candidate_rejected",
    "production_voice_candidate_still_blocked",
)
NEXT_ACTION = (
    "Produce one new production-eligible reference-bound dialogue candidate that satisfies the exact "
    "3.0-second content contract and a supported style taxonomy. Preserve all rejected Parler and "
    "CosyVoice2 takes; do not truncate, relabel, or promote the 8.8-second repetitive CosyVoice2 output. "
    "Then obtain independent playback and allowlisted production review."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_unique(current: str, value: str, separator: str) -> str:
    entries = [entry.strip() for entry in (current or "").split(separator) if entry.strip()]
    if value not in entries:
        entries.append(value)
    return separator.join(entries)


def verify_evidence() -> dict:
    qa_path = ROOT / EVIDENCE_REL
    tracker_path = ROOT / "Plan/Tracker/Evidence/Wave64" / qa_path.name
    for path in (qa_path, tracker_path):
        if not path.is_file() or sha256(path) != EVIDENCE_SHA256:
            raise ValueError(f"CosyVoice2 evidence hash mismatch: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        acceptance = payload.get("acceptance", {})
        if acceptance.get("candidate_reference_speaker_score_pass") is not True:
            raise ValueError("CosyVoice2 evidence must preserve the reference-speaker score pass")
        required_false = (
            "candidate_intelligibility_pass",
            "candidate_dialogue_timing_pass",
            "candidate_style_contract_pass",
            "production_review_authority_pass",
            "row_complete",
            "final_voice_certification_pass",
        )
        if any(acceptance.get(key) is not False for key in required_false):
            raise ValueError("CosyVoice2 evidence must remain fail-closed")
        if payload.get("decision", {}).get("candidate_rejected") is not True:
            raise ValueError("CosyVoice2 candidate must remain rejected")
        if acceptance.get("onnx_frontend_cuda_executed") is not False:
            raise ValueError("CosyVoice2 evidence must disclose the CPU ONNX frontend")
        if acceptance.get("candidate_dnsmos_quality_certification_pass") is not None:
            raise ValueError("CosyVoice2 evidence cannot certify quality from the DNSMOS floor")
        if payload.get("row_complete") is not False:
            raise ValueError("CosyVoice2 evidence cannot complete a row")
    return {"qa": str(qa_path), "tracker": str(tracker_path), "sha256": EVIDENCE_SHA256}


def update_report_payload(payload: dict) -> dict:
    row = str(payload.get("item_id", ""))[-3:]
    spec = ROW_SPECS.get(row)
    if not spec or payload.get("tracker_id") != spec["tracker_id"]:
        raise ValueError(f"unexpected Wave64 report identity: {payload.get('item_id')}")
    if payload.get("status") != spec["status"] or payload.get("row_complete") is not False:
        raise ValueError(f"Wave64 report status drift: {payload.get('item_id')}")
    payload["timestamp"] = "2026-07-15T05:40:34-05:00"
    payload.setdefault("implementation", {}).update(
        {
            "cosyvoice2_zero_shot_cuda_runner_ready": True,
            "cosyvoice2_candidate_evaluator_ready": True,
            "cosyvoice2_negative_evidence_packager_ready": True,
        }
    )
    payload.setdefault("validation", {}).update(
        {
            "cosyvoice2_runtime_executed": True,
            "cosyvoice2_candidate_sha256": (
                "13dbaefb9080fe0a6a8d6445f3daf568b6cb2a59df7e324cb3a99427d377ff47"
            ),
            "cosyvoice2_candidate_duration_seconds": 8.8,
            "cosyvoice2_expected_duration_seconds": 3.0,
            "cosyvoice2_candidate_asr_transcript": (
                "Oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, "
                "oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, "
                "oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh, oh,"
            ),
            "cosyvoice2_candidate_normalized_wer": 4.8,
            "cosyvoice2_candidate_speaker_similarity": 0.3992827236652374,
            "cosyvoice2_validated_speaker_threshold": 0.33445611596107483,
            "cosyvoice2_candidate_dnsmos_ovrl": 2.884593350272355,
            "cosyvoice2_candidate_dnsmos_reference_percentile": 0.5,
            "cosyvoice2_candidate_emotion_label": "sad",
            "cosyvoice2_candidate_emotion_score": 0.6004744172096252,
            "cosyvoice2_candidate_rejected": True,
        }
    )
    acceptance_gates = payload.setdefault("acceptance_gates", {})
    acceptance_gates.pop("cosyvoice2_genuine_local_cuda_runtime_executed", None)
    acceptance_gates.pop("cosyvoice2_rejected_candidate_dnsmos_floor_pass", None)
    acceptance_gates.update(
        {
            "cosyvoice2_pytorch_model_stack_cuda_executed": True,
            "cosyvoice2_onnx_frontend_cuda_executed": False,
            "cosyvoice2_independent_reference_speaker_bound": True,
            "cosyvoice2_rejected_candidate_reference_speaker_score_pass": True,
            "cosyvoice2_rejected_candidate_dnsmos_worst_reference_floor_pass": True,
            "cosyvoice2_rejected_candidate_dnsmos_quality_certification_pass": None,
            "cosyvoice2_candidate_intelligibility_pass": False,
            "cosyvoice2_candidate_dialogue_timing_pass": False,
            "cosyvoice2_candidate_style_contract_pass": False,
            "cosyvoice2_candidate_intensity_taxonomy_status": (
                "unmeasured_no_calibrated_intensity_evaluator"
            ),
            "candidate_reference_speaker_identity_verified": False,
            "independent_playback_review_pass": False,
            "production_review_authority_pass": False,
            "final_voice_certification_allowed": False,
        }
    )
    blockers = payload.get("blockers")
    if not isinstance(blockers, list):
        raise ValueError(f"Wave64 report blockers are missing: {payload.get('item_id')}")
    payload["blockers"] = [
        blocker
        for blocker in blockers
        if not (isinstance(blocker, dict) and blocker.get("classification") == SUPERSEDED_BLOCKER)
    ]
    current = [
        blocker
        for blocker in payload["blockers"]
        if isinstance(blocker, dict) and blocker.get("classification") == CURRENT_BLOCKER
    ]
    if len(current) > 1:
        raise ValueError(f"duplicate production-candidate blockers: {payload.get('item_id')}")
    blocker = {
        "classification": CURRENT_BLOCKER,
        "scope": "dialogue_candidate",
        "reason": (
            "The reference-bound CosyVoice2 candidate passes the calibrated speaker score and only the "
            "worst-reference DNSMOS floor, which is not quality certification. It is rejected for "
            "8.8-second timing and WER 4.8 repetitive non-dialogue content; focused emotion is unsupported "
            "and controlled intensity is unmeasured. No production-eligible candidate currently combines "
            "content, timing, speaker, and style proof."
        ),
    }
    if current:
        current[0].update(blocker)
    else:
        payload["blockers"].append(blocker)
    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError(f"Wave64 report evidence is missing: {payload.get('item_id')}")
    existing = next(
        (entry for entry in evidence if isinstance(entry, dict) and entry.get("path") == EVIDENCE_REL),
        None,
    )
    if existing:
        existing["sha256"] = EVIDENCE_SHA256
    else:
        evidence.append({"path": EVIDENCE_REL, "sha256": EVIDENCE_SHA256})
    payload.setdefault("runtime", {})["cosyvoice2_zero_shot_generation_count"] = 1
    payload["runtime"]["cosyvoice2_candidate_evaluation_count"] = 1
    payload["next_action"] = NEXT_ACTION
    return payload


def update_report(path: Path, apply: bool) -> dict:
    payload = update_report_payload(json.loads(path.read_text(encoding="utf-8")))
    if apply:
        temporary = path.with_name(f".{path.name}.cosyvoice2.tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    return {
        "path": str(path),
        "item_id": payload["item_id"],
        "status": payload["status"],
        "row_complete": payload["row_complete"],
        "candidate_rejected": payload["validation"]["cosyvoice2_candidate_rejected"],
    }


def update_csv(path: Path, key: str, evidence_field: str, specs: dict, apply: bool) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    required = {key, "Status", evidence_field, "Coverage_Audit_Status", "Notes"}
    if required - set(fields):
        raise ValueError(f"{path} is missing fields: {sorted(required - set(fields))}")
    by_id = {spec[key]: spec for spec in specs.values()}
    changed = []
    for row in rows:
        row_id = row.get(key)
        if row_id not in by_id:
            continue
        spec = by_id[row_id]
        if row.get("Status") != spec["status"]:
            raise ValueError(f"{path} status drift for {row_id}: {row.get('Status')}")
        if "Status_Decision" in fields and row.get("Status_Decision") != spec["status"]:
            raise ValueError(f"{path} status decision drift for {row_id}")
        row[evidence_field] = append_unique(row.get(evidence_field, ""), EVIDENCE_REL, "; ")
        coverage_entries = [
            entry.strip()
            for entry in row.get("Coverage_Audit_Status", "").split(";")
            if entry.strip() and entry.strip() != "cosyvoice2_local_cuda_runtime_executed"
        ]
        row["Coverage_Audit_Status"] = "; ".join(coverage_entries)
        for tag in COVERAGE_TAGS:
            row["Coverage_Audit_Status"] = append_unique(
                row.get("Coverage_Audit_Status", ""), tag, "; "
            )
        note_entries = [
            entry.strip()
            for entry in row.get("Notes", "").split("|")
            if entry.strip() and entry.strip() != OLD_NOTE
        ]
        row["Notes"] = append_unique(" | ".join(note_entries), NOTE, " | ")
        changed.append({"id": row_id, "status": row["Status"], "evidence_linked": True})
    if len(changed) != len(specs):
        raise ValueError(f"{path} matched {len(changed)} rows, expected {len(specs)}")
    if apply:
        temporary = path.with_name(f".{path.name}.cosyvoice2.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    return changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tracker_specs = {
        key: {**value, "Tracker_ID": value["tracker_id"]} for key, value in ROW_SPECS.items()
    }
    item_specs = {key: {**value, "Item_ID": value["item_id"]} for key, value in ROW_SPECS.items()}
    result = {
        "mode": "apply" if args.apply else "dry_run",
        "evidence": verify_evidence(),
        "reports": [update_report(ROOT / path, args.apply) for path in REPORT_PATHS],
        "tracker": [
            {
                "path": path,
                "rows": update_csv(
                    ROOT / path, "Tracker_ID", "Evidence_Path", tracker_specs, args.apply
                ),
            }
            for path in TRACKER_PATHS
        ],
        "items": [
            {
                "path": path,
                "rows": update_csv(
                    ROOT / path, "Item_ID", "Evidence_Required", item_specs, args.apply
                ),
            }
            for path in ITEM_PATHS
        ],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
