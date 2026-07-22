#!/usr/bin/env python3
"""Compile accepted Wav2Vec2 IPA spans into bounded viseme control evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any


EXPECTED_CANARY_SHA256 = (
    "404dbd97bbef08b966f6a39434b7256b97e42dc0c1a7c9cd56949f4f48878a93"
)
EXPECTED_MAPPING_SHA256 = (
    "da04cbd728a327f0f7f97923423cf4a60601ad8da0c9f7370f216f94184d7500"
)
EXPECTED_SCHEMA_SHA256 = (
    "1cc7c9b7012326b18be7191977d9c291cd358a1d8081cf7a2f1b6c5d4b07227b"
)
EXPECTED_CANARY_STATUS = "PASS_EXACT_MATRIX_AND_PROCESS_EXIT_CLEANUP"
EXPECTED_REGISTRY_ID = "W64-IPA-VISEME-EN-US-V1"
CONTROL_KEYS = (
    "jaw_open",
    "lip_closure",
    "lip_rounding",
    "lip_spread",
    "tongue_visibility",
)
REQUIRED_CATEGORIES = ("silence", "closure", "plosive", "fricative", "vowel")


class VisemeCompilationError(RuntimeError):
    """Raised when exact lineage, timing, mapping, or authority fails closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_exact_json(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise VisemeCompilationError(f"{label} is absent or unsafe")
    if sha256_file(path) != expected_sha256:
        raise VisemeCompilationError(f"{label} identity mismatch")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VisemeCompilationError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise VisemeCompilationError(f"{label} root must be an object")
    return value


def validate_registry(registry: dict[str, Any]) -> None:
    if registry.get("registry_id") != EXPECTED_REGISTRY_ID:
        raise VisemeCompilationError("mapping registry identity mismatch")
    visemes = registry.get("visemes")
    mapping = registry.get("phoneme_to_viseme")
    coarticulation = registry.get("coarticulation")
    if not isinstance(visemes, dict) or not isinstance(mapping, dict):
        raise VisemeCompilationError("mapping registry tables are absent")
    if not isinstance(coarticulation, dict):
        raise VisemeCompilationError("coarticulation policy is absent")
    for viseme_id, spec in visemes.items():
        if not isinstance(viseme_id, str) or not isinstance(spec, dict):
            raise VisemeCompilationError("viseme record is invalid")
        if not isinstance(spec.get("category"), str):
            raise VisemeCompilationError(f"viseme category is absent: {viseme_id}")
        for key in CONTROL_KEYS:
            value = spec.get(key)
            if not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
                raise VisemeCompilationError(f"viseme control is invalid: {viseme_id}.{key}")
    if "SIL" not in visemes:
        raise VisemeCompilationError("SIL viseme is required")
    for phoneme, viseme_id in mapping.items():
        if not isinstance(phoneme, str) or not phoneme or viseme_id not in visemes:
            raise VisemeCompilationError("phoneme mapping references an unknown viseme")
    for key in ("attack_seconds", "release_seconds"):
        value = coarticulation.get(key)
        if not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 0.2:
            raise VisemeCompilationError(f"coarticulation {key} is invalid")


def controls_for(registry: dict[str, Any], viseme_id: str) -> dict[str, float]:
    spec = registry["visemes"][viseme_id]
    return {key: float(spec[key]) for key in CONTROL_KEYS}


def make_event(
    *,
    index: int,
    source_kind: str,
    phoneme: str,
    viseme: str,
    category: str,
    start_sample: int,
    end_sample: int,
    sample_rate: int,
    posterior: float,
    controls: dict[str, float],
) -> dict[str, Any]:
    return {
        "event_index": index,
        "source_kind": source_kind,
        "phoneme": phoneme,
        "viseme": viseme,
        "category": category,
        "start_sample": start_sample,
        "end_sample": end_sample,
        "start_seconds": start_sample / sample_rate,
        "end_seconds": end_sample / sample_rate,
        "posterior": posterior,
        "controls": controls,
    }


def compile_events(
    fixture: dict[str, Any], registry: dict[str, Any]
) -> tuple[list[dict[str, Any]], int, int]:
    sample_rate = fixture.get("input_sample_rate_hz")
    duration_seconds = fixture.get("duration_seconds")
    spans = fixture.get("phoneme_spans")
    if not isinstance(sample_rate, int) or sample_rate <= 0:
        raise VisemeCompilationError("fixture sample rate is invalid")
    if not isinstance(duration_seconds, (int, float)) or duration_seconds <= 0:
        raise VisemeCompilationError("fixture duration is invalid")
    if not isinstance(spans, list) or not spans:
        raise VisemeCompilationError("fixture phoneme spans are absent")
    total_samples = round(float(duration_seconds) * sample_rate)
    mapping = registry["phoneme_to_viseme"]
    silence_controls = controls_for(registry, "SIL")
    events: list[dict[str, Any]] = []
    previous_end = 0
    for span in spans:
        if not isinstance(span, dict):
            raise VisemeCompilationError("phoneme span is invalid")
        token = span.get("token")
        if token not in mapping:
            raise VisemeCompilationError(f"unmapped IPA phoneme: {token!r}")
        start = round(float(span.get("start_seconds", math.nan)) * sample_rate)
        end = round(float(span.get("end_seconds", math.nan)) * sample_rate)
        posterior = float(span.get("posterior", math.nan))
        if start < previous_end or end <= start or end > total_samples:
            raise VisemeCompilationError("phoneme intervals are not monotonic and bounded")
        if not math.isfinite(posterior) or not 0.0 <= posterior <= 1.0:
            raise VisemeCompilationError("phoneme posterior is invalid")
        if start > previous_end:
            events.append(
                make_event(
                    index=len(events),
                    source_kind="inferred_silence_gap",
                    phoneme="<sil>",
                    viseme="SIL",
                    category="silence",
                    start_sample=previous_end,
                    end_sample=start,
                    sample_rate=sample_rate,
                    posterior=0.0,
                    controls=silence_controls,
                )
            )
        viseme_id = mapping[token]
        spec = registry["visemes"][viseme_id]
        events.append(
            make_event(
                index=len(events),
                source_kind="aligned_phoneme",
                phoneme=token,
                viseme=viseme_id,
                category=spec["category"],
                start_sample=start,
                end_sample=end,
                sample_rate=sample_rate,
                posterior=posterior,
                controls=controls_for(registry, viseme_id),
            )
        )
        previous_end = end
    if previous_end < total_samples:
        events.append(
            make_event(
                index=len(events),
                source_kind="inferred_silence_gap",
                phoneme="<sil>",
                viseme="SIL",
                category="silence",
                start_sample=previous_end,
                end_sample=total_samples,
                sample_rate=sample_rate,
                posterior=0.0,
                controls=silence_controls,
            )
        )
    return events, sample_rate, total_samples


def frame_controls(
    events: list[dict[str, Any]],
    registry: dict[str, Any],
    sample_rate: int,
    total_samples: int,
    fps: int,
) -> list[dict[str, Any]]:
    if fps <= 0 or fps > 240:
        raise VisemeCompilationError("frame rate is outside the bounded range")
    attack_limit = round(float(registry["coarticulation"]["attack_seconds"]) * sample_rate)
    release_limit = round(float(registry["coarticulation"]["release_seconds"]) * sample_rate)
    count = math.ceil(total_samples * fps / sample_rate)
    output = []
    event_index = 0
    for frame_index in range(count):
        center = min(total_samples - 1, math.floor((frame_index + 0.5) * sample_rate / fps))
        while center >= events[event_index]["end_sample"] and event_index + 1 < len(events):
            event_index += 1
        current = events[event_index]
        if not current["start_sample"] <= center < current["end_sample"]:
            raise VisemeCompilationError("frame center has no single owning event")
        duration = current["end_sample"] - current["start_sample"]
        attack = min(attack_limit, duration // 2)
        release = min(release_limit, duration // 2)
        weights = {current["viseme"]: 1.0}
        if event_index > 0 and attack > 0 and center < current["start_sample"] + attack:
            alpha = (center - current["start_sample"]) / attack
            previous = events[event_index - 1]["viseme"]
            weights = {previous: 1.0 - alpha, current["viseme"]: alpha}
        elif (
            event_index + 1 < len(events)
            and release > 0
            and center >= current["end_sample"] - release
        ):
            alpha = (center - (current["end_sample"] - release)) / release
            following = events[event_index + 1]["viseme"]
            weights = {current["viseme"]: 1.0 - alpha, following: alpha}
        combined: dict[str, float] = {}
        for viseme_id, weight in weights.items():
            combined[viseme_id] = combined.get(viseme_id, 0.0) + weight
        total_weight = sum(combined.values())
        combined = {key: value / total_weight for key, value in sorted(combined.items())}
        controls = {
            key: sum(controls_for(registry, viseme)[key] * weight for viseme, weight in combined.items())
            for key in CONTROL_KEYS
        }
        output.append(
            {
                "frame_index": frame_index,
                "center_sample": center,
                "primary_viseme": max(combined, key=combined.get),
                "viseme_weights": combined,
                "controls": controls,
            }
        )
    return output


def compile_fixture(
    receipt: dict[str, Any],
    registry: dict[str, Any],
    fixture_id: str,
    fps: int,
    *,
    receipt_binding: dict[str, Any] | None = None,
    mapping_binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_registry(registry)
    if receipt.get("status") != EXPECTED_CANARY_STATUS:
        raise VisemeCompilationError("source canary did not pass the exact matrix")
    if receipt.get("authority", {}).get("exact_matrix_alignment") is not True:
        raise VisemeCompilationError("source canary lacks exact-matrix authority")
    fixtures = receipt.get("fixtures")
    if not isinstance(fixtures, list):
        raise VisemeCompilationError("source fixture list is absent")
    matches = [item for item in fixtures if item.get("fixture_id") == fixture_id]
    if len(matches) != 1:
        raise VisemeCompilationError("exactly one requested fixture is required")
    fixture = matches[0]
    if fixture.get("expect_speech") is not True or fixture.get("speech_gate") is not True or fixture.get("passed") is not True:
        raise VisemeCompilationError("requested fixture lacks accepted speech authority")
    events, sample_rate, total_samples = compile_events(fixture, registry)
    frames = frame_controls(events, registry, sample_rate, total_samples, fps)
    categories = {category: any(event["category"] == category for event in events) for category in REQUIRED_CATEGORIES}
    categories["rapid_transition"] = any(
        event["source_kind"] == "aligned_phoneme"
        and event["end_sample"] - event["start_sample"] <= round(sample_rate * 0.05)
        for event in events
    )
    timeline_complete = (
        events[0]["start_sample"] == 0
        and events[-1]["end_sample"] == total_samples
        and all(left["end_sample"] == right["start_sample"] for left, right in zip(events, events[1:], strict=False))
    )
    frame_weights_valid = all(abs(sum(frame["viseme_weights"].values()) - 1.0) <= 1e-9 for frame in frames)
    gates = {
        "source_canary_pass": True,
        "requested_fixture_speech_gate_pass": True,
        "all_phonemes_mapped": True,
        "sample_timeline_complete": timeline_complete,
        "sample_timeline_nonoverlap": timeline_complete,
        "positive_bounded_intervals": all(event["end_sample"] > event["start_sample"] for event in events),
        "required_category_coverage": all(categories.values()),
        "single_owner_frame_centers": [frame["frame_index"] for frame in frames] == list(range(len(frames))),
        "coarticulation_weights_normalized": frame_weights_valid,
        "deterministic_replay": True,
    }
    if not all(gates.values()):
        raise VisemeCompilationError(f"viseme compilation gates failed: {gates}")
    return {
        "schema_version": "wave64.phoneme_viseme_compilation.v1",
        "compiler_version": "wave64_ipa_viseme_compiler_v1",
        "status": "PASS_EXACT_ACCEPTED_ALIGNMENT_TO_VISEME_CONTROLS",
        "input": {
            "fixture_id": fixture_id,
            "canary_status": receipt["status"],
            "canary_receipt": receipt_binding or {},
            "fixture_audio_sha256": fixture.get("sha256"),
            "transcript": receipt.get("transcript"),
            "phoneme_span_count": len(fixture["phoneme_spans"]),
        },
        "mapping": {
            "registry_id": registry["registry_id"],
            "registry_version": registry["registry_version"],
            "registry": mapping_binding or {},
            "source_alphabet": registry["source_alphabet"],
        },
        "timing": {
            "sample_rate_hz": sample_rate,
            "total_samples": total_samples,
            "fps": fps,
            "frame_count": len(frames),
        },
        "events": events,
        "frame_controls": frames,
        "coverage": categories,
        "gates": gates,
        "authority": {
            "exact_accepted_alignment_input": True,
            "sample_accurate_viseme_compilation": True,
            "single_owner_frame_control_compilation": True,
            "general_phoneme_inventory": False,
            "rendered_lip_sync": False,
            "identity_preservation": False,
            "audio_visual_sync": False,
            "operational_activation": False,
            "product_promotion": False,
        },
    }


def canonical_sha256(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise VisemeCompilationError("immutable output already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canary-receipt", type=Path, required=True)
    parser.add_argument("--mapping-registry", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--fixture-id", choices=("clean_speech", "speech_plus_tone"), required=True)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = load_exact_json(args.canary_receipt, EXPECTED_CANARY_SHA256, "canary receipt")
        registry = load_exact_json(args.mapping_registry, EXPECTED_MAPPING_SHA256, "mapping registry")
        schema = load_exact_json(args.schema, EXPECTED_SCHEMA_SHA256, "output schema")
        receipt_binding = {"path": str(args.canary_receipt), "sha256": EXPECTED_CANARY_SHA256}
        mapping_binding = {"path": str(args.mapping_registry), "sha256": EXPECTED_MAPPING_SHA256}
        first = compile_fixture(receipt, registry, args.fixture_id, args.fps, receipt_binding=receipt_binding, mapping_binding=mapping_binding)
        second = compile_fixture(receipt, registry, args.fixture_id, args.fps, receipt_binding=receipt_binding, mapping_binding=mapping_binding)
        if canonical_sha256(first) != canonical_sha256(second):
            raise VisemeCompilationError("deterministic replay mismatch")
        from jsonschema.validators import validator_for

        validator = validator_for(schema)
        validator.check_schema(schema)
        validator(schema).validate(first)
        write_json_new(args.output, first)
    except Exception as exc:  # noqa: BLE001 - fail-closed CLI retains concise blocker.
        print(json.dumps({"status": "FAIL_VISEME_COMPILATION", "error": str(exc)}, ensure_ascii=True))
        return 2
    print(json.dumps({"status": first["status"], "output": str(args.output), "sha256": sha256_file(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
