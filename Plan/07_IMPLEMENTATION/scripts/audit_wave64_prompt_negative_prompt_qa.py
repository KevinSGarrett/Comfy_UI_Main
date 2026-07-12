from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
PROFILES = ROOT / "PromptProfiles"
QA = PLAN / "Instructions/QA/Evidence/Wave64"
HYD = PLAN / "Instructions/Hydration_Rehydration"
TZ = ZoneInfo("America/Chicago")
TRK = "TRK-W64-064"
ITEM = "ITEM-W64-064"
STATUS = "Blocked_Prompt_Profile_Static_And_Runtime_QA_Gaps"
NEXT = "TRK-W64-065 / ITEM-W64-065"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def add(current: str, values: list[str]) -> str:
    entries = [entry.strip() for entry in (current or "").split(";") if entry.strip()]
    for value in values:
        if value not in entries:
            entries.append(value)
    return "; ".join(entries)


def update_csv(path: Path, key: str, expected: str, changes: dict[str, object]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    matched = 0
    for row in rows:
        if row.get(key) != expected:
            continue
        matched += 1
        for field, value in changes.items():
            if field in fields:
                row[field] = add(row.get(field, ""), value) if isinstance(value, list) else str(value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return matched


def prepend(path: Path, block: str) -> None:
    current = path.read_text(encoding="utf-8-sig").lstrip()
    marker = "## Wave64 Row064 Prompt And Negative-Prompt QA"
    if current.startswith(marker):
        next_heading = current.find("\n## ", len(marker))
        current = current[next_heading + 1 :] if next_heading >= 0 else ""
    path.write_text(block.strip() + "\n\n" + current, encoding="utf-8")


def recursive_values(value: object, keys: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys and isinstance(child, str) and child:
                found.append(child)
            found.extend(recursive_values(child, keys))
    elif isinstance(value, list):
        for child in value:
            found.extend(recursive_values(child, keys))
    return found


def clauses(text: str) -> set[str]:
    return {
        re.sub(r"\s+", " ", part.strip().lower())
        for part in re.split(r"[,;\n]+", text)
        if len(re.sub(r"\s+", " ", part.strip())) >= 4
    }


def classify(path: Path, data: dict) -> str:
    patch = data.get("request_patch_values") or {}
    if data.get("matrix_id") and path.name.endswith(".matrix.json"):
        return "certification_matrix"
    if patch.get("upscale_model") and not patch.get("positive_prompt") and not patch.get("negative_prompt"):
        return "non_prompt_operation_profile"
    return "prompt_profile"


def main() -> None:
    canonical = QA / "prompt_negative_prompt_qa.json"
    if canonical.exists():
        prior = load(canonical)
        iso = prior["created_iso"]
        stamp = prior["evidence_id"].removeprefix("PROMPT_NEGATIVE_PROMPT_QA_")
    else:
        now = datetime.now(TZ)
        iso = now.replace(microsecond=0).isoformat()
        stamp = now.strftime("%Y%m%dT%H%M%S%z")
    protocol = PLAN / "Instructions/QA/PROMPT_NEGATIVE_PROMPT_QA_PROTOCOL.md"
    contracts = PLAN / "10_REGISTRIES/wave15_base_generation_prompt_contracts.json"
    compatibility = PLAN / "10_REGISTRIES/wave15_model_family_compatibility_matrix.json"
    base_lanes = PLAN / "10_REGISTRIES/wave15_image_base_lane_registry.json"
    upscale_lanes = PLAN / "10_REGISTRIES/realesrgan_export_candidate_registry.json"
    protocol_text = protocol.read_text(encoding="utf-8-sig")
    compatibility_data = load(compatibility)
    authority_lane_ids = set(recursive_values(load(base_lanes), {"lane_id", "target_lane_id"}))
    authority_lane_ids.update(recursive_values(load(upscale_lanes), {"lane_id", "target_lane_id"}))

    paths = sorted(PROFILES.rglob("*.json"))
    parsed: list[tuple[Path, dict]] = []
    parse_failures = []
    for path in paths:
        try:
            parsed.append((path, load(path)))
        except (OSError, json.JSONDecodeError) as error:
            parse_failures.append({"path": rel(path), "error": type(error).__name__})

    pair_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    records = []
    for path, data in parsed:
        kind = classify(path, data)
        patch = data.get("request_patch_values") or {}
        positive = patch.get("positive_prompt") or data.get("positive_prompt") or ""
        negative = patch.get("negative_prompt") or data.get("negative_prompt") or ""
        lane = data.get("target_lane_id")
        profile_id = data.get("profile_id")
        prompt_bearing = kind == "prompt_profile"
        metadata_complete = all(data.get(key) not in (None, "", [], {}) for key in ("profile_id", "target_lane_id", "purpose", "qa_focus", "expected_outputs"))
        prompt_pair_complete = bool(positive.strip() and negative.strip())
        overlap = sorted(clauses(positive) & clauses(negative)) if prompt_pair_complete else []
        wave71_plus = bool(re.search(r"(?:wave|w)(?:7[1-9]|[89]\d)", (rel(path) + " " + str(profile_id)).lower()))
        runtime_evidence = recursive_values(data, {"runtime_evidence_path", "representative_output_evidence", "visual_qa_evidence_path", "generated_output_evidence"})
        model_asset = patch.get("model_asset")
        family_compatible = (not prompt_bearing) or (bool(lane and lane.startswith("sdxl_")) and (not model_asset or "sdxl" in json.dumps(compatibility_data).lower()))
        request_hash = hashlib.sha256(json.dumps(patch, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        record = {
            "path": rel(path), "sha256": sha(path), "artifact_type": kind,
            "profile_id": profile_id, "target_lane_id": lane, "purpose_present": bool(data.get("purpose")),
            "qa_focus_present": bool(data.get("qa_focus")), "expected_outputs_present": bool(data.get("expected_outputs")),
            "positive_prompt_present": bool(positive.strip()), "negative_prompt_present": bool(negative.strip()),
            "prompt_pair_complete": prompt_pair_complete, "metadata_complete": metadata_complete,
            "exact_positive_negative_clause_overlap": overlap, "lane_authority_present": bool(lane in authority_lane_ids),
            "model_asset": model_asset, "model_family_compatible_static": family_compatible,
            "request_patch_sha256": request_hash, "save_prefix": patch.get("save_prefix"),
            "wave71_plus_named": wave71_plus, "runtime_evidence_paths": runtime_evidence,
            "static_prompt_qa": "pass" if prompt_bearing and metadata_complete and prompt_pair_complete and not overlap and family_compatible else "not_pass",
            "approval_state": "blocked_pending_representative_runtime_output" if prompt_bearing else "not_applicable_non_prompt_artifact",
        }
        records.append(record)
        if prompt_bearing and prompt_pair_complete:
            pair_groups[(positive.strip().lower(), negative.strip().lower())].append(record)

    duplicate_groups = []
    for group in pair_groups.values():
        if len(group) < 2:
            continue
        controlled = (
            len({record["profile_id"] for record in group}) == len(group)
            and len({record["request_patch_sha256"] for record in group}) == len(group)
            and len({record["save_prefix"] for record in group}) == len(group)
            and None not in {record["save_prefix"] for record in group}
        )
        duplicate_groups.append({"count": len(group), "controlled_variant_set": controlled, "paths": [record["path"] for record in group]})

    prompt_records = [record for record in records if record["artifact_type"] == "prompt_profile"]
    non_prompt_records = [record for record in records if record["artifact_type"] != "prompt_profile"]
    missing_prompts = [record for record in prompt_records if not record["prompt_pair_complete"]]
    static_complete = [record for record in prompt_records if record["static_prompt_qa"] == "pass"]
    unmapped_lanes = [record for record in prompt_records if not record["lane_authority_present"]]
    contradictions = [record for record in prompt_records if record["exact_positive_negative_clause_overlap"]]
    wave_deferred = [record for record in prompt_records if record["wave71_plus_named"]]
    runtime_linked = [record for record in prompt_records if record["runtime_evidence_paths"]]
    lane_counts = Counter(record["target_lane_id"] for record in prompt_records)
    tracker_path = PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv"
    with tracker_path.open("r", encoding="utf-8-sig", newline="") as handle:
        tracker_rows = [row for row in csv.DictReader(handle) if row.get("Tracker_ID") == TRK]
    checks = {
        "PNQ-001_row064_tracker_contract_present": len(tracker_rows) == 1 and set(tracker_rows[0]["Validation_Method"].split("|")) == {"prompt_profile_valid", "negative_prompt_check", "intent_alignment", "model_compatibility", "qa_expectations"},
        "PNQ-002_protocol_present": protocol.exists(),
        "PNQ-003_protocol_static_review_areas_present": all(value in protocol_text for value in ("prompt intent clarity", "negative prompt effectiveness", "compatibility with target model family")),
        "PNQ-004_protocol_runtime_approval_rule_present": "representative test output aligns with intent, or pending runtime test is explicitly recorded" in protocol_text,
        "PNQ-005_exact_112_json_files": len(paths) == 112,
        "PNQ-006_all_112_parse": len(parsed) == 112 and not parse_failures,
        "PNQ-007_artifact_types_exact": Counter(record["artifact_type"] for record in records) == {"prompt_profile": 109, "non_prompt_operation_profile": 2, "certification_matrix": 1},
        "PNQ-008_prompt_pairs_complete_105": sum(record["prompt_pair_complete"] for record in prompt_records) == 105,
        "PNQ-009_missing_prompt_links_exact_four": len(missing_prompts) == 4,
        "PNQ-010_prompt_metadata_complete_109": sum(record["metadata_complete"] for record in prompt_records) == 109,
        "PNQ-011_negative_prompts_present_105": sum(record["negative_prompt_present"] for record in prompt_records) == 105,
        "PNQ-012_zero_exact_clause_contradictions": not contradictions,
        "PNQ-013_duplicate_groups_19": len(duplicate_groups) == 19,
        "PNQ-014_all_duplicates_controlled_variants": all(group["controlled_variant_set"] for group in duplicate_groups),
        "PNQ-015_eight_prompt_lane_ids": len(lane_counts) == 8,
        "PNQ-016_lane_authority_16_of_109": sum(record["lane_authority_present"] for record in prompt_records) == 16 and len(unmapped_lanes) == 93,
        "PNQ-017_model_family_static_compatible_109": all(record["model_family_compatible_static"] for record in prompt_records),
        "PNQ-018_wave71_plus_deferred_14": len(wave_deferred) == 14,
        "PNQ-019_no_direct_runtime_evidence_links": not runtime_linked,
        "PNQ-020_no_approval_or_runtime_action": all(record["approval_state"] != "approved" for record in records),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("failed audit invariants: " + ", ".join(failed))

    blockers = [
        {"blocker_id": "PROMPT_PAIR_OR_SOURCE_LINK_MISSING", "count": len(missing_prompts), "paths": [record["path"] for record in missing_prompts], "resolution": "Add explicit source_profile linkage or a complete positive/negative prompt pair; do not infer inherited text."},
        {"blocker_id": "PROMPT_TARGET_LANE_AUTHORITY_MISSING", "count": len(unmapped_lanes), "lane_counts": dict(sorted(Counter(record["target_lane_id"] for record in unmapped_lanes).items())), "resolution": "Register exact lane contracts before compatibility approval."},
        {"blocker_id": "REPRESENTATIVE_RUNTIME_OUTPUT_LINK_MISSING", "count": len(prompt_records), "resolution": "Link per-profile representative output and visual QA evidence, or explicitly record pending runtime; do not approve from static text."},
        {"blocker_id": "WAVE71_PLUS_PROFILE_ACTIVATION_DEFERRED", "count": len(wave_deferred), "paths": [record["path"] for record in wave_deferred], "resolution": "Keep deferred until the explicit Wave71+ activation gate is proven."},
    ]
    stamped = QA / f"PROMPT_NEGATIVE_PROMPT_QA_{stamp}.json"
    mirror = PLAN / "Tracker/Evidence" / stamped.name
    test_log = QA / "prompt_negative_prompt_qa_test_log.json"
    report = PLAN / "Items/Reports/ITEM-W64-064_prompt_negative_prompt_qa.json"
    payload = {
        "schema_version": "1.0", "evidence_id": stamped.stem, "created_iso": iso,
        "wave": 64, "tracker_id": TRK, "item_id": ITEM, "status": STATUS,
        "row_complete": False, "qa_decision": "static_inventory_complete_prompt_approval_fail_closed",
        "inventory_summary": {
            "json_files": len(paths), "parsed": len(parsed), "parse_failures": len(parse_failures),
            "prompt_profiles": len(prompt_records), "non_prompt_artifacts": len(non_prompt_records),
            "non_prompt_operation_profiles": sum(record["artifact_type"] == "non_prompt_operation_profile" for record in records),
            "certification_matrices": sum(record["artifact_type"] == "certification_matrix" for record in records),
            "static_prompt_profiles_pass": len(static_complete), "missing_prompt_pair_or_link": len(missing_prompts),
            "negative_prompts_present": sum(record["negative_prompt_present"] for record in prompt_records),
            "exact_contradictions": len(contradictions), "duplicate_groups": len(duplicate_groups),
            "controlled_duplicate_groups": sum(group["controlled_variant_set"] for group in duplicate_groups),
            "prompt_lane_ids": len(lane_counts), "lane_authority_present": len(prompt_records) - len(unmapped_lanes),
            "lane_authority_missing": len(unmapped_lanes), "wave71_plus_named_deferred": len(wave_deferred),
            "direct_runtime_evidence_links": len(runtime_linked), "approved_profiles": 0,
        },
        "lane_counts": dict(sorted(lane_counts.items())), "profile_index": records,
        "duplicate_prompt_pair_groups": duplicate_groups, "normalized_blockers": blockers,
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": 20, "passed": 20, "failed": 0},
        "safety_boundary": {"generation_executed": False, "profile_approved": False, "profiles_modified": False, "aws_contacted": False, "ec2_started": False, "wave71_activated": False, "mask_or_jira_touched": False},
        "source_hashes": [{"path": rel(path), "sha256": sha(path)} for path in (protocol, contracts, compatibility, base_lanes, upscale_lanes)],
        "next_action": f"Advance to {NEXT} RealVisXL terminal-state proof; keep prompt approvals blocked pending exact profile, lane, and runtime-evidence corrections.",
    }
    evidence_paths = [rel(canonical), rel(stamped), rel(mirror), rel(test_log), rel(report)]
    payload["evidence_paths"] = evidence_paths
    for path in (canonical, stamped, mirror):
        write(path, payload)
    write(test_log, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "result": "pass_audit_blocked_prompt_approval", "checks": payload["checks"], "summary": payload["check_summary"]})
    write(report, {"schema_version": "1.0", "created_iso": iso, "tracker_id": TRK, "item_id": ITEM, "status": STATUS, "inventory_summary": payload["inventory_summary"], "normalized_blockers": blockers, "evidence": evidence_paths, "next_action": payload["next_action"]})

    note = f"Wave64 Row064 {stamp}: parsed 112/112 JSON artifacts; classified 109 prompt profiles, 2 non-prompt operations, and 1 matrix; 105 static prompt pairs pass, 4 lack pair/source linkage, 93 lack lane authority, 109 lack direct runtime evidence, and 14 Wave71+ names remain deferred; 20/20 audit checks pass."
    tags = ["wave64_row064_prompt_inventory_complete", "prompt_approval_blocked", "four_prompt_link_gaps", "ninety_three_lane_authority_gaps", "runtime_alignment_pending", "advance_row065"]
    tracker_changes = [update_csv(path, "Tracker_ID", TRK, {"Status": STATUS, "Status_Decision": payload["qa_decision"], "Evidence_Path": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")]
    item_changes = [update_csv(path, "Item_ID", ITEM, {"Status": STATUS, "Evidence_Required": evidence_paths, "Coverage_Audit_Status": tags, "Notes": [note]}) for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
    if tracker_changes != [1, 1] or item_changes != [1, 1]:
        raise SystemExit(f"row update mismatch: {tracker_changes} {item_changes}")
    block = f"""## Wave64 Row064 Prompt And Negative-Prompt QA - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. The audit parsed all 112 PromptProfiles JSON artifacts and correctly separated 109 prompt profiles from two non-prompt RealESRGAN operations and one certification matrix. Of the prompt profiles, 105 pass deterministic static prompt-pair checks, four lack an explicit pair or source-profile link, zero have exact positive/negative clause contradictions, and all 19 duplicate-pair groups are controlled variants with unique patch payloads and output prefixes. Final approval remains fail-closed because 93 profiles lack exact lane-contract authority, all 109 lack direct representative-output evidence links, and 14 Wave71/Wave72-named profiles remain deferred. No profile was modified or approved, and no generation, AWS, EC2, mask, Jira, or Wave71+ activation occurred.

Next safe local action: `{NEXT}` RealVisXL completed-lane terminal-state proof.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
    for name in ("NEXT_ACTION.md", "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "RESUME_HERE_NEXT_CODEX_SESSION.md", "QA_EVIDENCE_INDEX.md", "RECENT_DECISIONS.md", "BLOCKERS.md", "KNOWN_ISSUES.md"):
        prepend(HYD / name, block)
    proof = HYD / "PROOF_OF_MOVEMENT_LOG.csv"
    if not any(row.get("Task") == TRK and row.get("Evidence_Path") == rel(canonical) for row in csv.DictReader(proof.open("r", encoding="utf-8-sig", newline=""))):
        with proof.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow([iso, "64", TRK, "Audited complete prompt-profile catalog and blocked unsupported approvals.", "; ".join(evidence_paths), "20/20 checks; 112/112 parsed; approval blocked", payload["qa_decision"], rel(canonical), f"Begin {NEXT}."])
    print(json.dumps({"status": STATUS, "summary": payload["inventory_summary"], "blockers": [{"blocker_id": item["blocker_id"], "count": item["count"]} for item in blockers], "checks": payload["check_summary"], "next": NEXT}, indent=2))


if __name__ == "__main__":
    main()
