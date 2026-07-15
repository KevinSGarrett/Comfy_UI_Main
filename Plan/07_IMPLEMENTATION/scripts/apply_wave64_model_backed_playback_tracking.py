#!/usr/bin/env python3
"""Apply the Wave64 model-backed playback result to the three affected rows."""

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
    "W64_MODEL_BACKED_PLAYBACK_AND_REPLACEMENT_REJECTION_20260715T012540-0500.json"
)
EVIDENCE_SHA256 = "0bdc4a5fdb5ded97418fb5e739e72f6d5fc50b6ca6a2d33f5c39f1266a202236"
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
NOTE = (
    "Wave64 model-backed playback 2026-07-15: a non-synthetic Whisper/DNSMOS/emotion2vec producer "
    "is hash-bound and allowlisted for playback review only. It hard-abstained from a strict proof for "
    "the original Parler take because focused/controlled is unsupported and identified the exact beat-to-B "
    "content mismatch. One separately seeded replacement was then generated under the explicit rejection "
    "guard and rejected at WER 0.70. No candidate, production authority, row, or certification was promoted."
)
COVERAGE_TAGS = (
    "model_backed_playback_producer_hash_bound",
    "original_and_replacement_dialogue_candidates_rejected",
)
BLOCKER_CLASSIFICATION = "Blocked_Model_Backed_Playback_Content_And_Style_Authority"
BLOCKER_REASON = (
    "The original candidate is technically clean but has a critical beat-to-B content mismatch and cannot "
    "emit a strict playback proof because focused/controlled is outside the calibrated style taxonomy. The "
    "single authorized seed-64028 replacement is also rejected because its independent Whisper WER is 0.70."
)
NEXT_ACTION = (
    "Keep both dialogue candidates rejected. Calibrate a genuinely perceptual audio reviewer or bind an "
    "independent reference speaker plus a supported style taxonomy before another dialogue generation; do "
    "not use the playback producer as production-review authority."
)


