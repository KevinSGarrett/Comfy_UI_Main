#!/usr/bin/env python3
"""Apply the CV3 speaker-threshold blocker to affected Wave64 ledgers."""

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
    "W64_CV3_SPEAKER_IDENTITY_CALIBRATION_BLOCKER_20260715T030600-0500.json"
)
EVIDENCE_SHA256 = "ea0c63de436bfebfc0fe5759a9fa15719702bdb83e4629ccc5238c89efe61916"
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
BLOCKER_CLASSIFICATION = "Blocked_Voice_Speaker_Threshold_Generalization"
BLOCKER_REASON = (
    "ERes2Net executed over all 46 paired English CV3 continuation references. Three of four "
    "category-held-out folds passed, but the emotion holdout false-positive rate was 0.15417 "
    "against the predeclared 0.10 maximum. The observed full-fit threshold is therefore not "
    "deployable, and the 0.99327 LibriVox source-to-derived-stem similarity cannot be promoted "
    "to an identity-preservation PASS."
)
NOTE = (
    "Wave64 CV3 speaker calibration 2026-07-15: 46 matched continuation pairs and 510 "
    "nonmatching within-category pairs executed. Full-fit TPR/FPR was 1.0/0.08824 at threshold "
    "0.41601, but the emotion-held-out FPR was 0.15417, so threshold deployment and the observed "
    "0.99327 LibriVox source-to-stem identity score remain fail-closed."
)
COVERAGE_TAGS = (
    "cv3_speaker_matched_pair_calibration_executed",
    "speaker_threshold_generalization_and_authority_blocked",
)
NEXT_ACTION = (
    "Calibrate ERes2Net against an independently speaker-labeled, disjoint validation set before "
    "binding any TTS candidate to a reference speaker. Keep the 0.99327 LibriVox chain score "
    "observational; do not relax the held-out false-positive gate, register production authority, "
    "or generate another dialogue take from this evidence."
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
            raise ValueError(f"CV3 speaker evidence hash mismatch: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        acceptance = payload.get("acceptance", {})
        if acceptance.get("speaker_model_execution_path_verified") is not True:
            raise ValueError("CV3 speaker evidence must verify model execution")
        if acceptance.get("speaker_threshold_generalization_pass") is not False:
            raise ValueError("CV3 speaker evidence must block threshold generalization")
        if acceptance.get("production_review_authority_pass") is not False:
            raise ValueError("CV3 speaker evidence must block production authority")
        if payload.get("row_complete") is not False:
            raise ValueError("CV3 speaker evidence must remain row-incomplete")
    return {"qa": str(qa_path), "tracker": str(tracker_path), "sha256": EVIDENCE_SHA256}


def update_report_payload(payload: dict) -> dict:
    row = str(payload.get("item_id", ""))[-3:]
    spec = ROW_SPECS.get(row)
    if not spec or payload.get("tracker_id") != spec["tracker_id"]:
        raise ValueError(f"unexpected Wave64 report identity: {payload.get('item_id')}")
    if payload.get("status") != spec["status"] or payload.get("row_complete") is not False:
        raise ValueError(f"Wave64 report status drift: {payload.get('item_id')}")
    payload["timestamp"] = "2026-07-15T03:06:00-05:00"
    payload.setdefault("implementation", {})[
        "cv3_speaker_identity_calibration_adapter_ready"
    ] = True
    payload.setdefault("validation", {}).update(
        {
            "cv3_speaker_continuation_pair_count": 46,
            "cv3_speaker_nonmatching_pair_count": 510,
            "cv3_speaker_full_fit_threshold": 0.41600924730300903,
            "cv3_speaker_full_fit_true_positive_rate": 1.0,
            "cv3_speaker_full_fit_false_positive_rate": 0.08823529411764706,
            "cv3_speaker_category_held_out_validation_pass": False,
            "cv3_speaker_emotion_holdout_false_positive_rate": 0.15416666666666667,
            "licensed_human_voice_chain_speaker_similarity": 0.9932656288146973,
            "licensed_human_voice_chain_identity_verified": False,
        }
    )
    gates = payload.setdefault("acceptance_gates", {})
    gates.update(
        {
            "cv3_speaker_matched_pair_calibration_executed": True,
            "cv3_speaker_threshold_generalization_pass": False,
            "licensed_human_voice_chain_identity_similarity_observed": True,
            "licensed_human_voice_chain_identity_verified": False,
            "candidate_reference_speaker_identity_verified": False,
            "production_review_authority_pass": False,
            "final_voice_certification_allowed": False,
        }
    )
    blockers = payload.get("blockers")
    if not isinstance(blockers, list):
        raise ValueError(f"Wave64 report blockers are missing: {payload.get('item_id')}")
    matching = [
        blocker
        for blocker in blockers
        if isinstance(blocker, dict) and blocker.get("classification") == BLOCKER_CLASSIFICATION
    ]
    if len(matching) > 1:
        raise ValueError(f"duplicate speaker-threshold blockers: {payload.get('item_id')}")
    if matching:
        matching[0]["reason"] = BLOCKER_REASON
    else:
        blockers.append({"classification": BLOCKER_CLASSIFICATION, "reason": BLOCKER_REASON})
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
    payload.setdefault("runtime", {})["cv3_speaker_calibration_execution_count"] = 1
    payload["next_action"] = NEXT_ACTION
    return payload


def update_report(path: Path, apply: bool) -> dict:
    payload = update_report_payload(json.loads(path.read_text(encoding="utf-8")))
    if apply:
        temporary = path.with_name(f".{path.name}.cv3-speaker.tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    return {
        "path": str(path),
        "item_id": payload["item_id"],
        "status": payload["status"],
        "row_complete": payload["row_complete"],
        "threshold_generalization_pass": payload["acceptance_gates"][
            "cv3_speaker_threshold_generalization_pass"
        ],
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
        for tag in COVERAGE_TAGS:
            row["Coverage_Audit_Status"] = append_unique(
                row.get("Coverage_Audit_Status", ""), tag, "; "
            )
        row["Notes"] = append_unique(row.get("Notes", ""), NOTE, " | ")
        changed.append({"id": row_id, "status": row["Status"], "evidence_linked": True})
    if len(changed) != len(specs):
        raise ValueError(f"{path} matched {len(changed)} rows, expected {len(specs)}")
    if apply:
        temporary = path.with_name(f".{path.name}.cv3-speaker.tmp")
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
