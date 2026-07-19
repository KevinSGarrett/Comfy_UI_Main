#!/usr/bin/env python3
"""Fail-closed Row089 visual material recognition compiler.

Compiles fixture scene-registry, classifier, texture, and contact packets into
a content-addressed material-decision manifest. Production completion remains
blocked until Rows085/088, calibrated material benchmarks, runtime receipts,
and combined frame/contact/audio review authorities are satisfied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_MATERIAL_CLASSES = {
    "hardwood",
    "carpet",
    "tile",
    "skin",
    "fabric",
    "leather",
    "metal",
    "glass",
}

# Governed aliases only; silent taxonomy substitution is rejected.
GOVERNED_ALIASES = {
    "wood_floor": "hardwood",
    "cotton_fabric": "fabric",
}

BROADER_CLASS_MAP = {
    "hardwood": "hard_floor",
    "tile": "hard_floor",
    "carpet": "soft_floor",
    "fabric": "textile",
    "leather": "textile",
    "skin": "organic_surface",
    "metal": "rigid_object",
    "glass": "rigid_object",
}

ALLOWED_BROADER_CLASSES = set(BROADER_CLASS_MAP.values()) | {"unknown_material"}

ALLOWED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "manifest_id",
    "revision",
    "run_id",
    "scene_id",
    "shot_id",
    "take_id",
    "is_synthetic",
    "video_sha256",
    "timeline_binding",
    "scene_registry_binding",
    "classifier_stack",
    "dependency_authority",
    "runtime_authority",
    "material_decisions",
    "thresholds",
    "provenance",
}

ALLOWED_TIMELINE_BINDING_FIELDS = {
    "timeline_id",
    "timeline_sha256",
    "frame_count",
    "frame_rate",
    "frame_time_origin_seconds",
}

ALLOWED_SCENE_REGISTRY_BINDING_FIELDS = {
    "scene_registry_id",
    "scene_registry_sha256",
    "frame_span_id",
    "entity_region_count",
}

ALLOWED_CLASSIFIER_STACK_FIELDS = {
    "classifier_id",
    "weights_sha256",
    "preprocessing_sha256",
    "class_map_sha256",
    "revision",
}

ALLOWED_DECISION_FIELDS = {
    "decision_id",
    "frame_index",
    "pts",
    "owner_id",
    "track_id",
    "region_id",
    "region_kind",
    "observed_class",
    "broader_class",
    "decision_state",
    "confidence",
    "ambiguity",
    "abstention_reason",
    "evidence_sources",
    "texture_evidence",
    "contact_context",
    "fusion",
}

ALLOWED_REGION_KINDS = {
    "surface",
    "object",
    "clothing_region",
    "contact_region",
    "skin_region",
}

ALLOWED_DECISION_STATES = {"observed_class", "broader_class", "abstain"}
ALLOWED_AMBIGUITY = {"none", "low", "medium", "high", "unsupported"}
ALLOWED_EVIDENCE_KINDS = {
    "scene_registry",
    "material_classifier",
    "texture_evidence",
    "contact_context",
}
ALLOWED_TEXTURE_FIELDS = {
    "feature_digest_sha256",
    "resolution_px",
    "crop_authority",
    "quality_score",
}
ALLOWED_CONTACT_FIELDS = {
    "contact_id",
    "source_owner_id",
    "target_owner_id",
    "ownership_state",
}
ALLOWED_OWNERSHIP_STATES = {"trusted", "candidate", "unknown", "absent"}
ALLOWED_FUSION_FIELDS = {
    "independent_source_count",
    "agreeing_source_count",
    "disagreement",
    "fusion_rule",
}
ALLOWED_THRESHOLD_FIELDS = {
    "min_class_confidence",
    "min_agreeing_independent_sources",
    "max_abstention_ratio",
    "min_texture_quality",
}
SHA256_HEX_CHARS = set("0123456789abcdef")
CONTENT_ADDRESSED_EXCLUDED_FIELDS = frozenset({"created_at", "manifest_sha256"})
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_DIR = (
    REPO_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Wave64" / "fixtures" / "row089"
)

# Checked-in fixture packets bound into the non-production synthetic ledger.
SYNTHETIC_BENCHMARK_FIXTURE_PACKETS: tuple[dict[str, str], ...] = (
    {
        "name": "materials_all_eight_required.json",
        "role": "required_materials",
        "case_id": "materials_all_eight_required",
    },
    {
        "name": "case_occlusion_abstain.json",
        "role": "occlusion_abstain",
        "case_id": "occlusion_abstain",
    },
    {
        "name": "case_ambiguity_broader_class.json",
        "role": "ambiguity_broader_class",
        "case_id": "ambiguity_broader_class",
    },
    {
        "name": "case_false_positive_disagreement_abstain.json",
        "role": "false_positive_disagreement_abstain",
        "case_id": "false_positive_disagreement_abstain",
    },
)

SYNTHETIC_BENCHMARK_LEDGER_FILENAME = "synthetic_per_class_benchmark_ledger.json"
ALLOWED_SYNTHETIC_LEDGER_FIELDS = {
    "schema_version",
    "record_type",
    "ledger_id",
    "revision",
    "is_synthetic",
    "production_benchmark",
    "material_benchmark_pass",
    "row_complete",
    "production_completion_allowed",
    "visual_review_claimed",
    "rows085_088_acceptance_claimed",
    "authority_ceiling",
    "hold_reasons",
    "fixture_bindings",
    "per_class_expectations",
    "edge_case_expectations",
    "provenance",
    "ledger_sha256",
}


def _assert_keys_exact(obj: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(obj.keys()) - allowed)
    if unknown:
        raise ValueError(f"{label} has unknown fields: {', '.join(unknown)}")


def _expect_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _expect_optional_string_or_none(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string or null")
    stripped = value.strip()
    return stripped if stripped else None


def _expect_boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


def _expect_non_negative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return int(value)


def _expect_positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return int(value)


def _expect_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    as_float = float(value)
    if not math.isfinite(as_float):
        raise ValueError(f"{label} must be finite")
    return as_float


def _expect_sha256(value: Any, label: str) -> str:
    text = _expect_non_empty_string(value, label)
    if len(text) != 64 or any(ch not in SHA256_HEX_CHARS for ch in text):
        raise ValueError(f"{label} must be a lowercase 64-char sha256")
    return text


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_path = Path(handle.name)
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    try:
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def content_addressed_body(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the deterministic body hashed for replay/tamper checks.

    Wall-clock ``created_at`` and the self-referential ``manifest_sha256`` are
    excluded so identical fixture packets replay to the same digest.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    return {key: value for key, value in payload.items() if key not in CONTENT_ADDRESSED_EXCLUDED_FIELDS}


def content_addressed_manifest_sha256(payload: dict[str, Any]) -> str:
    return _canonical_sha256(content_addressed_body(payload))


def verify_manifest_integrity(payload: dict[str, Any]) -> str:
    """Recompute content-addressed digest and reject tampered manifests."""
    recorded = _expect_sha256(payload.get("manifest_sha256"), "manifest_sha256")
    recomputed = content_addressed_manifest_sha256(payload)
    if recorded != recomputed:
        raise ValueError(
            "manifest_sha256 tamper/replay mismatch: "
            f"recorded={recorded} recomputed={recomputed}"
        )
    return recomputed


def load_fixture_packet(name: str, *, fixture_dir: Path | None = None) -> dict[str, Any]:
    """Load a checked-in Row089 fixture packet by filename."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(f"Row089 fixture packet missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Row089 fixture packet must be a JSON object: {path}")
    return payload


