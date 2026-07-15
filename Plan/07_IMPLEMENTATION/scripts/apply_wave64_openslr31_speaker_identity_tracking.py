#!/usr/bin/env python3
"""Apply OpenSLR31 speaker-validation evidence to affected Wave64 ledgers."""

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
    "W64_OPENSLR31_SPEAKER_IDENTITY_VALIDATION_20260715T035744-0500.json"
)
EVIDENCE_SHA256 = "b4164e44f2e3f3ea693fd2434316b48af96b81e9d71b44460a16b7be1ac3c986"
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
SUPERSEDED_BLOCKER = "Blocked_Voice_Speaker_Threshold_Generalization"
NOTE = (
    "Wave64 OpenSLR31 speaker validation 2026-07-15: 26 independently labeled speakers and "
    "1,089 utterances were split into disjoint 13/13 partitions. The fixed threshold 0.334456 "
    "passed held-out TPR/FPR at 0.99487/0.02564, and the existing 0.99327 public-domain "
    "source-to-derived-stem score now passes chain-specific identity preservation. Candidate "
    "reference-speaker binding, style, playback authority, and production certification remain blocked."
)
COVERAGE_TAGS = (
    "openslr31_speaker_disjoint_validation_pass",
    "licensed_human_voice_chain_identity_pass",
    "production_voice_authority_still_blocked",
)
NEXT_ACTION = (
    "Bind an independent reference-speaker recording to a production-eligible dialogue candidate and "
    "a supported emotion/style taxonomy, then obtain independent playback and allowlisted production "
    "review. Preserve both rejected Parler candidates and do not treat this chain-specific source-to-stem "
    "identity pass as TTS speaker identity or final voice certification."
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
            raise ValueError(f"OpenSLR31 speaker evidence hash mismatch: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        acceptance = payload.get("acceptance", {})
        if acceptance.get("speaker_disjoint_threshold_generalization_pass") is not True:
            raise ValueError("OpenSLR31 evidence must verify speaker-disjoint threshold validation")
        if acceptance.get("chain_specific_identity_preservation_verified") is not True:
            raise ValueError("OpenSLR31 evidence must verify chain-specific identity preservation")
        if acceptance.get("production_review_authority_pass") is not False:
            raise ValueError("OpenSLR31 evidence must block production authority")
        if payload.get("row_complete") is not False:
            raise ValueError("OpenSLR31 speaker evidence must remain row-incomplete")
    return {"qa": str(qa_path), "tracker": str(tracker_path), "sha256": EVIDENCE_SHA256}


def update_report_payload(payload: dict) -> dict:
    row = str(payload.get("item_id", ""))[-3:]
    spec = ROW_SPECS.get(row)
    if not spec or payload.get("tracker_id") != spec["tracker_id"]:
        raise ValueError(f"unexpected Wave64 report identity: {payload.get('item_id')}")
    if payload.get("status") != spec["status"] or payload.get("row_complete") is not False:
        raise ValueError(f"Wave64 report status drift: {payload.get('item_id')}")
    payload["timestamp"] = "2026-07-15T03:57:44-05:00"
    payload.setdefault("implementation", {})[
        "openslr31_speaker_identity_validation_adapter_ready"
    ] = True
    payload.setdefault("validation", {}).update(
        {
            "openslr31_speaker_count": 26,
            "openslr31_utterance_count": 1089,
            "openslr31_calibration_speaker_count": 13,
            "openslr31_validation_speaker_count": 13,
            "openslr31_speaker_overlap_count": 0,
            "openslr31_calibration_positive_pair_count": 195,
            "openslr31_calibration_different_speaker_pair_count": 2808,
            "openslr31_validation_positive_pair_count": 195,
            "openslr31_validation_different_speaker_pair_count": 2808,
            "openslr31_validated_speaker_threshold": 0.33445611596107483,
            "openslr31_calibration_true_positive_rate": 1.0,
            "openslr31_calibration_false_positive_rate": 0.02207977207977208,
            "openslr31_validation_true_positive_rate": 0.9948717948717949,
            "openslr31_validation_false_positive_rate": 0.02564102564102564,
            "openslr31_speaker_disjoint_validation_pass": True,
            "licensed_human_voice_chain_speaker_similarity": 0.9932656288146973,
            "licensed_human_voice_chain_identity_verified": True,
        }
    )
    payload.setdefault("acceptance_gates", {}).update(
        {
            "openslr31_speaker_disjoint_validation_pass": True,
            "speaker_threshold_deployment_allowed_for_chain_specific_evaluation": True,
            "licensed_human_voice_chain_identity_similarity_observed": True,
            "licensed_human_voice_chain_identity_verified": True,
            "candidate_reference_speaker_identity_verified": False,
            "independent_playback_review_pass": False,
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
        if isinstance(blocker, dict) and blocker.get("classification") == SUPERSEDED_BLOCKER
    ]
    if len(matching) > 1:
        raise ValueError(f"duplicate superseded speaker blockers: {payload.get('item_id')}")
    payload["blockers"] = [blocker for blocker in blockers if blocker not in matching]

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
    payload.setdefault("runtime", {})["openslr31_speaker_validation_execution_count"] = 1
    payload["next_action"] = NEXT_ACTION
    return payload


def update_report(path: Path, apply: bool) -> dict:
    payload = update_report_payload(json.loads(path.read_text(encoding="utf-8")))
    if apply:
        temporary = path.with_name(f".{path.name}.openslr31-speaker.tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    return {
        "path": str(path),
        "item_id": payload["item_id"],
        "status": payload["status"],
        "row_complete": payload["row_complete"],
        "speaker_disjoint_validation_pass": payload["acceptance_gates"][
            "openslr31_speaker_disjoint_validation_pass"
        ],
        "chain_specific_identity_verified": payload["acceptance_gates"][
            "licensed_human_voice_chain_identity_verified"
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
        temporary = path.with_name(f".{path.name}.openslr31-speaker.tmp")
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
