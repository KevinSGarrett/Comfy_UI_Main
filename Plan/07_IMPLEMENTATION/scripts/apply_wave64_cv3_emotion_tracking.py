#!/usr/bin/env python3
"""Apply the full CV3 emotion2vec calibration to affected Wave64 ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_REL = "Plan/Instructions/QA/Evidence/Wave64/W64_CV3_EMOTION2VEC_LOCAL_CALIBRATION_20260715T001113-0500.json"
EVIDENCE_SHA256 = "d2be31070c286c7c3998ca9f39bda3c2778f2c3422ad904aa531f356d3a76f44"
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
    "Wave64 CV3 emotion2vec calibration 2026-07-15: the exact Apache-2.0 ModelScope "
    "emotion2vec_plus_large payload executed over all 300 paired CV3 references at 72.33% accuracy "
    "and 0.7967 macro F1. The immutable Parler take scored neutral at 0.999997, but focused/controlled "
    "is outside the model/CV3 taxonomies; no mapping, threshold, playback, production authority, row "
    "completion, or certification was claimed."
)
COVERAGE_TAGS = (
    "cv3_emotion2vec_full_calibration_hash_bound",
    "focused_controlled_taxonomy_and_authority_blocked",
)
BLOCKER_CLASSIFICATION = "Blocked_Voice_Emotion_Taxonomy_Authority_Missing"
BLOCKER_REASON = (
    "The exact licensed emotion2vec_plus_large payload executed over all 300 paired CV3 emotion "
    "references and scored the candidate neutral at 0.99999678, but the contract target "
    "focused/controlled is outside the model and CV3 taxonomies. No registered threshold or approved "
    "mapping authorizes emotion PASS."
)
NEXT_ACTION = (
    "Obtain independent playback and a bound reference-speaker recording for the immutable Parler "
    "candidate. If machine-verifiable emotion proof is required, define and calibrate an explicit "
    "supported contract taxonomy; do not relabel neutral as focused or controlled, and do not rerun "
    "completed generation unless playback rejects the take."
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
            raise ValueError(f"CV3 emotion evidence hash mismatch: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        acceptance = payload.get("acceptance", {})
        if acceptance.get("emotion_model_execution_path_verified") is not True:
            raise ValueError("CV3 emotion evidence must verify model execution")
        if acceptance.get("candidate_emotion_verified") is not False:
            raise ValueError("CV3 emotion evidence must block candidate emotion verification")
        if payload.get("row_complete") is not False:
            raise ValueError("CV3 emotion evidence must remain row-incomplete")
    return {"qa": str(qa_path), "tracker": str(tracker_path), "sha256": EVIDENCE_SHA256}


def update_report_payload(payload: dict) -> dict:
    row = str(payload.get("item_id", ""))[-3:]
    spec = ROW_SPECS.get(row)
    if not spec or payload.get("tracker_id") != spec["tracker_id"]:
        raise ValueError(f"unexpected Wave64 report identity: {payload.get('item_id')}")
    if payload.get("status") != spec["status"] or payload.get("row_complete") is not False:
        raise ValueError(f"Wave64 report status drift: {payload.get('item_id')}")

    payload["timestamp"] = "2026-07-15T00:11:13-05:00"
    payload.setdefault("implementation", {})["cv3_emotion2vec_calibration_adapter_ready"] = True
    validation = payload.setdefault("validation", {})
    validation.update(
        {
            "cv3_emotion2vec_model_intake": "exact_license_revision_and_hash_pass",
            "cv3_emotion_reference_sample_count": 300,
            "cv3_emotion_accuracy": 0.7233333333333334,
            "cv3_emotion_macro_f1": 0.7967110893382565,
            "parler_tts_cv3_emotion_label": "neutral",
            "parler_tts_cv3_emotion_score": 0.9999967813491821,
            "parler_tts_target_emotion": "focused",
            "parler_tts_target_intensity": "controlled",
            "parler_tts_emotion_taxonomy_supported": False,
        }
    )
    gates = payload.setdefault("acceptance_gates", {})
    gates["cv3_emotion_model_execution_path_verified"] = True
    gates["cv3_candidate_emotion_score_present"] = True
    gates["candidate_emotion_verified"] = False

    blockers = payload.get("blockers")
    if not isinstance(blockers, list):
        raise ValueError(f"Wave64 report blockers are missing: {payload.get('item_id')}")
    matching = [
        blocker
        for blocker in blockers
        if isinstance(blocker, dict)
        and blocker.get("classification")
        in {"Blocked_Voice_Emotion_Model_Payload_Missing", BLOCKER_CLASSIFICATION}
    ]
    if len(matching) != 1:
        raise ValueError(f"expected one emotion blocker in {payload.get('item_id')}, got {len(matching)}")
    matching[0]["classification"] = BLOCKER_CLASSIFICATION
    matching[0]["reason"] = BLOCKER_REASON

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
    payload.setdefault("runtime", {})["cv3_emotion_calibration_count"] = 1
    payload["next_action"] = NEXT_ACTION
    return payload


def update_report(path: Path, apply: bool) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    updated = update_report_payload(payload)
    if apply:
        temporary = path.with_name(f".{path.name}.cv3-emotion.tmp")
        temporary.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    return {
        "path": str(path),
        "item_id": updated["item_id"],
        "status": updated["status"],
        "row_complete": updated["row_complete"],
        "emotion_execution_verified": updated["acceptance_gates"]["cv3_emotion_model_execution_path_verified"],
        "candidate_emotion_verified": updated["acceptance_gates"]["candidate_emotion_verified"],
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
        temporary = path.with_name(f".{path.name}.cv3-emotion.tmp")
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
                "rows": update_csv(ROOT / path, "Tracker_ID", "Evidence_Path", tracker_specs, args.apply),
            }
            for path in TRACKER_PATHS
        ],
        "items": [
            {
                "path": path,
                "rows": update_csv(ROOT / path, "Item_ID", "Evidence_Required", item_specs, args.apply),
            }
            for path in ITEM_PATHS
        ],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
