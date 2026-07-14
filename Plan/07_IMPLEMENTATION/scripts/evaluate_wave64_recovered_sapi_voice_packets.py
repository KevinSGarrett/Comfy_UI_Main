#!/usr/bin/env python3
"""Evaluate recovered SAPI dialogue with the existing strict Row027 pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
STAMP = "20260714T070304-0500"
TIMESTAMP = "2026-07-14T07:03:04-05:00"
STATUS = "Blocked_Voice_Dialogue_Production_Proof_Missing"
RECOVERY_ROOT = (
    PLAN
    / "Instructions/Operations/Pulled_Back_Artifacts"
    / "wave42_legacy_audio_recovery_20260714T063840-0500"
)
SOURCE_MANIFEST = RECOVERY_ROOT / "sapi_diagnostic/local_sapi_audio_candidate_20260702_034909.json"
RUNTIME_ROOT = ROOT / f"runtime_artifacts/wave64_voice_dialogue_continuity/recovered_sapi_{STAMP}"
EVIDENCE_PATH = PLAN / f"Instructions/QA/Evidence/Wave64/AUDIO_VOICE_DIALOGUE_RECOVERED_SAPI_EVALUATION_{STAMP}.json"
TRACKER_EVIDENCE_PATH = PLAN / f"Tracker/Evidence/AUDIO_VOICE_DIALOGUE_RECOVERED_SAPI_EVALUATION_{STAMP}.json"
PRODUCER = PLAN / "07_IMPLEMENTATION/scripts/produce_wave30_voice_dialogue_continuity_request.py"
EVALUATOR = PLAN / "07_IMPLEMENTATION/scripts/evaluate_wave30_voice_dialogue_continuity.py"
MISSING_PROOF_FILES = (
    "asr_proof.json",
    "speaker_proof.json",
    "emotion_proof.json",
    "playback_review_proof.json",
    "production_runtime_proof.json",
    "production_proof_bundle.json",
)
EXPECTED_LINES = {
    "L001": {
        "character_id": "C01",
        "sha256": "2c4188a284f1b19df16ddad759ddb96a2f9ca96f232f71d5097701136f477ed6",
        "bytes": 137374,
        "dialogue_timing_status": "PASS",
        "overall_status": "BLOCKED",
    },
    "L002": {
        "character_id": "C02",
        "sha256": "583a7ac689846b32634c6813cceeb86391009067a82cf303c77d9d814cc5044e",
        "bytes": 143110,
        "dialogue_timing_status": "FAIL",
        "overall_status": "FAIL",
    },
}
NOTE = (
    "Wave64 Row027 recovered-SAPI evaluation 2026-07-14: two existing character-owned diagnostic "
    "WAV packets were evaluated without regeneration. L001 remained BLOCKED on six missing proof "
    "artifacts; L002 also correctly failed the dialogue-timing gate at 0.844 seconds drift. No "
    "production voice, playback, runtime, or authority claim was made."
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def atomic_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        if handle.getcomptype() != "NONE" or handle.getframerate() <= 0:
            raise ValueError(f"Recovered WAV is not decodable PCM: {path}")
        return handle.getnframes() / handle.getframerate()


def validate_source_manifest(source: dict[str, Any]) -> list[dict[str, Any]]:
    if source.get("production_grade") is not False or source.get("completion_claim_allowed") is not False:
        raise ValueError("Recovered SAPI manifest must remain non-production and non-completing")
    if source.get("quality_label") != "diagnostic_candidate" or source.get("qa", {}).get("pass") is not False:
        raise ValueError("Recovered SAPI manifest must retain failed diagnostic QA")
    lines = source.get("rendered_lines")
    if not isinstance(lines, list) or len(lines) != 2:
        raise ValueError("Recovered SAPI manifest must contain exactly two rendered lines")
    by_id = {line.get("line_id"): line for line in lines if isinstance(line, dict)}
    if set(by_id) != set(EXPECTED_LINES):
        raise ValueError("Recovered SAPI line IDs do not match authority")
    for line_id, expected in EXPECTED_LINES.items():
        line = by_id[line_id]
        wav_path = RECOVERY_ROOT / "sapi_diagnostic" / Path(str(line.get("path"))).name
        if not wav_path.is_file():
            raise FileNotFoundError(wav_path)
        if line.get("character_id") != expected["character_id"]:
            raise ValueError(f"Recovered {line_id} character mismatch")
        if digest(wav_path) != expected["sha256"] or wav_path.stat().st_size != expected["bytes"]:
            raise ValueError(f"Recovered {line_id} WAV authority mismatch")
        if line.get("sha256") != expected["sha256"] or line.get("bytes") != expected["bytes"]:
            raise ValueError(f"Recovered {line_id} manifest binding mismatch")
        line["recovered_wav_path"] = wav_path
    return [by_id[line_id] for line_id in sorted(by_id)]


def build_profile(line: dict[str, Any], source_manifest_sha256: str) -> dict[str, Any]:
    return {
        "voice_profile_id": line["voice_profile_id"],
        "character_id": line["character_id"],
        "status": "diagnostic_placeholder_profile",
        "production_grade": False,
        "selected_sapi_voice": line["selected_sapi_voice"],
        "rights_status": line["voice_profile_rights_status"],
        "source_manifest_sha256": source_manifest_sha256,
        "boundary": "Ownership binding only; not a production voice-profile approval.",
    }


def build_contract(line: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_name": "wave30_voice_dialogue_contract",
        "dialogue_contract_version": 1,
        "lines": [
            {
                "line_id": line["line_id"],
                "character_id": line["character_id"],
                "voice_profile_id": line["voice_profile_id"],
                "text": line["text"],
                "start_time": line["start_seconds"],
                "end_time": line["end_seconds"],
                "emotion": line["emotion"],
                "intensity": "unverified_diagnostic_unknown",
                "sync_required": True,
                "output_file": str(line["recovered_wav_path"]),
            }
        ],
    }


def run(command: list[str], expected_codes: set[int]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode not in expected_codes:
        raise RuntimeError(
            f"Unexpected exit {result.returncode}: {' '.join(command)}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def evaluate_line(line: dict[str, Any], source_sha: str) -> dict[str, Any]:
    line_id = line["line_id"]
    expected = EXPECTED_LINES[line_id]
    packet_root = RUNTIME_ROOT / line["character_id"]
    proof_dir = packet_root / "proofs"
    proof_dir.mkdir(parents=True, exist_ok=False)
    profile_path = packet_root / "voice_profile.json"
    contract_path = packet_root / "dialogue_contract.json"
    request_path = packet_root / "request.json"
    evaluator_path = packet_root / "evidence.json"
    atomic_dump(profile_path, build_profile(line, source_sha))
    atomic_dump(contract_path, build_contract(line))
    run_id = f"wave64_row027_recovered_sapi_{line['character_id']}_{STAMP}"

    producer_command = [
        sys.executable, str(PRODUCER),
        "--voice-profile", str(profile_path),
        "--dialogue-contract", str(contract_path),
        "--proof-dir", str(proof_dir),
        "--output", str(request_path),
        "--run-id", run_id,
        "--production-input",
        "--root", str(ROOT),
    ]
    producer_result = run(producer_command, {0})
    request = load(request_path)
    if request.get("is_synthetic") is not False:
        raise ValueError(f"{line_id} must be marked as real generated diagnostic input")
    if [key for key, value in request["proof_bindings"].items() if value is not None]:
        raise ValueError(f"{line_id} unexpectedly acquired proof bindings")

    evaluator_command = [
        sys.executable, str(EVALUATOR),
        "--input", str(request_path),
        "--output", str(evaluator_path),
        "--root", str(ROOT),
    ]
    evaluator_result = run(evaluator_command, {2})
    evaluated = load(evaluator_path)
    gates = evaluated["gates"]
    if gates["voice_profile_match"]["status"] != "PASS":
        raise ValueError(f"{line_id} voice ownership did not pass")
    if gates["dialogue_timing"]["status"] != expected["dialogue_timing_status"]:
        raise ValueError(f"{line_id} timing status drifted")
    if gates["overall_pass"]["status"] != expected["overall_status"] or evaluated["overall_pass"] is not False:
        raise ValueError(f"{line_id} fail-closed outcome drifted")
    if gates["production_runtime_proof"]["status"] != "BLOCKED" or gates["production_proof_authority"]["status"] != "BLOCKED":
        raise ValueError(f"{line_id} production gates did not remain blocked")
    observed_missing = sorted(
        name for name in MISSING_PROOF_FILES if not (proof_dir / name).exists()
    )
    if observed_missing != sorted(MISSING_PROOF_FILES):
        raise ValueError(f"{line_id} missing-proof set drifted")

    actual_duration = wav_duration(line["recovered_wav_path"])
    contract_duration = float(line["end_seconds"]) - float(line["start_seconds"])
    return {
        "line_id": line_id,
        "character_id": line["character_id"],
        "run_id": run_id,
        "source_wav": rel(line["recovered_wav_path"]),
        "source_wav_sha256": digest(line["recovered_wav_path"]),
        "source_wav_bytes": line["recovered_wav_path"].stat().st_size,
        "contract_duration_seconds": round(contract_duration, 6),
        "actual_duration_seconds": round(actual_duration, 6),
        "duration_delta_seconds": round(abs(actual_duration - contract_duration), 6),
        "voice_profile": rel(profile_path),
        "voice_profile_sha256": digest(profile_path),
        "dialogue_contract": rel(contract_path),
        "dialogue_contract_sha256": digest(contract_path),
        "request": rel(request_path),
        "request_sha256": digest(request_path),
        "evaluation": rel(evaluator_path),
        "evaluation_sha256": digest(evaluator_path),
        "producer_exit_code": producer_result.returncode,
        "evaluator_exit_code": evaluator_result.returncode,
        "missing_proof_files": list(MISSING_PROOF_FILES),
        "gate_statuses": {name: gate["status"] for name, gate in gates.items()},
        "overall_pass": False,
    }


def update_csv(path: Path, id_field: str, row_id: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    matches = [row for row in rows if row.get(id_field) == row_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one {row_id} row in {path}, found {len(matches)}")
    row = matches[0]
    row["Status"] = STATUS
    if "Status_Decision" in row:
        row["Status_Decision"] = STATUS
    if NOTE not in row["Notes"]:
        row["Notes"] = f"{row['Notes']} | {NOTE}".strip(" |")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend_hydration(path: Path, evidence_path: str) -> None:
    marker = "## Wave64 Row027 Recovered SAPI Voice Evaluation"
    current = path.read_text(encoding="utf-8")
    if marker in current:
        return
    block = f"""{marker} - {TIMESTAMP}

