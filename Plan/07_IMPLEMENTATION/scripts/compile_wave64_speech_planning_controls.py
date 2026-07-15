from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
HASH_RE = re.compile(r"[a-f0-9]{64}")
ABBREVIATIONS = {
    "dr.": "Doctor",
    "mr.": "Mister",
    "mrs.": "Missus",
    "ms.": "Ms",
    "st.": "Saint",
    "vs.": "versus",
}
SMALL_NUMBERS = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen",
]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
ORDINALS = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh",
    8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth", 13: "thirteenth",
    14: "fourteenth", 15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
    19: "nineteenth", 20: "twentieth", 21: "twenty-first", 22: "twenty-second", 23: "twenty-third",
    24: "twenty-fourth", 25: "twenty-fifth", 26: "twenty-sixth", 27: "twenty-seventh",
    28: "twenty-eighth", 29: "twenty-ninth", 30: "thirtieth", 31: "thirty-first",
}


class PlanningError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(json_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise PlanningError(f"JSON root must be an object: {path}")
    return value


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def number_to_words(number: int) -> str:
    if number < 0 or number > 9999:
        raise PlanningError(f"number outside deterministic normalization range: {number}")
    if number < 20:
        return SMALL_NUMBERS[number]
    if number < 100:
        tens, ones = divmod(number, 10)
        return TENS[tens] + (f"-{SMALL_NUMBERS[ones]}" if ones else "")
    if number < 1000:
        hundreds, remainder = divmod(number, 100)
        return f"{SMALL_NUMBERS[hundreds]} hundred" + (f" {number_to_words(remainder)}" if remainder else "")
    thousands, remainder = divmod(number, 1000)
    return f"{number_to_words(thousands)} thousand" + (f" {number_to_words(remainder)}" if remainder else "")


def normalize_text(text: str, language: str) -> dict[str, Any]:
    if language != "en-US":
        raise PlanningError(f"unsupported normalization language: {language}")
    original = text
    normalized = unicodedata.normalize("NFC", text).strip()
    transforms: list[dict[str, str]] = []

    def apply(pattern: str, replacement: Any, kind: str, flags: int = 0) -> None:
        nonlocal normalized
        before = normalized
        normalized = re.sub(pattern, replacement, normalized, flags=flags)
        if normalized != before:
            transforms.append({"kind": kind, "before": before, "after": normalized})

    apply(r"\s+", " ", "whitespace")
    apply(r"[\u2018\u2019]", "'", "apostrophe")
    apply(r"[\u201c\u201d]", '"', "quotation")
    apply(r"[\u2013\u2014]", "-", "dash")
    for abbreviation, expansion in ABBREVIATIONS.items():
        apply(rf"(?<![A-Za-z]){re.escape(abbreviation)}", expansion, "abbreviation", re.IGNORECASE)
    apply(r"&", " and ", "symbol")
    apply(r"%", " percent", "symbol")
    def replace_date(match: re.Match[str]) -> str:
        month, day, year = (int(value) for value in match.groups())
        if not 1 <= month <= 12 or day not in ORDINALS:
            raise PlanningError(f"invalid en-US date: {match.group(0)}")
        return f"{MONTHS[month]} {ORDINALS[day]}, {number_to_words(year)}"

    apply(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)", replace_date, "date")
    apply(r"(?<![\w.])(\d{1,4})(?![\w.])", lambda match: number_to_words(int(match.group(1))), "integer")
    apply(r"\s+", " ", "whitespace")

    tokens = [match.group(0).casefold() for match in TOKEN_RE.finditer(normalized)]
    if not tokens:
        raise PlanningError("normalized text has no pronounceable tokens")
    return {
        "original_text": original,
        "original_sha256": sha256_bytes(original.encode("utf-8")),
        "normalized_text": normalized,
        "normalized_sha256": sha256_bytes(normalized.encode("utf-8")),
        "language": language,
        "tokens": tokens,
        "token_sha256": sha256_bytes("\n".join(tokens).encode("utf-8")),
        "transforms": transforms,
        "reversible": True,
        "reversal_authority": "original_text_and_original_sha256",
        "casing_policy": "preserve_source_except_explicit_expansions",
    }


def compile_pronunciations(tokens: list[str], lexicon: dict[str, Any], language: str) -> dict[str, Any]:
    if lexicon.get("language") != language:
        raise PlanningError("pronunciation lexicon language differs from line language")
    entries = lexicon.get("entries")
    if not isinstance(entries, dict):
        raise PlanningError("pronunciation lexicon entries must be an object")
    pronunciations = []
    unknown = []
    ambiguous = []
    for index, token in enumerate(tokens):
        options = entries.get(token)
        if not isinstance(options, list) or not options:
            unknown.append(token)
            continue
        if len(options) != 1:
            ambiguous.append(token)
            continue
        phonemes = options[0]
        if not isinstance(phonemes, list) or not phonemes or not all(isinstance(item, str) and item for item in phonemes):
            raise PlanningError(f"invalid phoneme entry for token: {token}")
        pronunciations.append({"token_index": index, "token": token, "phonemes": phonemes, "stress_encoded": True})
    blockers = [f"unknown pronunciation: {token}" for token in sorted(set(unknown))]
    blockers.extend(f"ambiguous pronunciation: {token}" for token in sorted(set(ambiguous)))
    return {
        "lexicon_id": lexicon.get("registry_id"),
        "lexicon_sha256": sha256_bytes(json_bytes(lexicon)),
        "pronunciations": pronunciations,
        "unknown_tokens": sorted(set(unknown)),
        "ambiguous_tokens": sorted(set(ambiguous)),
        "pass": not blockers,
        "blockers": blockers,
        "fallback_policy": "fail_closed_no_unreviewed_g2p_guess",
    }


def compile_performance(request: dict[str, Any]) -> dict[str, Any]:
    required = ("emotion_class", "delivery_style", "intensity", "pace_wpm", "emphasis", "articulation")
    missing = [field for field in required if field not in request]
    if missing:
        raise PlanningError(f"performance controls missing: {', '.join(missing)}")
    pace = float(request["pace_wpm"])
    if pace <= 0:
        raise PlanningError("pace_wpm must be positive")
    unsupported = [
        "emotion_class",
        "delivery_style",
        "intensity",
        "pace_wpm",
        "emphasis",
        "articulation",
        "pauses",
        "breaths",
        "vocal_effort",
    ]
    return {
        "emotion_class": request["emotion_class"],
        "delivery_style": request["delivery_style"],
        "intensity": request["intensity"],
        "pace_wpm": pace,
        "emphasis": request["emphasis"],
        "articulation": request["articulation"],
        "pauses": request.get("pauses", []),
        "breaths": request.get("breaths", []),
        "vocal_effort": request.get("vocal_effort", "neutral"),
        "taxonomy_conflation": False,
        "unsupported_engine_controls": unsupported,
        "engine_mapping_status": "structured_plan_compiled_adapter_mapping_pending",
        "pass": True,
    }


def compile_duration(tokens: list[str], pace_wpm: float, target_seconds: float, tolerance_seconds: float) -> dict[str, Any]:
    if target_seconds <= 0 or tolerance_seconds < 0:
        raise PlanningError("duration target must be positive and tolerance non-negative")
    estimate = len(tokens) * 60.0 / pace_wpm
    delta = estimate - target_seconds
    ratio = target_seconds / estimate
    if abs(delta) <= tolerance_seconds:
        decision = "native_timing"
        pass_value = True
        blocker = None
    elif 0.9 <= ratio <= 1.1:
        decision = "bounded_rate_correction_pending_runtime_proof"
        pass_value = True
        blocker = None
    else:
        decision = "shot_contract_blocked_or_alternate_engine_required"
        pass_value = False
        blocker = "estimated speech duration exceeds the no-truncation correction envelope"
    return {
        "token_count": len(tokens),
        "pace_wpm": pace_wpm,
        "estimated_seconds": round(estimate, 6),
        "target_seconds": target_seconds,
        "tolerance_seconds": tolerance_seconds,
        "delta_seconds": round(delta, 6),
        "native_to_target_ratio": round(ratio, 6),
        "decision": decision,
        "spoken_content_trim_allowed": False,
        "pass": pass_value,
        "blockers": [blocker] if blocker else [],
    }


def evaluate_tournament(adapter_registry: dict[str, Any]) -> dict[str, Any]:
    dimensions = [
        "character_match",
        "language_support",
        "duration_accuracy",
        "delivery_style",
        "audio_quality",
        "voice_identity",
        "runtime_performance",
        "failure_rate",
    ]
    entries = []
    for adapter in adapter_registry.get("adapters", []):
        checks = {
            "load_proven": adapter.get("runtime_status") == "load_proven",
            "license_declared": bool(adapter.get("license", {}).get("id")),
            "content_based_suppression_false": adapter.get("content_based_suppression") is False,
            "candidate_generation_proven": adapter.get("capabilities", {}).get("candidate_generation_proven") is True,
        }
        score = sum(25 for value in checks.values() if value)
        entries.append(
            {
                "adapter_id": adapter.get("adapter_id"),
                "engine_family": adapter.get("engine_family"),
                "checks": checks,
                "score": score,
                "runtime_benchmark_eligible": all(checks.values()),
                "benchmark_dimensions": {dimension: None for dimension in dimensions},
                "missing_runtime_dimensions": dimensions,
                "production_ready": False,
            }
        )
    eligible = [entry for entry in entries if entry["runtime_benchmark_eligible"]]
    blockers = []
    if len(eligible) < 2:
        blockers.append("fewer than two engines have hash-bound candidate-generation runtime proof")
    return {
        "hard_gate_weights": {"load_proven": 25, "license_declared": 25, "content_based_suppression_false": 25, "candidate_generation_proven": 25},
        "required_benchmark_dimensions": dimensions,
        "entries": entries,
        "eligible_engine_count": len(eligible),
        "winner": None,
        "universal_engine_assumed": False,
        "comparative_tournament_pass": len(eligible) >= 2,
        "blockers": blockers,
    }


def compile_controls(root: Path, request_path: Path, adapter_path: Path, lexicon_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    request = load_json(request_path)
    adapters = load_json(adapter_path)
    lexicon = load_json(lexicon_path)
    normalized = normalize_text(str(request.get("text", "")), str(request.get("language", "")))
    pronunciation = compile_pronunciations(normalized["tokens"], lexicon, normalized["language"])
    performance = compile_performance(request)
    duration = compile_duration(
        normalized["tokens"],
        performance["pace_wpm"],
        float(request["duration_target_seconds"]),
        float(request.get("duration_tolerance_seconds", 0.08)),
    )
    tournament = evaluate_tournament(adapters)
    request_sha = sha256_file(request_path)
    plan = {
        "schema_version": "1.0",
        "plan_id": f"W64-SPEECH-PLAN-{request_sha[:16].upper()}",
        "created_at": now_iso(),
        "request": {"path": display(root, request_path), "sha256": request_sha},
        "line_id": request["line_id"],
        "character_id": request["character_id"],
        "voice_profile_id": request["voice_profile_id"],
        "normalization": normalized,
        "pronunciation": pronunciation,
        "performance": performance,
        "duration": duration,
        "generation_executed": False,
        "spoken_content_trimmed": False,
        "production_ready": False,
        "content_based_suppression": False,
    }
    decisions = {
        "TRK-W64-118": {"status": "Implemented_Tournament_Control_Blocked_Comparative_Runtime_Missing", "pass_like": False, "blockers": tournament["blockers"]},
        "TRK-W64-119": {"status": "Implemented_Deterministic_Text_Normalization_Pass", "pass_like": True, "blockers": []},
        "TRK-W64-120": {"status": "Implemented_Pronunciation_Lexicon_Pass" if pronunciation["pass"] else "Blocked_Pronunciation_Authority", "pass_like": pronunciation["pass"], "blockers": pronunciation["blockers"]},
        "TRK-W64-121": {"status": "Implemented_Separated_Performance_Planner_Pass", "pass_like": performance["pass"], "blockers": []},
        "TRK-W64-122": {"status": "Implemented_No_Truncation_Duration_Planner_Pass" if duration["pass"] else "Blocked_Duration_Shot_Contract", "pass_like": duration["pass"], "blockers": duration["blockers"]},
    }
    evidence = {
        "schema_version": "1.0",
        "artifact_type": "wave64_speech_planning_controls_evidence",
        "created_at": now_iso(),
        "classification": "W64_ROWS118_122_CONTROLS_PARTIAL_FAIL_CLOSED",
        "inputs": {
            "request": {"path": display(root, request_path), "sha256": request_sha},
            "adapter_registry": {"path": display(root, adapter_path), "sha256": sha256_file(adapter_path)},
            "lexicon_registry": {"path": display(root, lexicon_path), "sha256": sha256_file(lexicon_path)},
        },
        "tournament": tournament,
        "plan": plan,
        "decisions": decisions,
        "boundaries": {
            "candidate_generated": False,
            "comparative_tournament_complete": False,
            "playback_review_complete": False,
            "production_ready": False,
            "rejected_candidate_rerun": False,
            "content_based_suppression": False,
        },
    }
    return plan, evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--adapter-registry", type=Path, required=True)
    parser.add_argument("--lexicon-registry", type=Path, required=True)
    parser.add_argument("--out-plan", type=Path, required=True)
    parser.add_argument("--out-evidence", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    resolve = lambda value: value.resolve() if value.is_absolute() else (root / value).resolve()
    plan, evidence = compile_controls(root, resolve(args.request), resolve(args.adapter_registry), resolve(args.lexicon_registry))
    out_plan = resolve(args.out_plan)
    out_evidence = resolve(args.out_evidence)
    write_json_atomic(out_plan, plan)
    evidence["plan_artifact"] = {"path": display(root, out_plan), "sha256": sha256_file(out_plan)}
    write_json_atomic(out_evidence, evidence)
    print(json.dumps({"classification": evidence["classification"], "plan": display(root, out_plan), "evidence": display(root, out_evidence)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
