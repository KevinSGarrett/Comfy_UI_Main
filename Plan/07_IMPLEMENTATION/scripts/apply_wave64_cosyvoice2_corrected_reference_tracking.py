#!/usr/bin/env python3
"""Track the corrected-reference CosyVoice2 timing rejection."""

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
    "W64_COSYVOICE2_CORRECTED_REFERENCE_CANDIDATE_20260715T064000-0500.json"
)
EVIDENCE_SHA256 = "95e8cf23052028783f29503b760de9d419d33b0af7d04ece703f705543f5f12c"
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
    "Wave64 CosyVoice2 corrected-reference take 2026-07-15: a 5.0-second public-domain reference "
    "eliminated the repetitive collapse. The immutable take has exact ASR at WER 0.0, speaker score "
    "0.66076 >= 0.33446, and DNSMOS OVRL 3.17410 at the 75th reference percentile. It remains rejected "
    "because 4.84 seconds exceeds the 3.0-second contract; focused emotion is unsupported, controlled "
    "intensity is unmeasured, and playback/production authority is absent."
)
COVERAGE_TAGS = (
    "cosyvoice2_corrected_reference_exact_content_pass",
    "cosyvoice2_corrected_reference_speaker_score_pass",
    "cosyvoice2_corrected_reference_timing_rejected",
)
NEXT_ACTION = (
    "Select a dialogue engine or supported control path that can satisfy the immutable 3.0-second "
    "contract without truncation or time-stretching while retaining exact content, reference-speaker "
    "identity, and a supported style taxonomy. Preserve all rejected Parler and CosyVoice2 takes."
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
            raise ValueError(f"corrected-reference evidence hash mismatch: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        acceptance = payload.get("acceptance", {})
        required_true = (
            "candidate_exact_content_pass",
            "candidate_reference_speaker_score_pass",
            "candidate_dnsmos_worst_reference_floor_pass",
        )
        if any(acceptance.get(key) is not True for key in required_true):
            raise ValueError("corrected-reference narrow pass drift")
        required_false = (
            "candidate_dialogue_timing_pass",
            "independent_playback_review_pass",
            "production_review_authority_pass",
            "row_complete",
            "final_voice_certification_pass",
        )
        if any(acceptance.get(key) is not False for key in required_false):
            raise ValueError("corrected-reference fail-closed drift")
        if payload.get("decision", {}).get("candidate_rejected") is not True:
            raise ValueError("corrected-reference candidate must remain rejected")
    return {"qa": str(qa), "tracker": str(tracker), "sha256": EVIDENCE_SHA256}


def update_report_payload(payload: dict) -> dict:
    row = str(payload.get("item_id", ""))[-3:]
    spec = ROW_SPECS.get(row)
    if not spec or payload.get("tracker_id") != spec[0]:
        raise ValueError(f"unexpected report identity: {payload.get('item_id')}")
    if payload.get("status") != spec[2] or payload.get("row_complete") is not False:
        raise ValueError(f"report status drift: {payload.get('item_id')}")
    payload["timestamp"] = "2026-07-15T06:45:00-05:00"
    payload.setdefault("implementation", {}).update(
        {
            "cosyvoice2_validated_source_path_activation_ready": True,
            "cosyvoice2_corrected_reference_packager_ready": True,
            "cosyvoice2_corrected_reference_tracking_ready": True,
        }
    )
    payload.setdefault("validation", {}).update(
        {
            "cosyvoice2_corrected_reference_sha256": (
                "f1e5f767d775c514cf94cdedfdf0010961102a3358e095812301e5da72e6d932"
            ),
            "cosyvoice2_corrected_reference_duration_seconds": 5.0,
            "cosyvoice2_corrected_candidate_sha256": (
                "845b8971bd9ca8e3898e632cd02ad14f0eb0c1d2d6b1ec3cdd2e537fb94295ba"
            ),
            "cosyvoice2_corrected_candidate_duration_seconds": 4.84,
            "cosyvoice2_corrected_candidate_expected_duration_seconds": 3.0,
            "cosyvoice2_corrected_candidate_asr_transcript": (
                "We hold the frame steady and move on the beat."
            ),
            "cosyvoice2_corrected_candidate_normalized_wer": 0.0,
            "cosyvoice2_corrected_candidate_speaker_similarity": 0.6607623100280762,
            "cosyvoice2_corrected_candidate_dnsmos_ovrl": 3.174097435695213,
            "cosyvoice2_corrected_candidate_dnsmos_reference_percentile": 0.75,
            "cosyvoice2_corrected_candidate_emotion_label": "neutral",
            "cosyvoice2_corrected_candidate_rejected": True,
        }
    )
    gates = payload.setdefault("acceptance_gates", {})
    gates.update(
        {
            "cosyvoice2_corrected_candidate_exact_content_pass": True,
            "cosyvoice2_corrected_candidate_reference_speaker_score_pass": True,
            "cosyvoice2_corrected_candidate_dnsmos_worst_reference_floor_pass": True,
            "cosyvoice2_corrected_candidate_dnsmos_quality_certification_pass": None,
            "cosyvoice2_corrected_candidate_dialogue_timing_pass": False,
            "cosyvoice2_corrected_candidate_style_contract_pass": False,
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
        entry for entry in blockers if isinstance(entry, dict) and entry.get("classification") == BLOCKER
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one production-candidate blocker, got {len(matches)}")
    matches[0].update(
        {
            "scope": "dialogue_candidate",
            "reason": (
                "The corrected-reference take now passes exact content and the chain-specific speaker "
                "score, but 4.84 seconds exceeds the immutable 3.0-second contract. Focused emotion is "
                "unsupported, controlled intensity is unmeasured, and no production-eligible candidate "
                "combines timing, content, speaker, style, playback, and authority proof."
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
    payload.setdefault("runtime", {})["cosyvoice2_zero_shot_generation_count"] = 2
    payload["runtime"]["cosyvoice2_candidate_evaluation_count"] = 2
    payload["next_action"] = NEXT_ACTION
    return payload


def update_report(path: Path, apply: bool) -> dict:
    payload = update_report_payload(json.loads(path.read_text(encoding="utf-8")))
    if apply:
        temporary = path.with_name(f".{path.name}.corrected-cosyvoice2.tmp")
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
        temporary = path.with_name(f".{path.name}.corrected-cosyvoice2.tmp")
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
    item_specs = {row: {"Item_ID": spec[1], "status": spec[2]} for row, spec in ROW_SPECS.items()}
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