def canonical_json_sha256(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"evidence is not UTF-8 JSON text: {path}") from exc
    canonical = text.replace("\r\n", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_unique(current: str, value: str, separator: str) -> str:
    entries = [entry.strip() for entry in (current or "").split(separator) if entry.strip()]
    if value not in entries:
        entries.append(value)
    return separator.join(entries)


def verify_evidence() -> dict:
    qa_path = ROOT / EVIDENCE_REL
    tracker_path = ROOT / "Plan/Tracker/Evidence/Wave64" / qa_path.name
    for path in (qa_path, tracker_path):
        if not path.is_file() or canonical_json_sha256(path) != EVIDENCE_SHA256:
            raise ValueError(f"model-backed playback evidence hash mismatch: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        gates = payload.get("gates", {})
        if gates.get("producer_model_and_calibration_hash_binding_pass") is not True:
            raise ValueError("playback producer binding gate must pass")
        if gates.get("original_playback_proof_emitted") is not False:
            raise ValueError("original candidate must not emit a playback proof")
        if gates.get("replacement_intelligibility_pass") is not False:
            raise ValueError("replacement candidate must remain rejected")
        if gates.get("row_complete") is not False or gates.get("certification_pass") is not False:
            raise ValueError("evidence must remain row-incomplete and uncertified")
    return {"qa": str(qa_path), "tracker": str(tracker_path), "sha256": EVIDENCE_SHA256}


def update_report_payload(payload: dict) -> dict:
    row = str(payload.get("item_id", ""))[-3:]
    spec = ROW_SPECS.get(row)
    if not spec or payload.get("tracker_id") != spec["tracker_id"]:
        raise ValueError(f"unexpected Wave64 report identity: {payload.get('item_id')}")
    if payload.get("status") != spec["status"] or payload.get("row_complete") is not False:
        raise ValueError(f"Wave64 report status drift: {payload.get('item_id')}")

    payload["timestamp"] = "2026-07-15T01:25:40-05:00"
    payload.setdefault("implementation", {})["model_backed_playback_producer_ready"] = True
    validation = payload.setdefault("validation", {})
    validation.update(
        {
            "model_backed_playback_combined_tests_passed": 117,
            "model_backed_playback_combined_test_failures": 0,
            "model_backed_playback_original_status": "ABSTAINED_UNSUPPORTED_REQUIRED_CATEGORY",
            "model_backed_playback_original_exact_content_pass": False,
            "model_backed_playback_original_dnsmos_cleanliness_score": 4.293041,
            "model_backed_playback_original_technical_consistency_score": 5.0,
            "model_backed_playback_original_proof_emitted": False,
            "parler_replacement_seed": 64028,
            "parler_replacement_runtime_executed": True,
            "parler_replacement_speech_truncated": False,
            "parler_replacement_asr_transcript": "We hold the frames.",
            "parler_replacement_normalized_wer": 0.7,
            "parler_replacement_intelligibility_pass": False,
        }
    )
    gates = payload.setdefault("acceptance_gates", {})
    gates["non_synthetic_playback_producer_allowlisted"] = True
    gates["candidate_model_backed_playback_proof_present"] = False
    gates["candidate_exact_content_verified"] = False
    gates["replacement_candidate_intelligibility_verified"] = False
    gates["independent_playback_review_pass"] = False
    gates["production_review_authority_pass"] = False
    gates["final_voice_certification_allowed"] = False

    blockers = payload.get("blockers")
    if not isinstance(blockers, list):
        raise ValueError(f"Wave64 report blockers are missing: {payload.get('item_id')}")
    old_classes = {
        "Blocked_Voice_Playback_Quality_Edge_Review_Missing",
        "Blocked_Model_Backed_Playback_Content_And_Style_Authority",
    }
    matching = [
        blocker
        for blocker in blockers
        if isinstance(blocker, dict) and blocker.get("classification") in old_classes
    ]
    if len(matching) > 1:
        raise ValueError(f"duplicate playback blockers in {payload.get('item_id')}")
    if matching:
        matching[0]["classification"] = BLOCKER_CLASSIFICATION
        matching[0]["scope"] = "dialogue_candidates"
        matching[0]["reason"] = BLOCKER_REASON
    else:
        blockers.append(
            {
                "classification": BLOCKER_CLASSIFICATION,
                "scope": "dialogue_candidates",
                "reason": BLOCKER_REASON,
            }
        )

    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError(f"Wave64 report evidence is missing: {payload.get('item_id')}")
    existing = next(
        (item for item in evidence if isinstance(item, dict) and item.get("path") == EVIDENCE_REL),
        None,
    )
    if existing is None:
        evidence.append({"path": EVIDENCE_REL, "sha256": EVIDENCE_SHA256})
    else:
        existing["sha256"] = EVIDENCE_SHA256
    payload.setdefault("runtime", {})["parler_replacement_generation_count"] = 1
    payload["next_action"] = NEXT_ACTION
    return payload


def update_report(path: Path, apply: bool) -> dict:
    updated = update_report_payload(json.loads(path.read_text(encoding="utf-8")))
    if apply:
        temporary = path.with_name(f".{path.name}.model-playback.tmp")
        temporary.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    return {
        "path": str(path),
        "item_id": updated["item_id"],
        "status": updated["status"],
        "row_complete": updated["row_complete"],
        "proof_emitted": updated["acceptance_gates"]["candidate_model_backed_playback_proof_present"],
        "replacement_pass": updated["acceptance_gates"]["replacement_candidate_intelligibility_verified"],
    }


def update_csv(path: Path, key: str, evidence_field: str, specs: dict[str, dict], apply: bool) -> list[dict]:
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
            raise ValueError(f"{path} status decision drift for {row_id}: {row.get('Status_Decision')}")
        row[evidence_field] = append_unique(row.get(evidence_field, ""), EVIDENCE_REL, "; ")
        for tag in COVERAGE_TAGS:
            row["Coverage_Audit_Status"] = append_unique(row.get("Coverage_Audit_Status", ""), tag, "; ")
        row["Notes"] = append_unique(row.get("Notes", ""), NOTE, " | ")
        changed.append({"id": row_id, "status": row["Status"], "evidence_linked": True})
    if len(changed) != len(specs):
        raise ValueError(f"{path} matched {len(changed)} rows, expected {len(specs)}")
    if apply:
        temporary = path.with_name(f".{path.name}.model-playback.tmp")
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
    tracker_specs = {key: {**value, "Tracker_ID": value["tracker_id"]} for key, value in ROW_SPECS.items()}
    item_specs = {key: {**value, "Item_ID": value["item_id"]} for key, value in ROW_SPECS.items()}
    result = {
        "mode": "apply" if args.apply else "dry_run",
        "evidence": verify_evidence(),
        "reports": [update_report(ROOT / path, args.apply) for path in REPORT_PATHS],
        "tracker": [
            {"path": path, "rows": update_csv(ROOT / path, "Tracker_ID", "Evidence_Path", tracker_specs, args.apply)}
            for path in TRACKER_PATHS
        ],
        "items": [
            {"path": path, "rows": update_csv(ROOT / path, "Item_ID", "Evidence_Required", item_specs, args.apply)}
            for path in ITEM_PATHS
        ],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
