#!/usr/bin/env python3
"""Validate the frozen expanded forced-alignment and audio-event matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import wave


class ExpansionError(RuntimeError):
    """Raised when the prospective expansion is unsafe or inconsistent."""


SOURCE_IDS = {
    "qwen_l02_english",
    "qwen_l08_spanish",
    "qwen_l10_code_switch",
    "librivox_raven_natural_speaker",
    "room_ambience",
    "cloth_body_shift_foley",
    "speech_foley_ambience_mix",
    "kokoro_qwen_overlap",
}
ALIGNMENT_CASE_IDS = {
    "align_qwen_english",
    "align_natural_english",
    "align_spanish_diagnostic",
    "align_code_switch_diagnostic",
    "align_transcript_mismatch_refusal",
    "align_overlap_refusal",
    "align_ambience_refusal",
    "align_foley_refusal",
}
EVENT_CASE_IDS = {
    "event_room_ambience",
    "event_cloth_body_shift",
    "event_speech_foley_ambience_mix",
    "event_two_speaker_overlap",
}
EXECUTION_ORDER = [
    "verify_exact_sources",
    "run_alignment_calibration_partition",
    "freeze_observed_thresholds",
    "run_alignment_held_out_partition_once",
    "run_event_calibration_partition",
    "freeze_observed_thresholds",
    "run_event_held_out_partition_once",
    "independent_audio_review_if_promotion_eligible",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(plan: dict, repository_root: Path, *, verify_bytes: bool = True) -> list[str]:
    errors: list[str] = []
    if plan.get("schema_version") != "wave64.aqa.forced_alignment_audio_event_expansion.v1":
        errors.append("expansion schema version mismatch")
    if plan.get("status") != "PROSPECTIVE_EXPANDED_MATRIX_FROZEN_EXECUTION_PENDING":
        errors.append("expansion status mismatch")
    sources = plan.get("sources", [])
    by_id = {item.get("source_id"): item for item in sources}
    if len(sources) != 8 or set(by_id) != SOURCE_IDS:
        errors.append("source matrix IDs do not match the frozen set")
    speaker_classes = {item.get("speaker_class") for item in sources}
    if "public_domain_natural_speaker" not in speaker_classes:
        errors.append("a distinct natural-speaker source is required")
    if {item.get("language") for item in sources}.isdisjoint({"es", "en-es"}):
        errors.append("multilingual or code-switch coverage is required")
    alignment_cases = plan.get("alignment_cases", [])
    event_cases = plan.get("event_cases", [])
    if {item.get("case_id") for item in alignment_cases} != ALIGNMENT_CASE_IDS:
        errors.append("alignment case IDs do not match the frozen set")
    if {item.get("case_id") for item in event_cases} != EVENT_CASE_IDS:
        errors.append("event case IDs do not match the frozen set")
    if plan.get("execution_order") != EXECUTION_ORDER:
        errors.append("execution order does not match the frozen sequence")
    cases = alignment_cases + event_cases
    unknown = sorted({item.get("source_id") for item in cases} - set(by_id))
    if unknown:
        errors.append(f"cases reference unknown sources: {unknown}")
    partitions = {item.get("partition") for item in cases}
    if partitions != {"calibration", "held_out"}:
        errors.append("calibration and held-out partitions are both required")
    policies = {item.get("policy") for item in plan.get("alignment_cases", [])}
    if "REQUIRE_MATCH_SCORE_DROP_AT_LEAST_0_15_FROM_MATCHED_SOURCE" not in policies:
        errors.append("transcript-mismatch refusal control is required")
    if "REQUIRE_SINGLE_SPEAKER_ALIGNMENT_AUTHORITY_REFUSAL" not in policies:
        errors.append("overlap refusal control is required")
    authority = plan.get("authority", {})
    allowed_true = {"source_admission", "prospective_case_binding"}
    if any(authority.get(name) is not True for name in allowed_true):
        errors.append("source and prospective binding authority is required")
    if any(value is not False for name, value in authority.items() if name not in allowed_true):
        errors.append("prospective plan exceeds source-admission authority")
    if verify_bytes:
        root = repository_root.resolve()
        for source in sources:
            path = (root / source["relative_path"]).resolve()
            try:
                path.relative_to(root)
                if not path.is_file() or path.is_symlink():
                    raise ExpansionError("missing or symlinked source")
                if path.stat().st_size != source["bytes"] or sha256(path) != source["sha256"]:
                    raise ExpansionError("size or hash mismatch")
                with wave.open(str(path), "rb") as handle:
                    observed = (
                        handle.getframerate(),
                        handle.getnchannels(),
                        handle.getsampwidth(),
                        handle.getnframes(),
                        handle.getcomptype(),
                    )
                expected = (
                    source["sample_rate_hz"],
                    source["channels"],
                    source["sample_width_bytes"],
                    source["frame_count"],
                    "NONE",
                )
                if observed != expected:
                    raise ExpansionError(f"PCM geometry mismatch: {observed}")
            except (KeyError, OSError, EOFError, ValueError, ExpansionError) as exc:
                errors.append(f"source {source.get('source_id')} failed identity: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--repository-root", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    errors = validate(plan, args.repository_root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_FORCED_ALIGNMENT_AUDIO_EVENT_EXPANSION_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