def fixture_file_sha256(name: str, *, fixture_dir: Path | None = None) -> str:
    """Return the lowercase sha256 of a checked-in fixture packet file bytes."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(f"Row089 fixture packet missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_synthetic_benchmark_ledger_integrity(payload: dict[str, Any]) -> str:
    """Recompute content-addressed ledger digest and reject tamper."""
    recorded = _expect_sha256(payload.get("ledger_sha256"), "ledger_sha256")
    body = {key: value for key, value in payload.items() if key != "ledger_sha256"}
    recomputed = _canonical_sha256(body)
    if recorded != recomputed:
        raise ValueError(
            "ledger_sha256 tamper/replay mismatch: "
            f"recorded={recorded} recomputed={recomputed}"
        )
    return recomputed


def load_synthetic_benchmark_ledger(*, fixture_dir: Path | None = None) -> dict[str, Any]:
    """Load the checked-in non-production synthetic per-class benchmark ledger."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = directory / SYNTHETIC_BENCHMARK_LEDGER_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Row089 synthetic benchmark ledger missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Row089 synthetic benchmark ledger must be a JSON object: {path}")
    return payload


def _decision_by_id(compiled: dict[str, Any], decision_id: str, label: str) -> dict[str, Any]:
    decisions = compiled.get("material_decisions")
    if not isinstance(decisions, list):
        raise ValueError(f"{label}: compiled manifest missing material_decisions")
    for decision in decisions:
        if isinstance(decision, dict) and decision.get("decision_id") == decision_id:
            return decision
    raise ValueError(f"{label}: decision_id {decision_id!r} absent from compiled manifest")


def _assert_expectation_matches_decision(
    expectation: dict[str, Any],
    decision: dict[str, Any],
    *,
    label: str,
) -> None:
    field_pairs = (
        ("expected_decision_state", "decision_state"),
        ("expected_observed_class", "observed_class"),
        ("expected_broader_class", "broader_class"),
        ("expected_abstention_reason", "abstention_reason"),
    )
    for expected_key, actual_key in field_pairs:
        if expected_key not in expectation:
            raise ValueError(f"{label}: missing {expected_key}")
        if expectation[expected_key] != decision.get(actual_key):
            raise ValueError(
                f"{label}: {expected_key} mismatch "
                f"ledger={expectation[expected_key]!r} compiled={decision.get(actual_key)!r}"
            )


