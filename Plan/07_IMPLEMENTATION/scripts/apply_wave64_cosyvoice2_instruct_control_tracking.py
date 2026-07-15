#!/usr/bin/env python3
"""Track the terminal CosyVoice2 instruct-control rejection."""

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
    "W64_COSYVOICE2_INSTRUCT_CONTROL_REJECTION_20260715T074822-0500.json"
)
EVIDENCE_SHA256 = "e736b31cc47108d050a0126e6d29af72680df1561a6789f0f7748a64296e2c2a"
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
    "025": ("TRK-W64-025", "ITEM-W64-025", "Blocked_Audio_Production_Runtime_Proof_Missing"),
    "027": ("TRK-W64-027", "ITEM-W64-027", "Blocked_Voice_Dialogue_Production_Proof_Missing"),
    "031": ("TRK-W64-031", "ITEM-W64-031", "Blocked_Strict_Audio_Production_Review_Proof_Missing"),
}
BLOCKER = "Blocked_Production_Eligible_Voice_Candidate_Missing"
NOTE = (
    "Wave64 CosyVoice2 instruct-control take 2026-07-15: one hash-bound model-native instruct2 "
    "candidate ran at speed 1.2 with no truncation or time stretching. It is rejected at 7.32 "
    "seconds and WER 1.0 after producing unrelated speech; speaker score 0.34052 narrowly clears "
    "0.33446, DNSMOS OVRL is 2.86294, and emotion is happy rather than the unsupported focused target. "
    "The one-candidate stop rule forbids retrying this same control path."
)
COVERAGE_TAGS = (
    "cosyvoice2_instruct_control_runtime_executed",
    "cosyvoice2_instruct_control_content_rejected",
    "cosyvoice2_instruct_control_timing_rejected",
    "cosyvoice2_instruct_control_one_candidate_stop_rule",
)
NEXT_ACTION = (
    "Select a distinct dialogue engine or newly supported timing/style implementation artifact. "
    "Do not retry the rejected CosyVoice2 instruct2 fast-control path, truncate or time-stretch its "
    "output, or reuse any rejected Parler/CosyVoice2 candidate as production proof."
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
    qa = ROOT / EVIDENCE_REL
    tracker = ROOT / "Plan/Tracker/Evidence/Wave64" / qa.name
    for path in (qa, tracker):
        if not path.is_file() or sha256(path) != EVIDENCE_SHA256:
            raise ValueError(f"instruct-control evidence hash mismatch: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("classification") != "COSYVOICE2_INSTRUCT_CONTROL_REJECTED_NO_RETRY":
            raise ValueError("instruct-control classification drift")
        acceptance = payload.get("acceptance", {})
        if acceptance.get("model_native_instruct_control_executed") is not True:
            raise ValueError("instruct-control execution drift")
        for key in (
            "candidate_exact_content_pass",
            "candidate_dialogue_timing_pass",
            "candidate_style_contract_pass",
            "independent_playback_review_pass",
            "production_review_authority_pass",
            "row_complete",
            "final_voice_certification_pass",
        ):
            if acceptance.get(key) is not False:
                raise ValueError(f"instruct-control fail-closed drift: {key}")
        if payload.get("decision", {}).get("same_instruct_control_retry_authorized") is not False:
            raise ValueError("instruct-control retry boundary drift")
    return {"qa": str(qa), "tracker": str(tracker), "sha256": EVIDENCE_SHA256}


def update_report_payload(payload: dict) -> dict:
    row = str(payload.get("item_id", ""))[-3:]
    spec = ROW_SPECS.get(row)
    if not spec or payload.get("tracker_id") != spec[0]:
        raise ValueError(f"unexpected report identity: {payload.get('item_id')}")
    if payload.get("status") != spec[2] or payload.get("row_complete") is not False:
        raise ValueError(f"report status drift: {payload.get('item_id')}")
    payload["timestamp"] = "2026-07-15T08:02:00-05:00"
    payload.setdefault("implementation", {}).update(
        {
            "cosyvoice2_instruct_control_runner_ready": True,
            "cosyvoice2_instruct_control_lineage_verifier_ready": True,
            "cosyvoice2_instruct_control_packager_ready": True,
            "cosyvoice2_instruct_control_tracking_ready": True,
        }
    )
    payload.setdefault("validation", {}).update(
        {
            "cosyvoice2_instruct_candidate_sha256": (
                "87db819128b524c4ff3b14e80445785aed2b5aa43665ed65c0686dccae27fb39"
            ),
            "cosyvoice2_instruct_candidate_duration_seconds": 7.32,
            "cosyvoice2_instruct_candidate_expected_duration_seconds": 3.0,
            "cosyvoice2_instruct_candidate_asr_transcript": "I'm not sure if I can get it.",
            "cosyvoice2_instruct_candidate_normalized_wer": 1.0,
            "cosyvoice2_instruct_candidate_speaker_similarity": 0.34052106738090515,
            "cosyvoice2_instruct_candidate_dnsmos_ovrl": 2.8629396650581356,
            "cosyvoice2_instruct_candidate_dnsmos_reference_percentile": 0.5,
            "cosyvoice2_instruct_candidate_emotion_label": "happy",
            "cosyvoice2_instruct_candidate_rejected": True,
            "cosyvoice2_instruct_same_control_retry_authorized": False,
        }
    )
    payload.setdefault("acceptance_gates", {}).update(
        {
            "cosyvoice2_instruct_candidate_exact_content_pass": False,
            "cosyvoice2_instruct_candidate_reference_speaker_score_pass": True,
            "cosyvoice2_instruct_candidate_dnsmos_worst_reference_floor_pass": True,
            "cosyvoice2_instruct_candidate_dnsmos_quality_certification_pass": None,
            "cosyvoice2_instruct_candidate_dialogue_timing_pass": False,
            "cosyvoice2_instruct_candidate_style_contract_pass": False,
            "candidate_reference_speaker_identity_verified": False,
            "independent_playback_review_pass": False,
            "production_review_authority_pass": False,
            "final_voice_certification_allowed": False,
        }
    )
    blockers = payload.get("blockers")
    if not isinstance(blockers, list):
        raise ValueError("report blockers are missing")
    matches = [
        entry
        for entry in blockers
        if isinstance(entry, dict) and entry.get("classification") == BLOCKER
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one production-candidate blocker, got {len(matches)}")
    matches[0].update(
        {
            "scope": "dialogue_candidate",
            "reason": (
                "No production-eligible dialogue candidate exists. The best corrected zero-shot take "
                "retains exact content but lasts 4.84 seconds; the single model-native instruct2 fast-control "
                "take lasts 7.32 seconds and changes the line at WER 1.0. Focused emotion remains unsupported, "
                "controlled intensity unmeasured, and playback/production authority absent."
            ),
        }
    )
    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError("report evidence is missing")
    existing = next(
        (entry for entry in evidence if isinstance(entry, dict) and entry.get("path") == EVIDENCE_REL),
        None,
    )
    if existing:
        existing["sha256"] = EVIDENCE_SHA256
    else:
        evidence.append({"path": EVIDENCE_REL, "sha256": EVIDENCE_SHA256})
    runtime = payload.setdefault("runtime", {})
    runtime["cosyvoice2_instruct_control_generation_count"] = 1
    runtime["cosyvoice2_candidate_evaluation_count"] = 3
    payload["next_action"] = NEXT_ACTION
    return payload


def update_report(path: Path, apply: bool) -> dict:
    payload = update_report_payload(json.loads(path.read_text(encoding="utf-8")))
    if apply:
        temporary = path.with_name(f".{path.name}.instruct-control.tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    return {"item_id": payload["item_id"], "status": payload["status"], "row_complete": False}


def update_csv(path: Path, key: str, evidence_field: str, specs: dict, apply: bool) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    required = {key, "Status", evidence_field, "Coverage_Audit_Status", "Notes"}
    if required - set(fields):
        raise ValueError(f"{path} is missing required fields")
    by_id = {spec[key]: spec for spec in specs.values()}
    changed = []
    for row in rows:
        row_id = row.get(key)
        if row_id not in by_id:
            continue
        if row.get("Status") != by_id[row_id]["status"]:
            raise ValueError(f"status drift for {row_id}")
        row[evidence_field] = append_unique(row.get(evidence_field, ""), EVIDENCE_REL, "; ")
        for tag in COVERAGE_TAGS:
            row["Coverage_Audit_Status"] = append_unique(
                row.get("Coverage_Audit_Status", ""), tag, "; "
            )
        row["Notes"] = append_unique(row.get("Notes", ""), NOTE, " | ")
        changed.append({"id": row_id, "status": row["Status"]})
    if len(changed) != 3:
        raise ValueError(f"{path} matched {len(changed)} rows, expected 3")
    if apply:
        temporary = path.with_name(f".{path.name}.instruct-control.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    tracker_specs = {
        row: {"Tracker_ID": spec[0], "status": spec[2]} for row, spec in ROW_SPECS.items()
    }
    item_specs = {
        row: {"Item_ID": spec[1], "status": spec[2]} for row, spec in ROW_SPECS.items()
    }
    result = {
        "mode": "apply" if args.apply else "dry_run",
        "evidence": verify_evidence(),
        "reports": [update_report(ROOT / path, args.apply) for path in REPORT_PATHS],
        "tracker": [
            update_csv(ROOT / path, "Tracker_ID", "Evidence_Path", tracker_specs, args.apply)
            for path in TRACKER_PATHS
        ],
        "items": [
            update_csv(ROOT / path, "Item_ID", "Evidence_Required", item_specs, args.apply)
            for path in ITEM_PATHS
        ],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
