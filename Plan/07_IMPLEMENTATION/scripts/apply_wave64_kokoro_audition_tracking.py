#!/usr/bin/env python3
"""Apply the Kokoro automated-eligible audition to Wave64 ledgers idempotently."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_REL = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "W64_KOKORO_C01_AUTOMATED_ELIGIBILITY_20260715T131034-0500.json"
)
EVIDENCE_SHA256 = "f7bb114b4a031e6fc85a045b50701ad520bd8ee8f7aceaf85f5c5012dc937077"
REPORTS = {
    "025": "Plan/Items/Reports/ITEM-W64-025_audio_pipeline_build.json",
    "026": "Plan/Items/Reports/ITEM-W64-026_audio_engine_routing.json",
    "027": "Plan/Items/Reports/ITEM-W64-027_audio_voice_dialogue.json",
    "031": "Plan/Items/Reports/ITEM-W64-031_audio_strict_review.json",
}
ROW_SPECS = {
    "025": {
        "tracker_id": "TRK-W64-025",
        "item_id": "ITEM-W64-025",
        "before": "Blocked_Production_Eligible_Audio_Candidate_Missing",
        "after": "Blocked_Audio_Playback_Review_Missing",
    },
    "026": {
        "tracker_id": "TRK-W64-026",
        "item_id": "ITEM-W64-026",
        "before": "Blocked_Audio_Engine_Authority_Not_Approved",
        "after": "Blocked_Audio_Engine_Authority_Not_Approved",
    },
    "027": {
        "tracker_id": "TRK-W64-027",
        "item_id": "ITEM-W64-027",
        "before": "Blocked_Production_Eligible_Voice_Candidate_Missing",
        "after": "Blocked_Human_Audio_Playback_Review_Missing",
    },
    "031": {
        "tracker_id": "TRK-W64-031",
        "item_id": "ITEM-W64-031",
        "before": "Blocked_Strict_Audio_Production_Review_Proof_Missing",
        "after": "Blocked_Strict_Audio_Production_Review_Proof_Missing",
    },
}
TRACKER_PATHS = (
    "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv",
    "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
)
ITEM_PATHS = (
    "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv",
    "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
)
STALE_BLOCKERS = {
    "Blocked_Production_Eligible_Audio_Candidate_Missing",
    "Blocked_Production_Eligible_Voice_Candidate_Missing",
    "Blocked_Model_Backed_Playback_Content_And_Style_Authority",
    "Blocked_Voice_Emotion_Taxonomy_Authority_Missing",
    "Blocked_Audio_Engine_Proof_Artifacts_Missing",
}
GATE_UPDATES = {
    "kokoro_three_speed_audition_generated": True,
    "kokoro_exact_content_asr_pass": True,
    "kokoro_exact_dialogue_timing_pass": True,
    "kokoro_dnsmos_calibrated_floor_pass": True,
    "kokoro_synthetic_voice_continuity_pass": True,
    "kokoro_automated_candidate_eligibility_pass": True,
    "kokoro_human_playback_request_ready": True,
    "candidate_exact_content_verified": True,
    "automated_eligible_dialogue_candidate_present": True,
    "production_eligible_dialogue_candidate_present": False,
    "independent_playback_review_pass": False,
    "production_review_authority_pass": False,
    "final_voice_certification_allowed": False,
    "row_complete": False,
}
NOTE = (
    "Wave64 Kokoro audition 2026-07-15: one predeclared three-speed local CPU batch produced three "
    "immutable exact-3.000-second PCM candidates with no truncation, time stretch, normalization, or retry. "
    "All three scored WER 0.0 and passed calibrated DNSMOS and synthetic-voice continuity gates. The "
    "speed-1.00 hash a212653c029f5677b97bba8c769186fc11d29b561b4ca19a2344ff294a5fdd56 "
    "was selected by the predeclared highest-DNSMOS rule and has a schema-valid blinded human playback "
    "request. Human playback and distinct final-production authority remain blocked; no production promotion occurred."
)
NEXT_ACTION = (
    "Collect one independent human playback record against the prepared exact-hash Kokoro request, validate "
    "it through the canonical human playback validator, and only then consider the separate final-production "
    "authority gate. Do not regenerate or alter the three audition candidates."
)
COVERAGE_TAGS = (
    "kokoro_three_speed_immutable_audition_generated",
    "kokoro_automated_candidate_eligibility_pass",
    "kokoro_human_playback_request_hash_bound",
    "human_playback_and_final_production_authority_still_blocked",
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


def write_json(path: Path, payload: dict[str, Any], apply: bool) -> None:
    if not apply:
        return
    temporary = path.with_name(f".{path.name}.kokoro.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def verify_evidence() -> dict[str, Any]:
    qa = ROOT / EVIDENCE_REL
    tracker = ROOT / "Plan/Tracker/Evidence/Wave64" / qa.name
    payloads = []
    for path in (qa, tracker):
        if not path.is_file() or sha256(path) != EVIDENCE_SHA256:
            raise ValueError(f"Kokoro evidence hash mismatch: {path}")
        payloads.append(json.loads(path.read_text(encoding="utf-8")))
    if payloads[0] != payloads[1]:
        raise ValueError("Kokoro evidence mirrors diverged")
    if payloads[0].get("classification") != "KOKORO_C01_DESIGNED_SYNTHETIC_BASELINE_AUTOMATED_ELIGIBLE":
        raise ValueError("Kokoro evidence classification drift")
    if payloads[0].get("acceptance", {}).get("human_playback_review_pass") is not False:
        raise ValueError("Kokoro evidence falsely claims playback review")
    return {"sha256": EVIDENCE_SHA256, "status": payloads[0]["status"]}


def blockers_for_row(row: str, current: list[Any]) -> list[Any]:
    kept = [
        entry
        for entry in current
        if not (isinstance(entry, dict) and entry.get("classification") in STALE_BLOCKERS)
    ]
    human = {
        "classification": "Blocked_Human_Audio_Playback_Review_Missing",
        "scope": "kokoro_selected_candidate",
        "reason": "The selected Kokoro hash passed automated gates and has a prepared request, but no independent human playback record or validated proof exists.",
    }
    production = {
        "classification": "Blocked_Audio_Production_Review_Authority_Missing",
        "scope": "final_production_authority",
        "reason": "A distinct allowlisted final-production authority and review bundle remain absent.",
    }
    if row in {"025", "027", "031"}:
        kept.extend([human, production])
    if row == "026":
        kept.append(
            {
                "classification": "Blocked_Audio_Engine_Authority_Not_Approved",
                "scope": "production_route",
                "reason": "Kokoro has bounded local runtime and automated candidate proof, but production engine authority remains unapproved pending playback and final review.",
            }
        )
    unique = []
    seen = set()
    for entry in kept:
        key = json.dumps(entry, sort_keys=True) if isinstance(entry, dict) else repr(entry)
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    return unique


def update_report(row: str, path: Path, apply: bool) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    spec = ROW_SPECS[row]
    if payload.get("item_id") != spec["item_id"] or payload.get("tracker_id") != spec["tracker_id"]:
        raise ValueError(f"report identity drift: {path}")
    if payload.get("status") not in {spec["before"], spec["after"]} or payload.get("row_complete") is not False:
        raise ValueError(f"report status drift: {path}")
    payload["status"] = spec["after"]
    payload["row_complete"] = False
    payload.setdefault("acceptance_gates", {}).update(GATE_UPDATES)
    payload["blockers"] = blockers_for_row(row, payload.get("blockers", []))
    evidence = payload.setdefault("evidence", [])
    existing = next((entry for entry in evidence if isinstance(entry, dict) and entry.get("path") == EVIDENCE_REL), None)
    if existing:
        existing["sha256"] = EVIDENCE_SHA256
    else:
        evidence.append({"path": EVIDENCE_REL, "sha256": EVIDENCE_SHA256})
    payload.setdefault("runtime", {})["kokoro_c01_audition"] = {
        "engine": "hexgrad/Kokoro-82M",
        "revision": "f3ff3571791e39611d31c381e3a41a3af07b4987",
        "voice": "af_heart",
        "selected_sha256": "a212653c029f5677b97bba8c769186fc11d29b561b4ca19a2344ff294a5fdd56",
        "automated_eligibility_pass": True,
        "human_playback_review_pass": False,
        "production_authority_pass": False,
    }
    payload["next_action"] = NEXT_ACTION
    payload["timestamp"] = datetime.now().astimezone().isoformat(timespec="seconds")
    write_json(path, payload, apply)
    return {"item_id": spec["item_id"], "status": payload["status"], "row_complete": False}


def update_csv(path: Path, key: str, evidence_field: str, apply: bool) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    required = {key, "Status", evidence_field, "Coverage_Audit_Status", "Notes"}
    if required - set(fields):
        raise ValueError(f"{path} is missing required fields")
    specs = {spec[key.lower()]: (row, spec) for row, spec in ROW_SPECS.items()}
    changed = []
    for record in rows:
        record_id = record.get(key)
        if record_id not in specs:
            continue
        row, spec = specs[record_id]
        if record.get("Status") not in {spec["before"], spec["after"]}:
            raise ValueError(f"CSV status drift for {record_id}")
        record["Status"] = spec["after"]
        if "Status_Decision" in fields:
            record["Status_Decision"] = spec["after"]
        record[evidence_field] = append_unique(record.get(evidence_field, ""), EVIDENCE_REL, "; ")
        for tag in COVERAGE_TAGS:
            record["Coverage_Audit_Status"] = append_unique(record.get("Coverage_Audit_Status", ""), tag, "; ")
        record["Notes"] = append_unique(record.get("Notes", ""), NOTE, " | ")
        changed.append({"id": record_id, "status": record["Status"], "row": row})
    if len(changed) != 4:
        raise ValueError(f"{path} matched {len(changed)} rows, expected 4")
    if apply:
        temporary = path.with_name(f".{path.name}.kokoro.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    return changed


def update_voice_profile(path: Path, apply: bool) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = payload.get("character_profiles", [])
    matches = [row for row in profiles if row.get("voice_profile_id") == "voice_C01_pending_authority"]
    if len(matches) != 1:
        raise ValueError("C01 voice profile identity drift")
    profile = matches[0]
    profile.update(
        {
            "identity_policy": "designed_synthetic_voice",
            "reference_ids": [],
            "license": {
                "model": "Apache-2.0",
                "source": "hexgrad/Kokoro-82M",
                "revision": "f3ff3571791e39611d31c381e3a41a3af07b4987",
            },
            "timbre": "af_heart_designed_synthetic_baseline_pending_human_review",
            "accent": "American English (engine-declared; human review pending)",
            "pitch": "pending_human_playback_review",
            "pace_wpm_range": {"minimum": 195, "maximum": 205},
            "delivery_styles": ["focused"],
            "emotion_range": [],
            "intensity_range": ["controlled"],
            "continuity_lines": [
                {
                    "line_id": "L001",
                    "transcript": "We hold the frame steady and move on the beat.",
                    "selected_audio_sha256": "a212653c029f5677b97bba8c769186fc11d29b561b4ca19a2344ff294a5fdd56",
                }
            ],
            "engine_configuration": {
                "engine": "kokoro",
                "package_version": "0.9.4",
                "model_id": "hexgrad/Kokoro-82M",
                "model_revision": "f3ff3571791e39611d31c381e3a41a3af07b4987",
                "model_sha256": "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
                "config_sha256": "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f",
                "voice": "af_heart",
                "voice_sha256": "0ab5709b8ffab19bfd849cd11d98f75b60af7733253ad0d67b12382a102cb4ff",
                "language_code": "a",
                "speed": 1.0,
                "sample_rate_hz": 24000,
                "seed": 64033,
            },
            "audition_evidence": {"path": EVIDENCE_REL, "sha256": EVIDENCE_SHA256},
            "production_authorized": False,
            "blocker": "automated eligibility passed; independent human playback and distinct final-production authority remain required",
        }
    )
    write_json(path, payload, apply)
    return {"voice_profile_id": profile["voice_profile_id"], "identity_policy": profile["identity_policy"], "production_authorized": False}


def update_model_registry(path: Path, apply: bool) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    target_ids = {
        "MODEL-ACQ-1EA0EF3B4ADFC287",
        "MODEL-ACQ-D6C8916C93AD79F1",
        "MODEL-ACQ-E9F0F36F65D3ACC3",
    }
    changed = []
    for record in records:
        if record.get("record_id") not in target_ids:
            continue
        record.update(
            {
                "updated_at": "2026-07-15T13:16:26-05:00",
                "compatibility_status": "bounded_local_runtime_validated",
                "qa_status": "automated_audition_pass_human_review_pending",
                "runtime_validation_status": "bounded_runtime_complete",
                "last_tested_at": "2026-07-15T13:16:26-05:00",
                "evidence_paths": [EVIDENCE_REL],
                "known_issues": ["Independent human playback and distinct final-production authority remain required."],
            }
        )
        changed.append(record["record_id"])
    if set(changed) != target_ids:
        raise ValueError("Kokoro model registry records are missing")
    if apply:
        temporary = path.with_name(f".{path.name}.kokoro.tmp")
        temporary.write_text("\n".join(json.dumps(row, separators=(",", ":")) for row in records) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    return [{"record_id": record_id, "runtime_validation_status": "bounded_runtime_complete"} for record_id in sorted(changed)]


def update_model_queue(path: Path, apply: bool) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    target = {
        "MRQ-ACQ-1EA0EF3B4ADFC287",
        "MRQ-ACQ-D6C8916C93AD79F1",
        "MRQ-ACQ-E9F0F36F65D3ACC3",
    }
    changed = []
    for row in rows:
        if row.get("queue_id") not in target:
            continue
        row["status"] = "bounded_runtime_complete"
        row["evidence_path"] = EVIDENCE_REL
        changed.append(row["queue_id"])
    if set(changed) != target:
        raise ValueError("Kokoro model queue records are missing")
    if apply:
        temporary = path.with_name(f".{path.name}.kokoro.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    return [{"queue_id": queue_id, "status": "bounded_runtime_complete"} for queue_id in sorted(changed)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = {
        "mode": "apply" if args.apply else "dry_run",
        "evidence": verify_evidence(),
        "reports": [update_report(row, ROOT / path, args.apply) for row, path in REPORTS.items()],
        "tracker": [update_csv(ROOT / path, "Tracker_ID", "Evidence_Path", args.apply) for path in TRACKER_PATHS],
        "items": [update_csv(ROOT / path, "Item_ID", "Evidence_Required", args.apply) for path in ITEM_PATHS],
        "voice_profile": update_voice_profile(ROOT / "Plan/10_REGISTRIES/wave30_voice_profile_registry.json", args.apply),
        "model_registry": update_model_registry(ROOT / "Plan/Registries/Models/model_registry.jsonl", args.apply),
        "model_queue": update_model_queue(ROOT / "Plan/Registries/Models/model_runtime_validation_queue.csv", args.apply),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