def verify_synthetic_ledger_vs_compiled_manifest_expectations(
    ledger: dict[str, Any] | None = None,
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Fail-closed ledger-vs-compiled-manifest expectation verifier.

    Recompiles every ledger-bound fixture packet and rejects:
    - fixture-file digest drift
    - compiled-manifest digest drift
    - per-class / edge-case expectation field drift

    Explicitly refuses production benchmark pass, visual-review, Rows085/088
    acceptance, and row completion claims. Synthetic fixture authority only.
    """
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    payload = ledger if ledger is not None else load_synthetic_benchmark_ledger(fixture_dir=directory)
    if not isinstance(payload, dict):
        raise ValueError("synthetic ledger must be an object")
    _assert_keys_exact(payload, ALLOWED_SYNTHETIC_LEDGER_FIELDS, "synthetic_ledger")
    ledger_digest = verify_synthetic_benchmark_ledger_integrity(payload)

    if payload.get("record_type") != "row089_synthetic_per_class_benchmark_ledger":
        raise ValueError("synthetic ledger record_type mismatch")
    if payload.get("is_synthetic") is not True:
        raise ValueError("synthetic ledger must set is_synthetic=true")
    if payload.get("authority_ceiling") != "fixture_synthetic_only":
        raise ValueError("synthetic ledger authority_ceiling must remain fixture_synthetic_only")

    false_flags = (
        "production_benchmark",
        "material_benchmark_pass",
        "row_complete",
        "production_completion_allowed",
        "visual_review_claimed",
        "rows085_088_acceptance_claimed",
    )
    for flag in false_flags:
        if payload.get(flag) is not False:
            raise ValueError(f"synthetic ledger must keep {flag}=false")

    bindings = payload.get("fixture_bindings")
    if not isinstance(bindings, list) or not bindings:
        raise ValueError("synthetic ledger fixture_bindings must be a non-empty list")
    per_class = payload.get("per_class_expectations")
    if not isinstance(per_class, list) or len(per_class) != len(REQUIRED_MATERIAL_CLASSES):
        raise ValueError("synthetic ledger per_class_expectations must cover exactly eight classes")
    edge_cases = payload.get("edge_case_expectations")
    if not isinstance(edge_cases, list) or len(edge_cases) != 3:
        raise ValueError("synthetic ledger edge_case_expectations must contain exactly three cases")

    compiled_by_fixture: dict[str, dict[str, Any]] = {}
    live_file_digest_by_fixture: dict[str, str] = {}
    live_compiled_digest_by_fixture: dict[str, str] = {}

    for idx, binding in enumerate(bindings):
        label = f"fixture_bindings[{idx}]"
        if not isinstance(binding, dict):
            raise ValueError(f"{label} must be an object")
        fixture_name = _expect_non_empty_string(binding.get("fixture_name"), f"{label}.fixture_name")
        recorded_file = _expect_sha256(
            binding.get("fixture_file_sha256"), f"{label}.fixture_file_sha256"
        )
        recorded_compiled = _expect_sha256(
            binding.get("compiled_manifest_sha256"), f"{label}.compiled_manifest_sha256"
        )
        if binding.get("row_complete") is not False:
            raise ValueError(f"{label}.row_complete must remain false")
        if binding.get("is_synthetic") is not True:
            raise ValueError(f"{label}.is_synthetic must be true")

        live_file = fixture_file_sha256(fixture_name, fixture_dir=directory)
        if recorded_file != live_file:
            raise ValueError(
                f"{label}: fixture file digest drift for {fixture_name}: "
                f"ledger={recorded_file} live={live_file}"
            )

        compiled = compile_manifest(load_fixture_packet(fixture_name, fixture_dir=directory))
        live_compiled = verify_manifest_integrity(compiled)
        if recorded_compiled != live_compiled:
            raise ValueError(
                f"{label}: compiled manifest digest drift for {fixture_name}: "
                f"ledger={recorded_compiled} live={live_compiled}"
            )
        if compiled["row_complete"] or compiled["production_completion_allowed"]:
            raise ValueError(f"{label}: compiled fixture must remain non-complete")
        if compiled["runtime_authority"].get("material_benchmark_pass"):
            raise ValueError(f"{label}: compiled fixture must not claim material_benchmark_pass")

        compiled_by_fixture[fixture_name] = compiled
        live_file_digest_by_fixture[fixture_name] = live_file
        live_compiled_digest_by_fixture[fixture_name] = live_compiled

    expected_fixture_names = {meta["name"] for meta in SYNTHETIC_BENCHMARK_FIXTURE_PACKETS}
    if set(compiled_by_fixture) != expected_fixture_names:
        raise ValueError(
            "synthetic ledger fixture_bindings set drift: "
            f"ledger={sorted(compiled_by_fixture)} expected={sorted(expected_fixture_names)}"
        )

    seen_classes: set[str] = set()
    for idx, expectation in enumerate(per_class):
        label = f"per_class_expectations[{idx}]"
        if not isinstance(expectation, dict):
            raise ValueError(f"{label} must be an object")
        material_class = _expect_non_empty_string(
            expectation.get("material_class"), f"{label}.material_class"
        )
        if material_class not in REQUIRED_MATERIAL_CLASSES:
            raise ValueError(f"{label}.material_class not in required taxonomy: {material_class}")
        if material_class in seen_classes:
            raise ValueError(f"{label}: duplicate material_class {material_class}")
        seen_classes.add(material_class)

        source_fixture = _expect_non_empty_string(
            expectation.get("source_fixture"), f"{label}.source_fixture"
        )
        if source_fixture not in compiled_by_fixture:
            raise ValueError(f"{label}: source_fixture {source_fixture!r} not bound")
        recorded_file = _expect_sha256(
            expectation.get("source_fixture_file_sha256"),
            f"{label}.source_fixture_file_sha256",
        )
        recorded_compiled = _expect_sha256(
            expectation.get("source_compiled_manifest_sha256"),
            f"{label}.source_compiled_manifest_sha256",
        )
        if recorded_file != live_file_digest_by_fixture[source_fixture]:
            raise ValueError(
                f"{label}: source fixture file digest drift for {source_fixture}: "
                f"ledger={recorded_file} live={live_file_digest_by_fixture[source_fixture]}"
            )
        if recorded_compiled != live_compiled_digest_by_fixture[source_fixture]:
            raise ValueError(
                f"{label}: source compiled manifest digest drift for {source_fixture}: "
                f"ledger={recorded_compiled} live={live_compiled_digest_by_fixture[source_fixture]}"
            )

        decision_id = _expect_non_empty_string(
            expectation.get("decision_id"), f"{label}.decision_id"
        )
        decision = _decision_by_id(compiled_by_fixture[source_fixture], decision_id, label)
        _assert_expectation_matches_decision(expectation, decision, label=label)
        if expectation.get("expected_observed_class") != material_class:
            raise ValueError(
                f"{label}: expected_observed_class must equal material_class "
                f"({material_class})"
            )
        if expectation.get("expected_decision_state") != "observed_class":
            raise ValueError(f"{label}: required materials must expect observed_class")

    missing_classes = sorted(REQUIRED_MATERIAL_CLASSES - seen_classes)
    if missing_classes:
        raise ValueError(
            "synthetic ledger per_class coverage missing: " + ",".join(missing_classes)
        )

    seen_edge_cases: set[str] = set()
    for idx, expectation in enumerate(edge_cases):
        label = f"edge_case_expectations[{idx}]"
        if not isinstance(expectation, dict):
            raise ValueError(f"{label} must be an object")
        case_id = _expect_non_empty_string(expectation.get("case_id"), f"{label}.case_id")
        if case_id in seen_edge_cases:
            raise ValueError(f"{label}: duplicate case_id {case_id}")
        seen_edge_cases.add(case_id)

        source_fixture = _expect_non_empty_string(
            expectation.get("source_fixture"), f"{label}.source_fixture"
        )
        if source_fixture not in compiled_by_fixture:
            raise ValueError(f"{label}: source_fixture {source_fixture!r} not bound")
        recorded_file = _expect_sha256(
            expectation.get("source_fixture_file_sha256"),
            f"{label}.source_fixture_file_sha256",
        )
        recorded_compiled = _expect_sha256(
            expectation.get("source_compiled_manifest_sha256"),
            f"{label}.source_compiled_manifest_sha256",
        )
        if recorded_file != live_file_digest_by_fixture[source_fixture]:
            raise ValueError(
                f"{label}: source fixture file digest drift for {source_fixture}: "
                f"ledger={recorded_file} live={live_file_digest_by_fixture[source_fixture]}"
            )
        if recorded_compiled != live_compiled_digest_by_fixture[source_fixture]:
            raise ValueError(
                f"{label}: source compiled manifest digest drift for {source_fixture}: "
                f"ledger={recorded_compiled} live={live_compiled_digest_by_fixture[source_fixture]}"
            )

        decision_id = _expect_non_empty_string(
            expectation.get("decision_id"), f"{label}.decision_id"
        )
        decision = _decision_by_id(compiled_by_fixture[source_fixture], decision_id, label)
        _assert_expectation_matches_decision(expectation, decision, label=label)

    expected_edge_cases = {
        meta["case_id"]
        for meta in SYNTHETIC_BENCHMARK_FIXTURE_PACKETS
        if meta["role"] != "required_materials"
    }
    if seen_edge_cases != expected_edge_cases:
        raise ValueError(
            "synthetic ledger edge_case set drift: "
            f"ledger={sorted(seen_edge_cases)} expected={sorted(expected_edge_cases)}"
        )

    return {
        "status": "ok",
        "verifier": "verify_synthetic_ledger_vs_compiled_manifest_expectations",
        "ledger_sha256": ledger_digest,
        "fixture_binding_count": len(bindings),
        "per_class_expectation_count": len(per_class),
        "edge_case_expectation_count": len(edge_cases),
        "digest_drift_rejected": True,
        "production_benchmark": False,
        "material_benchmark_pass": False,
        "visual_review_claimed": False,
        "rows085_088_acceptance_claimed": False,
        "row_complete": False,
        "authority_ceiling": "fixture_synthetic_only",
    }


def build_synthetic_per_class_benchmark_ledger(
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Bind fixture digests into a non-production per-class benchmark ledger.

    Records expected decision_state per required material class and edge-case
    fixtures. Explicitly refuses production benchmark pass, visual-review, and
    Rows085/088 acceptance claims. ``row_complete`` remains false.
    """
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    fixture_bindings: list[dict[str, Any]] = []
    per_class_expectations: list[dict[str, Any]] = []
    edge_case_expectations: list[dict[str, Any]] = []
    seen_classes: set[str] = set()

    for packet_meta in SYNTHETIC_BENCHMARK_FIXTURE_PACKETS:
        name = packet_meta["name"]
        role = packet_meta["role"]
        case_id = packet_meta["case_id"]
        file_digest = fixture_file_sha256(name, fixture_dir=directory)
        packet = load_fixture_packet(name, fixture_dir=directory)
        compiled = compile_manifest(packet)
        compiled_digest = verify_manifest_integrity(compiled)
        if compiled["row_complete"] or compiled["production_completion_allowed"]:
            raise ValueError(
                f"fixture {name} must remain non-complete for synthetic ledger binding"
            )
        if compiled["runtime_authority"].get("material_benchmark_pass"):
            raise ValueError(
                f"fixture {name} must not claim material_benchmark_pass in synthetic ledger"
            )

        fixture_bindings.append(
            {
                "fixture_name": name,
                "role": role,
                "case_id": case_id,
                "fixture_file_sha256": file_digest,
                "compiled_manifest_sha256": compiled_digest,
                "is_synthetic": True,
                "row_complete": False,
            }
        )

        for decision in compiled["material_decisions"]:
            decision_state = decision["decision_state"]
            observed_class = decision.get("observed_class")
            entry = {
                "source_fixture": name,
                "source_fixture_file_sha256": file_digest,
                "source_compiled_manifest_sha256": compiled_digest,
                "decision_id": decision["decision_id"],
                "expected_decision_state": decision_state,
                "expected_observed_class": observed_class,
                "expected_broader_class": decision.get("broader_class"),
                "expected_abstention_reason": decision.get("abstention_reason"),
            }
            if role == "required_materials":
                if observed_class is None:
                    raise ValueError(
                        f"required_materials fixture decision {decision['decision_id']} "
                        "missing observed_class"
                    )
                if observed_class in seen_classes:
                    raise ValueError(f"duplicate required material class in ledger: {observed_class}")
                seen_classes.add(observed_class)
                per_class_expectations.append(
                    {
                        "material_class": observed_class,
                        **entry,
                    }
                )
            else:
                edge_case_expectations.append(
                    {
                        "case_id": case_id,
                        "role": role,
                        **entry,
                    }
                )

    missing = sorted(REQUIRED_MATERIAL_CLASSES - seen_classes)
    if missing:
        raise ValueError(
            "synthetic ledger missing required material classes: " + ",".join(missing)
        )
    if len(per_class_expectations) != len(REQUIRED_MATERIAL_CLASSES):
        raise ValueError("synthetic ledger per_class_expectations must cover exactly eight classes")
    if len(edge_case_expectations) != 3:
        raise ValueError("synthetic ledger requires exactly three edge-case expectations")

    per_class_expectations.sort(key=lambda item: item["material_class"])
    edge_case_expectations.sort(key=lambda item: item["case_id"])
    fixture_bindings.sort(key=lambda item: item["fixture_name"])

    ledger_body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "record_type": "row089_synthetic_per_class_benchmark_ledger",
        "ledger_id": "row089_synthetic_per_class_benchmark_ledger_v1",
        "revision": "row089_synthetic_ledger_v1",
        "is_synthetic": True,
        "production_benchmark": False,
        "material_benchmark_pass": False,
        "row_complete": False,
        "production_completion_allowed": False,
        "visual_review_claimed": False,
        "rows085_088_acceptance_claimed": False,
        "authority_ceiling": "fixture_synthetic_only",
        "hold_reasons": [
            "synthetic_fixture_ledger_only",
            "dependency_row085_incomplete",
            "dependency_row088_incomplete",
            "material_benchmark_absent",
            "runtime_receipt_absent",
            "combined_frame_contact_audio_review_absent",
        ],
        "fixture_bindings": fixture_bindings,
        "per_class_expectations": per_class_expectations,
        "edge_case_expectations": edge_case_expectations,
        "provenance": {
            "compiler": "compile_wave64_visual_material_recognition.py",
            "compiler_revision": "row089_synthetic_per_class_benchmark_ledger_v1",
            "non_production": True,
            "binds_fixture_file_and_compiled_manifest_digests": True,
        },
    }
    _assert_keys_exact(ledger_body, ALLOWED_SYNTHETIC_LEDGER_FIELDS - {"ledger_sha256"}, "synthetic_ledger")
    ledger_body["ledger_sha256"] = _canonical_sha256(ledger_body)
    verify_synthetic_benchmark_ledger_integrity(ledger_body)
    return ledger_body