`TRK-W64-027` / `ITEM-W64-027` remains `{STATUS}`, now with the recovered SAPI lines evaluated by the existing strict producer/evaluator. The two character-owned packets use the original text and timing windows, an explicit unverified intensity sentinel, and no fabricated proof files. `L001` is `BLOCKED` on the six missing proof classes; `L002` is `FAIL` because its actual 3.244-second audio exceeds the original 2.4-second window by 0.844 seconds, in addition to the missing proofs.

This clears only the missing-input ambiguity. Production voice quality, ASR, speaker identity, emotion/intensity, playback review, runtime proof, and allowlisted bundle authority remain absent. No generation, AWS, EC2, masks, Wave71+, or Jira action occurred.

Next action: map the recovered procedural/returned-runtime foley and AV packet through the existing strict Row028 and Row030 evaluators without regenerating media.

Evidence: `{evidence_path}`.

"""
    path.write_text(block + current, encoding="utf-8")


def append_proof_log(path: Path, evidence_path: str) -> None:
    marker = "row027_recovered_sapi_packets_strictly_evaluated"
    current = path.read_text(encoding="utf-8")
    if marker in current:
        return
    row = (
        f"{TIMESTAMP},64,TRK-W64-027,Evaluated two recovered character-owned SAPI packets with the existing strict voice pipeline,"
        f"{evidence_path},L001 BLOCKED missing 6 proofs; L002 FAIL timing drift 0.844s plus missing proofs,"
        f"blocked,{evidence_path},Map recovered foley and AV packet through Rows 028 and 030; {marker}\n"
    )
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(row)


def update_authority(evidence: dict[str, Any]) -> None:
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/audio_voice_dialogue.json"
    tracker_canonical_path = PLAN / "Tracker/Evidence/Wave64/audio_voice_dialogue.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-027_audio_voice_dialogue.json"
    evidence_rel = rel(EVIDENCE_PATH)
    canonical = load(canonical_path)
    canonical["timestamp"] = TIMESTAMP
    canonical["recovered_sapi_evaluation"] = {
        "evidence": evidence_rel,
        "runtime_root": rel(RUNTIME_ROOT),
        "source_manifest": rel(SOURCE_MANIFEST),
        "character_packet_count": 2,
        "missing_proof_count_per_packet": 6,
        "l001_overall_status": "BLOCKED",
        "l002_overall_status": "FAIL",
        "l002_duration_delta_seconds": 0.844,
        "production_eligible": False,
    }
    canonical["acceptance_gates"].update({
        "recovered_diagnostic_voice_audio_present": True,
        "recovered_diagnostic_voice_audio_evaluated": True,
        "recovered_voice_profile_ownership_passed": True,
        "recovered_l002_timing_passed": False,
        "genuine_production_voice_audio_present": False,
        "genuine_production_asr_speaker_emotion_proofs_present": False,
        "genuine_production_playback_review_present": False,
        "genuine_production_runtime_proof_present": False,
        "production_proof_bundle_allowlisted": False,
        "row_complete": False,
    })
    canonical["runtime"].update({
        "diagnostic_voice_evaluation_count": 2,
        "production_voice_generation_count": 0,
        "production_voice_evaluation_count": 0,
        "generation_executed": False,
        "aws_contacted": False,
        "ec2_started": False,
    })
    canonical["blockers"][0]["reason"] = (
        "Recovered SAPI voice audio has now been evaluated: both character packets lack independent ASR, "
        "speaker, emotion, playback-review, runtime, and production-bundle proofs, and L002 additionally "
        "fails strict dialogue timing by 0.844 seconds."
    )
    canonical["result"] = evidence["result"]
    canonical["reconciliation_evidence"] = evidence_rel
    dump(canonical_path, canonical)
    dump(tracker_canonical_path, canonical)

    report = load(report_path)
    report["timestamp"] = TIMESTAMP
    report["validation"].update({
        "recovered_sapi_packet_evaluation": "pass_fail_closed",
        "recovered_character_packet_count": 2,
        "recovered_missing_proof_count_per_packet": 6,
        "recovered_l001_overall_status": "BLOCKED",
        "recovered_l002_overall_status": "FAIL",
        "recovered_l002_duration_delta_seconds": 0.844,
    })
    report["acceptance_gates"].update({
        "recovered_diagnostic_voice_audio_present": True,
        "recovered_diagnostic_voice_audio_evaluated": True,
        "recovered_voice_profile_ownership_passed": True,
        "recovered_l002_timing_passed": False,
        "genuine_production_voice_audio_present": False,
        "genuine_production_proof_set_present": False,
        "production_proof_bundle_allowlisted": False,
        "final_voice_continuity_certification_allowed": False,
    })
    report["runtime"].update({
        "diagnostic_voice_evaluation_count": 2,
        "production_voice_generation_count": 0,
        "production_voice_evaluation_count": 0,
        "aws_contacted": False,
        "ec2_started": False,
    })
    report["blockers"] = canonical["blockers"]
    for record in report["evidence"]:
        if record.get("path") == rel(canonical_path):
            record["sha256"] = digest(canonical_path)
    report["evidence"].append({"path": evidence_rel, "sha256": digest(EVIDENCE_PATH)})
    report["next_action"] = evidence["next_action"]
    dump(report_path, report)

    for path in (
        PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
        PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
    ):
        update_csv(path, "Tracker_ID", "TRK-W64-027")
    for path in (
        PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    ):
        update_csv(path, "Item_ID", "ITEM-W64-027")
    for name in (
        "CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "NEXT_ACTION.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ):
        prepend_hydration(PLAN / "Instructions/Hydration_Rehydration" / name, evidence_rel)
    append_proof_log(PLAN / "Instructions/Hydration_Rehydration/PROOF_OF_MOVEMENT_LOG.csv", evidence_rel)


def main() -> None:
    if RUNTIME_ROOT.exists() or EVIDENCE_PATH.exists() or TRACKER_EVIDENCE_PATH.exists():
        raise FileExistsError("Row027 recovered SAPI evaluation outputs already exist")
    for path in (SOURCE_MANIFEST, PRODUCER, EVALUATOR):
        if not path.is_file():
            raise FileNotFoundError(path)
    source = load(SOURCE_MANIFEST)
    lines = validate_source_manifest(source)
    source_sha = digest(SOURCE_MANIFEST)
    records = [evaluate_line(line, source_sha) for line in lines]
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W64-AUDIO-VOICE-DIALOGUE-RECOVERED-SAPI-EVALUATION-{STAMP}",
        "timestamp": TIMESTAMP,
        "tracker_id": "TRK-W64-027",
        "item_id": "ITEM-W64-027",
        "status_decision": STATUS,
        "source_manifest": rel(SOURCE_MANIFEST),
        "source_manifest_sha256": source_sha,
        "runtime_root": rel(RUNTIME_ROOT),
        "packet_records": records,
        "adapter_assumptions": {
            "separate_character_owned_packets_required": True,
            "intensity_value": "unverified_diagnostic_unknown",
            "intensity_is_source_truth": False,
            "sync_required_value": True,
            "sync_required_is_conservative_adapter_default": True,
            "original_start_and_end_windows_preserved": True,
            "production_input_flag_meaning": "real_generated_non_synthetic_artifact_only_not_production_acceptance",
        },
        "gate_summary": {
            "diagnostic_packets_evaluated": 2,
            "voice_profile_ownership_passed": 2,
            "dialogue_timing_passed": 1,
            "dialogue_timing_failed": 1,
            "overall_blocked": 1,
            "overall_failed": 1,
            "overall_passed": 0,
            "missing_proofs_per_packet": 6,
            "authority_allowlist_count": 0,
        },
        "boundaries": {
            "existing_audio_reused": True,
            "audio_generated": False,
            "source_audio_modified": False,
            "proofs_fabricated": False,
            "production_voice_claimed": False,
            "playback_review_claimed": False,
            "production_runtime_claimed": False,
            "authority_promotion_executed": False,
            "aws_contacted": False,
            "ec2_started": False,
            "mask_or_wave71_touched": False,
            "jira_mutated": False,
        },
        "result": "blocked_recovered_sapi_evaluated_missing_proofs_and_l002_timing_failure",
        "next_action": "Map the recovered procedural/returned-runtime foley and AV packet through the existing strict Row028 and Row030 evaluators without regenerating media.",
    }
    dump(EVIDENCE_PATH, evidence)
    dump(TRACKER_EVIDENCE_PATH, evidence)
    update_authority(evidence)
    print(json.dumps({
        "status": STATUS,
        "packets_evaluated": 2,
        "l001_overall_status": records[0]["gate_statuses"]["overall_pass"],
        "l002_overall_status": records[1]["gate_statuses"]["overall_pass"],
        "l002_duration_delta_seconds": records[1]["duration_delta_seconds"],
        "proofs_fabricated": False,
        "generation_executed": False,
        "next_action": evidence["next_action"],
    }, indent=2))


if __name__ == "__main__":
    main()