def write_synthetic_per_class_benchmark_ledger(
    output_path: Path | None = None,
    *,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """Build and atomically write the synthetic per-class benchmark ledger."""
    directory = fixture_dir if fixture_dir is not None else DEFAULT_FIXTURE_DIR
    path = output_path if output_path is not None else directory / SYNTHETIC_BENCHMARK_LEDGER_FILENAME
    ledger = build_synthetic_per_class_benchmark_ledger(fixture_dir=directory)
    _write_json_atomic(path, ledger)
    return ledger


def _normalize_material_class(raw: Any, label: str) -> str:
    text = _expect_non_empty_string(raw, label)
    if text in REQUIRED_MATERIAL_CLASSES:
        return text
    if text in GOVERNED_ALIASES:
        return GOVERNED_ALIASES[text]
    raise ValueError(
        f"{label} must be a required material class or governed alias; got {text!r}"
    )


def _validate_timeline_binding(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("timeline_binding must be an object")
    _assert_keys_exact(raw, ALLOWED_TIMELINE_BINDING_FIELDS, "timeline_binding")
    frame_rate = _expect_number(raw.get("frame_rate"), "timeline_binding.frame_rate")
    if frame_rate <= 0:
        raise ValueError("timeline_binding.frame_rate must be > 0")
    return {
        "timeline_id": _expect_non_empty_string(raw.get("timeline_id"), "timeline_binding.timeline_id"),
        "timeline_sha256": _expect_sha256(raw.get("timeline_sha256"), "timeline_binding.timeline_sha256"),
        "frame_count": _expect_positive_int(raw.get("frame_count"), "timeline_binding.frame_count"),
        "frame_rate": frame_rate,
        "frame_time_origin_seconds": _expect_number(
            raw.get("frame_time_origin_seconds"), "timeline_binding.frame_time_origin_seconds"
        ),
    }


def _validate_scene_registry_binding(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("scene_registry_binding must be an object")
    _assert_keys_exact(raw, ALLOWED_SCENE_REGISTRY_BINDING_FIELDS, "scene_registry_binding")
    return {
        "scene_registry_id": _expect_non_empty_string(
            raw.get("scene_registry_id"), "scene_registry_binding.scene_registry_id"
        ),
        "scene_registry_sha256": _expect_sha256(
            raw.get("scene_registry_sha256"), "scene_registry_binding.scene_registry_sha256"
        ),
        "frame_span_id": _expect_non_empty_string(
            raw.get("frame_span_id"), "scene_registry_binding.frame_span_id"
        ),
        "entity_region_count": _expect_positive_int(
            raw.get("entity_region_count"), "scene_registry_binding.entity_region_count"
        ),
    }


def _validate_classifier_stack(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("classifier_stack must be an object")
    _assert_keys_exact(raw, ALLOWED_CLASSIFIER_STACK_FIELDS, "classifier_stack")
    return {
        "classifier_id": _expect_non_empty_string(raw.get("classifier_id"), "classifier_stack.classifier_id"),
        "weights_sha256": _expect_sha256(raw.get("weights_sha256"), "classifier_stack.weights_sha256"),
        "preprocessing_sha256": _expect_sha256(
            raw.get("preprocessing_sha256"), "classifier_stack.preprocessing_sha256"
        ),
        "class_map_sha256": _expect_sha256(raw.get("class_map_sha256"), "classifier_stack.class_map_sha256"),
        "revision": _expect_non_empty_string(raw.get("revision"), "classifier_stack.revision"),
    }


def _validate_thresholds(raw: Any) -> dict[str, float | int]:
    if not isinstance(raw, dict):
        raise ValueError("thresholds must be an object")
    _assert_keys_exact(raw, ALLOWED_THRESHOLD_FIELDS, "thresholds")
    min_class_confidence = _expect_number(raw.get("min_class_confidence"), "thresholds.min_class_confidence")
    if min_class_confidence < 0 or min_class_confidence > 1:
        raise ValueError("thresholds.min_class_confidence must be within [0, 1]")
    min_agreeing = _expect_positive_int(
        raw.get("min_agreeing_independent_sources"), "thresholds.min_agreeing_independent_sources"
    )
    if min_agreeing < 2:
        raise ValueError("thresholds.min_agreeing_independent_sources must be >= 2")
    max_abstention_ratio = _expect_number(raw.get("max_abstention_ratio"), "thresholds.max_abstention_ratio")
    if max_abstention_ratio < 0 or max_abstention_ratio > 1:
        raise ValueError("thresholds.max_abstention_ratio must be within [0, 1]")
    min_texture_quality = _expect_number(raw.get("min_texture_quality"), "thresholds.min_texture_quality")
    if min_texture_quality < 0 or min_texture_quality > 1:
        raise ValueError("thresholds.min_texture_quality must be within [0, 1]")
    return {
        "min_class_confidence": min_class_confidence,
        "min_agreeing_independent_sources": min_agreeing,
        "max_abstention_ratio": max_abstention_ratio,
        "min_texture_quality": min_texture_quality,
    }


def _validate_evidence_sources(raw: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{label} must be a non-empty list")
    sources: list[dict[str, Any]] = []
    seen_kinds: set[str] = set()
    for idx, item in enumerate(raw):
        item_label = f"{label}[{idx}]"
        if not isinstance(item, dict):
            raise ValueError(f"{item_label} must be an object")
        _assert_keys_exact(item, {"kind", "source_id", "observation_sha256", "supports_class"}, item_label)
        kind = _expect_non_empty_string(item.get("kind"), f"{item_label}.kind")
        if kind not in ALLOWED_EVIDENCE_KINDS:
            raise ValueError(f"{item_label}.kind must be one of {sorted(ALLOWED_EVIDENCE_KINDS)}")
        if kind in seen_kinds:
            raise ValueError(f"{item_label}.kind duplicate independent evidence kind: {kind}")
        seen_kinds.add(kind)
        sources.append(
            {
                "kind": kind,
                "source_id": _expect_non_empty_string(item.get("source_id"), f"{item_label}.source_id"),
                "observation_sha256": _expect_sha256(
                    item.get("observation_sha256"), f"{item_label}.observation_sha256"
                ),
                "supports_class": _normalize_material_class(
                    item.get("supports_class"), f"{item_label}.supports_class"
                ),
            }
        )
    return sources


def _validate_texture_evidence(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object")
    _assert_keys_exact(raw, ALLOWED_TEXTURE_FIELDS, label)
    quality = _expect_number(raw.get("quality_score"), f"{label}.quality_score")
    if quality < 0 or quality > 1:
        raise ValueError(f"{label}.quality_score must be within [0, 1]")
    resolution = raw.get("resolution_px")
    if not isinstance(resolution, list) or len(resolution) != 2:
        raise ValueError(f"{label}.resolution_px must be a 2-integer array")
    width = _expect_positive_int(resolution[0], f"{label}.resolution_px[0]")
    height = _expect_positive_int(resolution[1], f"{label}.resolution_px[1]")
    return {
        "feature_digest_sha256": _expect_sha256(
            raw.get("feature_digest_sha256"), f"{label}.feature_digest_sha256"
        ),
        "resolution_px": [width, height],
        "crop_authority": _expect_non_empty_string(raw.get("crop_authority"), f"{label}.crop_authority"),
        "quality_score": quality,
    }


def _validate_contact_context(raw: Any, label: str, *, region_kind: str) -> dict[str, Any] | None:
    if region_kind != "contact_region":
        if raw is not None:
            raise ValueError(f"{label} must be null unless region_kind=contact_region")
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"{label} required for contact_region decisions")
    _assert_keys_exact(raw, ALLOWED_CONTACT_FIELDS, label)
    ownership_state = _expect_non_empty_string(raw.get("ownership_state"), f"{label}.ownership_state")
    if ownership_state not in ALLOWED_OWNERSHIP_STATES:
        raise ValueError(f"{label}.ownership_state must be one of {sorted(ALLOWED_OWNERSHIP_STATES)}")
    return {
        "contact_id": _expect_non_empty_string(raw.get("contact_id"), f"{label}.contact_id"),
        "source_owner_id": _expect_non_empty_string(
            raw.get("source_owner_id"), f"{label}.source_owner_id"
        ),
        "target_owner_id": _expect_non_empty_string(
            raw.get("target_owner_id"), f"{label}.target_owner_id"
        ),
        "ownership_state": ownership_state,
    }


def _validate_fusion(raw: Any, label: str, *, evidence_sources: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object")
    _assert_keys_exact(raw, ALLOWED_FUSION_FIELDS, label)
    independent_source_count = _expect_positive_int(
        raw.get("independent_source_count"), f"{label}.independent_source_count"
    )
    agreeing_source_count = _expect_non_negative_int(
        raw.get("agreeing_source_count"), f"{label}.agreeing_source_count"
    )
    if independent_source_count != len(evidence_sources):
        raise ValueError(f"{label}.independent_source_count must equal evidence_sources length")
    if agreeing_source_count > independent_source_count:
        raise ValueError(f"{label}.agreeing_source_count cannot exceed independent_source_count")
    disagreement = _expect_boolean(raw.get("disagreement"), f"{label}.disagreement")
    support_classes = {source["supports_class"] for source in evidence_sources}
    computed_disagreement = len(support_classes) > 1
    if disagreement != computed_disagreement:
        raise ValueError(f"{label}.disagreement does not match evidence_sources class disagreement")
    if not disagreement and agreeing_source_count != independent_source_count:
        raise ValueError(f"{label}.agreeing_source_count must equal independent sources when no disagreement")
    return {
        "independent_source_count": independent_source_count,
        "agreeing_source_count": agreeing_source_count,
        "disagreement": disagreement,
        "fusion_rule": _expect_non_empty_string(raw.get("fusion_rule"), f"{label}.fusion_rule"),
    }


def _compile_material_decision(
    raw: Any,
    *,
    index: int,
    frame_count: int,
    previous_frame: int | None,
    previous_pts: int | None,
    thresholds: dict[str, float | int],
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"material_decisions[{index}] must be an object")
    label = f"material_decisions[{index}]"
    _assert_keys_exact(raw, ALLOWED_DECISION_FIELDS, label)

    frame_index = _expect_non_negative_int(raw.get("frame_index"), f"{label}.frame_index")
    pts = _expect_non_negative_int(raw.get("pts"), f"{label}.pts")
    if frame_index >= frame_count:
        raise ValueError(f"{label}.frame_index must be < timeline frame_count")
    if previous_frame is not None:
        if frame_index < previous_frame:
            raise ValueError(f"{label}.frame_index must be non-decreasing across decisions")
        if frame_index == previous_frame and pts <= previous_pts:
            raise ValueError(f"{label}.pts must be unique and strictly increasing within a frame")

    region_kind = _expect_non_empty_string(raw.get("region_kind"), f"{label}.region_kind")
    if region_kind not in ALLOWED_REGION_KINDS:
        raise ValueError(f"{label}.region_kind must be one of {sorted(ALLOWED_REGION_KINDS)}")

    decision_state = _expect_non_empty_string(raw.get("decision_state"), f"{label}.decision_state")
    if decision_state not in ALLOWED_DECISION_STATES:
        raise ValueError(f"{label}.decision_state must be one of {sorted(ALLOWED_DECISION_STATES)}")

    ambiguity = _expect_non_empty_string(raw.get("ambiguity"), f"{label}.ambiguity")
    if ambiguity not in ALLOWED_AMBIGUITY:
        raise ValueError(f"{label}.ambiguity must be one of {sorted(ALLOWED_AMBIGUITY)}")

    confidence = _expect_number(raw.get("confidence"), f"{label}.confidence")
    if confidence < 0 or confidence > 1:
        raise ValueError(f"{label}.confidence must be within [0, 1]")

    observed_raw = raw.get("observed_class")
    broader_raw = raw.get("broader_class")
    abstention_reason = _expect_optional_string_or_none(
        raw.get("abstention_reason"), f"{label}.abstention_reason"
    )

    evidence_sources = _validate_evidence_sources(raw.get("evidence_sources"), f"{label}.evidence_sources")
    texture_evidence = _validate_texture_evidence(raw.get("texture_evidence"), f"{label}.texture_evidence")
    contact_context = _validate_contact_context(
        raw.get("contact_context"), f"{label}.contact_context", region_kind=region_kind
    )
    fusion = _validate_fusion(raw.get("fusion"), f"{label}.fusion", evidence_sources=evidence_sources)

    if decision_state == "abstain":
        if confidence != 0:
            raise ValueError(f"{label} abstain decision_state requires confidence=0")
        if observed_raw is not None:
            raise ValueError(f"{label} abstain decision_state requires observed_class=null")
        if broader_raw is not None:
            raise ValueError(f"{label} abstain decision_state requires broader_class=null")
        if abstention_reason is None:
            raise ValueError(f"{label} abstain decision_state requires abstention_reason")
        observed_class = None
        broader_class = None
    elif decision_state == "broader_class":
        if observed_raw is not None:
            raise ValueError(f"{label} broader_class decision_state requires observed_class=null")
        broader_class = _expect_non_empty_string(broader_raw, f"{label}.broader_class")
        if broader_class not in ALLOWED_BROADER_CLASSES:
            raise ValueError(f"{label}.broader_class must be one of {sorted(ALLOWED_BROADER_CLASSES)}")
        if abstention_reason is not None:
            raise ValueError(f"{label} broader_class decision_state requires abstention_reason=null")
        observed_class = None
    else:
        observed_class = _normalize_material_class(observed_raw, f"{label}.observed_class")
        expected_broader = BROADER_CLASS_MAP[observed_class]
        broader_class = _expect_non_empty_string(broader_raw, f"{label}.broader_class")
        if broader_class != expected_broader:
            raise ValueError(
                f"{label}.broader_class must equal governed parent {expected_broader!r} for {observed_class}"
            )
        if abstention_reason is not None:
            raise ValueError(f"{label} observed_class decision_state requires abstention_reason=null")
        if confidence < float(thresholds["min_class_confidence"]):
            raise ValueError(
                f"{label} observed_class confidence below thresholds.min_class_confidence"
            )
        if fusion["agreeing_source_count"] < int(thresholds["min_agreeing_independent_sources"]):
            raise ValueError(
                f"{label} observed_class requires >= "
                f"{thresholds['min_agreeing_independent_sources']} agreeing independent sources"
            )
        if fusion["disagreement"]:
            raise ValueError(f"{label} observed_class blocked when evidence sources disagree")
        if "material_classifier" not in {source["kind"] for source in evidence_sources}:
            raise ValueError(f"{label} observed_class requires material_classifier evidence")
        if "texture_evidence" not in {source["kind"] for source in evidence_sources}:
            raise ValueError(f"{label} observed_class requires texture_evidence evidence")
        if texture_evidence["quality_score"] < float(thresholds["min_texture_quality"]):
            raise ValueError(f"{label} texture quality below thresholds.min_texture_quality")
        support_classes = {source["supports_class"] for source in evidence_sources}
        if support_classes != {observed_class}:
            raise ValueError(f"{label} evidence_sources must unanimously support observed_class")

    if region_kind == "contact_region" and contact_context is not None:
        if contact_context["ownership_state"] != "trusted" and decision_state == "observed_class":
            raise ValueError(
                f"{label} contact_region observed_class requires trusted contact ownership_state"
            )

    return {
        "decision_id": _expect_non_empty_string(raw.get("decision_id"), f"{label}.decision_id"),
        "frame_index": frame_index,
        "pts": pts,
        "owner_id": _expect_non_empty_string(raw.get("owner_id"), f"{label}.owner_id"),
        "track_id": _expect_non_empty_string(raw.get("track_id"), f"{label}.track_id"),
        "region_id": _expect_non_empty_string(raw.get("region_id"), f"{label}.region_id"),
        "region_kind": region_kind,
        "observed_class": observed_class,
        "broader_class": broader_class,
        "decision_state": decision_state,
        "confidence": confidence,
        "ambiguity": ambiguity,
        "abstention_reason": abstention_reason,
        "evidence_sources": evidence_sources,
        "texture_evidence": texture_evidence,
        "contact_context": contact_context,
        "fusion": fusion,
    }


def compile_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    _assert_keys_exact(payload, ALLOWED_TOP_LEVEL_FIELDS, "input")
    schema_version = _expect_non_empty_string(payload.get("schema_version"), "schema_version")
    if schema_version != "1.0.0":
        raise ValueError("schema_version must equal 1.0.0")

    shot_id = _expect_non_empty_string(payload.get("shot_id"), "shot_id")
    take_id = _expect_non_empty_string(payload.get("take_id"), "take_id")

    timeline_binding = _validate_timeline_binding(payload.get("timeline_binding"))
    scene_registry_binding = _validate_scene_registry_binding(payload.get("scene_registry_binding"))
    classifier_stack = _validate_classifier_stack(payload.get("classifier_stack"))
    thresholds = _validate_thresholds(payload.get("thresholds"))

    dependency_raw = payload.get("dependency_authority")
    if not isinstance(dependency_raw, dict):
        raise ValueError("dependency_authority must be an object")
    _assert_keys_exact(dependency_raw, {"row085_complete", "row088_complete"}, "dependency_authority")
    row085_complete = _expect_boolean(dependency_raw.get("row085_complete"), "dependency_authority.row085_complete")
    row088_complete = _expect_boolean(dependency_raw.get("row088_complete"), "dependency_authority.row088_complete")

    runtime_raw = payload.get("runtime_authority")
    if not isinstance(runtime_raw, dict):
        raise ValueError("runtime_authority must be an object")
    runtime_allowed = {
        "material_benchmark_pass",
        "runtime_receipt_present",
        "combined_frame_contact_audio_review_present",
    }
    _assert_keys_exact(runtime_raw, runtime_allowed, "runtime_authority")
    material_benchmark_pass = _expect_boolean(
        runtime_raw.get("material_benchmark_pass"), "runtime_authority.material_benchmark_pass"
    )
    runtime_receipt_present = _expect_boolean(
        runtime_raw.get("runtime_receipt_present"), "runtime_authority.runtime_receipt_present"
    )
    combined_review_present = _expect_boolean(
        runtime_raw.get("combined_frame_contact_audio_review_present"),
        "runtime_authority.combined_frame_contact_audio_review_present",
    )

    decisions_raw = payload.get("material_decisions")
    if not isinstance(decisions_raw, list) or not decisions_raw:
        raise ValueError("material_decisions must be a non-empty list")

    material_decisions: list[dict[str, Any]] = []
    seen_decision_ids: set[str] = set()
    previous_frame: int | None = None
    previous_pts: int | None = None
    for idx, decision_raw in enumerate(decisions_raw):
        compiled = _compile_material_decision(
            decision_raw,
            index=idx,
            frame_count=timeline_binding["frame_count"],
            previous_frame=previous_frame,
            previous_pts=previous_pts,
            thresholds=thresholds,
        )
        if compiled["decision_id"] in seen_decision_ids:
            raise ValueError(f"duplicate decision_id detected: {compiled['decision_id']}")
        seen_decision_ids.add(compiled["decision_id"])
        previous_frame = compiled["frame_index"]
        previous_pts = compiled["pts"]
        material_decisions.append(compiled)

    if scene_registry_binding["entity_region_count"] < len({d["region_id"] for d in material_decisions}):
        raise ValueError("scene_registry_binding.entity_region_count under-counts distinct region_id values")

    decision_count = len(material_decisions)
    observed_count = sum(1 for d in material_decisions if d["decision_state"] == "observed_class")
    broader_count = sum(1 for d in material_decisions if d["decision_state"] == "broader_class")
    abstention_count = sum(1 for d in material_decisions if d["decision_state"] == "abstain")
    disagreement_count = sum(1 for d in material_decisions if d["fusion"]["disagreement"])
    contact_region_count = sum(1 for d in material_decisions if d["region_kind"] == "contact_region")
    classes_covered = sorted(
        {
            d["observed_class"]
            for d in material_decisions
            if d["observed_class"] is not None
        }
    )
    metrics = {
        "decision_count": decision_count,
        "observed_class_count": observed_count,
        "broader_class_count": broader_count,
        "abstention_count": abstention_count,
        "disagreement_count": disagreement_count,
        "contact_region_count": contact_region_count,
        "required_classes_covered": classes_covered,
        "required_class_coverage_count": len(classes_covered),
    }

    threshold_violations: list[str] = []
    abstention_ratio = abstention_count / decision_count if decision_count else 1.0
    if abstention_ratio > float(thresholds["max_abstention_ratio"]):
        threshold_violations.append("abstention_ratio>max_abstention_ratio")

    unsupported_material_claims = bool(threshold_violations) or disagreement_count > 0 and observed_count > 0
    dependency_ready = row085_complete and row088_complete
    runtime_ready = material_benchmark_pass and runtime_receipt_present and combined_review_present
    material_certification_allowed = (
        dependency_ready and runtime_ready and not unsupported_material_claims and not threshold_violations
    )
    # Fail closed in this increment: no production tracker runtime authority yet.
    production_completion_allowed = False
    row_complete = False

    if not dependency_ready:
        authority_ceiling = "candidate"
        status = "candidate_hold"
    else:
        authority_ceiling = "technical"
        status = "technical_partial"

    hold_reasons: list[str] = []
    if not row085_complete:
        hold_reasons.append("dependency_row085_incomplete")
    if not row088_complete:
        hold_reasons.append("dependency_row088_incomplete")
    if not material_benchmark_pass:
        hold_reasons.append("material_benchmark_absent")
    if not runtime_receipt_present:
        hold_reasons.append("runtime_receipt_absent")
    if not combined_review_present:
        hold_reasons.append("combined_frame_contact_audio_review_absent")
    if unsupported_material_claims:
        hold_reasons.append("unsupported_material_claims_block_certification")
    if threshold_violations:
        hold_reasons.append("threshold_violations:" + ",".join(threshold_violations))
    missing_required = sorted(REQUIRED_MATERIAL_CLASSES - set(classes_covered))
    if missing_required:
        hold_reasons.append("required_taxonomy_coverage_incomplete:" + ",".join(missing_required))

    provenance = payload.get("provenance")
    if provenance is None:
        provenance = {
            "compiler": "compile_wave64_visual_material_recognition.py",
            "compiler_revision": "row089_fail_closed_v1",
        }
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")

    receipt_body = {
        "schema_version": "1.0.0",
        "record_type": "visual_material_recognition_manifest",
        "manifest_id": _expect_non_empty_string(payload.get("manifest_id"), "manifest_id"),
        "revision": _expect_non_empty_string(payload.get("revision"), "revision"),
        "run_id": _expect_non_empty_string(payload.get("run_id"), "run_id"),
        "scene_id": _expect_non_empty_string(payload.get("scene_id"), "scene_id"),
        "shot_id": shot_id,
        "take_id": take_id,
        "is_synthetic": _expect_boolean(payload.get("is_synthetic"), "is_synthetic"),
        "video_sha256": _expect_sha256(payload.get("video_sha256"), "video_sha256"),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status,
        "timeline_binding": timeline_binding,
        "scene_registry_binding": scene_registry_binding,
        "classifier_stack": classifier_stack,
        "dependency_authority": {
            "row085_complete": row085_complete,
            "row088_complete": row088_complete,
            "dependency_ready": dependency_ready,
        },
        "runtime_authority": {
            "material_benchmark_pass": material_benchmark_pass,
            "runtime_receipt_present": runtime_receipt_present,
            "combined_frame_contact_audio_review_present": combined_review_present,
            "runtime_ready": runtime_ready,
        },
        "taxonomy": {
            "required_material_classes": sorted(REQUIRED_MATERIAL_CLASSES),
            "governed_aliases": dict(sorted(GOVERNED_ALIASES.items())),
            "broader_class_map": dict(sorted(BROADER_CLASS_MAP.items())),
        },
        "material_decisions": material_decisions,
        "metrics": metrics,
        "thresholds": thresholds,
        "threshold_violations": threshold_violations,
        "authority_summary": {
            "material_certification_allowed": material_certification_allowed,
            "unsupported_material_claims": unsupported_material_claims,
            "hold_reasons": hold_reasons,
        },
        "authority_ceiling": authority_ceiling,
        "production_completion_allowed": production_completion_allowed,
        "row_complete": row_complete,
        "provenance": provenance,
    }
    # Content-addressed digest excludes wall-clock created_at for deterministic replay.
    manifest_sha256 = content_addressed_manifest_sha256(receipt_body)
    receipt_body["manifest_sha256"] = manifest_sha256
    return receipt_body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile a fail-closed Row089 visual material recognition manifest."
    )
    parser.add_argument("--input", help="Path to visual material recognition input packet JSON")
    parser.add_argument("--output", help="Path to write compiled material manifest JSON")
    parser.add_argument(
        "--emit-synthetic-benchmark-ledger",
        metavar="PATH",
        help=(
            "Build the non-production synthetic per-class benchmark ledger bound to "
            "checked-in fixture digests and write it to PATH"
        ),
    )
    parser.add_argument(
        "--verify-synthetic-benchmark-ledger",
        action="store_true",
        help=(
            "Fail-closed verify checked-in synthetic ledger expectations against "
            "live compiled fixture manifests; reject digest drift without claiming "
            "production benchmark pass"
        ),
    )
    parser.add_argument(
        "--fixture-dir",
        default=str(DEFAULT_FIXTURE_DIR),
        help="Fixture directory for synthetic ledger emission (default: checked-in row089 fixtures)",
    )
    args = parser.parse_args(argv)

    if args.emit_synthetic_benchmark_ledger:
        try:
            ledger = write_synthetic_per_class_benchmark_ledger(
                Path(args.emit_synthetic_benchmark_ledger),
                fixture_dir=Path(args.fixture_dir),
            )
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW089_FAIL_CLOSED: {exc}") from exc
        print(
            json.dumps(
                {
                    "status": "ok",
                    "record_type": ledger["record_type"],
                    "ledger_sha256": ledger["ledger_sha256"],
                    "row_complete": False,
                    "material_benchmark_pass": False,
                    "production_benchmark": False,
                    "visual_review_claimed": False,
                    "rows085_088_acceptance_claimed": False,
                    "per_class_count": len(ledger["per_class_expectations"]),
                    "edge_case_count": len(ledger["edge_case_expectations"]),
                }
            )
        )
        return 0

    if args.verify_synthetic_benchmark_ledger:
        try:
            receipt = verify_synthetic_ledger_vs_compiled_manifest_expectations(
                fixture_dir=Path(args.fixture_dir),
            )
        except (OSError, ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"ROW089_FAIL_CLOSED: {exc}") from exc
        print(json.dumps(receipt))
        return 0

    if not args.input or not args.output:
        raise SystemExit(
            "ROW089_FAIL_CLOSED: --input and --output are required unless emitting "
            "or verifying the synthetic ledger"
        )

    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("input packet must be a JSON object")
    try:
        receipt = compile_manifest(payload)
    except ValueError as exc:
        raise SystemExit(f"ROW089_FAIL_CLOSED: {exc}") from exc
    _write_json_atomic(output_path, receipt)
    print(
        json.dumps(
            {
                "status": "ok",
                "manifest_sha256": receipt["manifest_sha256"],
                "row_complete": False,
                "material_certification_allowed": receipt["authority_summary"][
                    "material_certification_allowed"
                ],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
