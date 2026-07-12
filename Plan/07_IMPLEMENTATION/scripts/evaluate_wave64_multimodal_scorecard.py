#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover
    Draft202012Validator = None  # type: ignore[assignment]


CANONICAL_ROOT = Path(__file__).resolve().parents[3]
REQUEST_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_multimodal_scorecard_request.schema.json"
REPORT_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_multimodal_scorecard_report.schema.json"
STRICT_AUDIO_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_strict_audio_review_report.schema.json"
GLOBAL_AUDIO_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_global_audio_review_report.schema.json"
AV_SYNC_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_av_sync_certification_report.schema.json"
W34_MANIFEST_CONTRACT = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave34_release_manifest.schema.json"
W34_DECISION_CONTRACT = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave34_release_gate_decision.schema.json"
RULES_PATH = CANONICAL_ROOT / "Plan/10_REGISTRIES/wave64_multimodal_scorecard_rules.json"


class EvaluatorError(ValueError):
    pass


def _reject_nonfinite_json(token: str) -> Any:
    raise EvaluatorError(f"non-finite numeric token is not allowed: {token}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise EvaluatorError(f"duplicate JSON key is not allowed: {key}")
        payload[key] = value
    return payload


def _load_json_strict(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_nonfinite_json,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except OSError as exc:
        raise EvaluatorError(f"failed reading JSON file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise EvaluatorError(f"invalid JSON in {path}: {exc}") from exc


def _validate_with_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    if Draft202012Validator is None:
        raise EvaluatorError("jsonschema Draft 2020-12 validation is unavailable; failing closed")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        where = ".".join(str(part) for part in first.path)
        raise EvaluatorError(f"{label} schema validation failed at {where}: {first.message}")


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _expect_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvaluatorError(f"{label} must be a non-empty string")
    return value.strip()


def _expect_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise EvaluatorError(f"{label} must be boolean")
    return bool(value)


def _expect_exact_object_keys(payload: dict[str, Any], required: set[str], label: str) -> None:
    observed = set(payload.keys())
    missing = sorted(required - observed)
    extra = sorted(observed - required)
    if missing or extra:
        parts: list[str] = []
        if missing:
            parts.append(f"missing={','.join(missing)}")
        if extra:
            parts.append(f"unknown={','.join(extra)}")
        raise EvaluatorError(f"{label} key mismatch ({'; '.join(parts)})")


def _resolve_under_root(raw_path: str, label: str) -> Path:
    candidate = Path(raw_path).resolve()
    if not _is_under_root(candidate, CANONICAL_ROOT):
        raise EvaluatorError(f"{label} escapes canonical root: {candidate}")
    return candidate


def _resolve_binding(binding: Any, label: str) -> dict[str, Any]:
    if not isinstance(binding, dict):
        raise EvaluatorError(f"{label} must be object")
    _expect_exact_object_keys(binding, {"path", "sha256", "bytes"}, label)
    path = _resolve_under_root(_expect_str(binding["path"], f"{label}.path"), f"{label}.path")
    sha = _expect_str(binding["sha256"], f"{label}.sha256")
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise EvaluatorError(f"{label}.sha256 must be lowercase SHA-256")
    size = binding["bytes"]
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise EvaluatorError(f"{label}.bytes must be a positive integer")
    if not path.is_file():
        raise EvaluatorError(f"{label}.path does not exist: {path}")
    observed_size = path.stat().st_size
    if observed_size != size:
        raise EvaluatorError(f"{label}.bytes mismatch ({size} != {observed_size})")
    observed_sha = _sha256_of(path)
    if observed_sha != sha:
        raise EvaluatorError(f"{label}.sha256 mismatch ({sha} != {observed_sha})")
    return {"path": str(path), "sha256": sha, "bytes": size}


def _binding_to_repo_relative(binding: dict[str, Any]) -> dict[str, Any]:
    path = Path(binding["path"]).resolve()
    relative = path.relative_to(CANONICAL_ROOT).as_posix()
    return {"path": relative, "sha256": binding["sha256"], "bytes": binding["bytes"]}


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    try:
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _read_bool_path(payload: dict[str, Any], dotted_path: str) -> tuple[bool, str]:
    node: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, f"missing {dotted_path}"
        node = node[part]
    if isinstance(node, bool):
        return node, ""
    if isinstance(node, str):
        return node == "PASS", ""
    return False, f"non-boolean gate at {dotted_path}"


def _extract_lineage(payload: dict[str, Any], label: str) -> dict[str, Any]:
    lineage = payload.get("lineage")
    if not isinstance(lineage, dict):
        raise EvaluatorError(f"{label}.lineage must be object")
    required = {"run_id", "scene_id", "shot_id", "take_id", "is_synthetic"}
    _expect_exact_object_keys(lineage, required, f"{label}.lineage")
    return {
        "run_id": _expect_str(lineage["run_id"], f"{label}.lineage.run_id"),
        "scene_id": _expect_str(lineage["scene_id"], f"{label}.lineage.scene_id"),
        "shot_id": _expect_str(lineage["shot_id"], f"{label}.lineage.shot_id"),
        "take_id": _expect_str(lineage["take_id"], f"{label}.lineage.take_id"),
        "is_synthetic": _expect_bool(lineage["is_synthetic"], f"{label}.lineage.is_synthetic"),
    }


def _extract_lineage_optional(payload: dict[str, Any], label: str, blockers: list[str]) -> dict[str, Any] | None:
    lineage = payload.get("lineage")
    if not isinstance(lineage, dict):
        blockers.append(f"{label}.lineage missing or non-object")
        return None
    expected = {"run_id", "scene_id", "shot_id", "take_id", "is_synthetic"}
    observed = set(lineage.keys())
    for missing in sorted(expected - observed):
        blockers.append(f"{label}.lineage missing {missing}")
    for extra in sorted(observed - expected):
        blockers.append(f"{label}.lineage unknown key {extra}")
    if expected - observed:
        return None
    parsed: dict[str, Any] = {}
    for key in ("run_id", "scene_id", "shot_id", "take_id"):
        value = lineage.get(key)
        if not isinstance(value, str) or not value.strip():
            blockers.append(f"{label}.lineage.{key} must be a non-empty string")
        else:
            parsed[key] = value.strip()
    synthetic_value = lineage.get("is_synthetic")
    if not isinstance(synthetic_value, bool):
        blockers.append(f"{label}.lineage.is_synthetic must be boolean")
    else:
        parsed["is_synthetic"] = synthetic_value
    if len(parsed) != 5:
        return None
    return parsed


def _validate_legacy_contract(payload: dict[str, Any], contract: dict[str, Any], label: str, blockers: list[str]) -> None:
    if not isinstance(contract, dict):
        blockers.append(f"{label} contract schema must be object")
        return
    required_fields = contract.get("required_fields")
    if not isinstance(required_fields, list) or not required_fields:
        blockers.append(f"{label} contract required_fields missing")
        return
    for field_name in required_fields:
        if not isinstance(field_name, str) or not field_name:
            blockers.append(f"{label} contract required field must be non-empty string")
            continue
        if field_name not in payload:
            blockers.append(f"{label} missing required field from legacy contract: {field_name}")


def _expect_nonnegative_int(value: Any, label: str, blockers: list[str]) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        blockers.append(f"{label} must be a non-negative integer")
        return None
    return value


def _expect_nonempty_str_soft(value: Any, label: str, blockers: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        blockers.append(f"{label} must be a non-empty string")
        return None
    return value.strip()


def _expect_list_soft(value: Any, label: str, blockers: list[str]) -> list[Any] | None:
    if not isinstance(value, list):
        blockers.append(f"{label} must be a list")
        return None
    return value


def _expect_object_soft(value: Any, label: str, blockers: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        blockers.append(f"{label} must be an object")
        return None
    return value


def _read_path_soft(payload: Any, dotted_path: str) -> tuple[bool, Any]:
    node = payload
    for part in dotted_path.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def _expect_bool_path_soft(payload: dict[str, Any], dotted_path: str, label: str, blockers: list[str]) -> bool | None:
    exists, value = _read_path_soft(payload, dotted_path)
    if not exists:
        blockers.append(f"{label}.{dotted_path} missing")
        return None
    if not isinstance(value, bool):
        blockers.append(f"{label}.{dotted_path} must be boolean")
        return None
    return value


def _expect_pass_path_soft(payload: dict[str, Any], dotted_path: str, label: str, blockers: list[str]) -> bool | None:
    exists, value = _read_path_soft(payload, dotted_path)
    if not exists:
        blockers.append(f"{label}.{dotted_path} missing")
        return None
    if not isinstance(value, str):
        blockers.append(f"{label}.{dotted_path} must be string PASS/BLOCKED/FAIL")
        return None
    return value == "PASS"


def _expect_str_path_soft(payload: dict[str, Any], dotted_path: str, label: str, blockers: list[str]) -> str | None:
    exists, value = _read_path_soft(payload, dotted_path)
    if not exists:
        blockers.append(f"{label}.{dotted_path} missing")
        return None
    if not isinstance(value, str) or not value.strip():
        blockers.append(f"{label}.{dotted_path} must be a non-empty string")
        return None
    return value.strip()


def _collect_legacy_semantic_blockers(
    manifest_payload: dict[str, Any],
    release_payload: dict[str, Any],
    blockers: list[str],
) -> None:
    _expect_nonempty_str_soft(manifest_payload.get("release_id"), "artifact_manifest.release_id", blockers)
    _expect_nonempty_str_soft(manifest_payload.get("release_type"), "artifact_manifest.release_type", blockers)
    _expect_nonempty_str_soft(manifest_payload.get("pack_root"), "artifact_manifest.pack_root", blockers)
    _expect_nonnegative_int(manifest_payload.get("file_count"), "artifact_manifest.file_count", blockers)
    _expect_nonnegative_int(manifest_payload.get("json_count"), "artifact_manifest.json_count", blockers)
    _expect_nonnegative_int(manifest_payload.get("script_count"), "artifact_manifest.script_count", blockers)
    _expect_list_soft(manifest_payload.get("main_flow_inventory"), "artifact_manifest.main_flow_inventory", blockers)
    _expect_list_soft(manifest_payload.get("source_inputs"), "artifact_manifest.source_inputs", blockers)
    _expect_list_soft(manifest_payload.get("added_wave34_files"), "artifact_manifest.added_wave34_files", blockers)
    _expect_object_soft(manifest_payload.get("proof_boundaries"), "artifact_manifest.proof_boundaries", blockers)
    _expect_nonempty_str_soft(manifest_payload.get("validation_report_ref"), "artifact_manifest.validation_report_ref", blockers)
    _expect_nonempty_str_soft(manifest_payload.get("handoff_ref"), "artifact_manifest.handoff_ref", blockers)
    _expect_nonempty_str_soft(
        manifest_payload.get("release_gate_decision_ref"), "artifact_manifest.release_gate_decision_ref", blockers
    )

    _expect_nonempty_str_soft(release_payload.get("decision_id"), "release_gate_decision.decision_id", blockers)
    _expect_nonempty_str_soft(release_payload.get("release_id"), "release_gate_decision.release_id", blockers)
    for field in (
        "app_mode_status",
        "orchestrator_status",
        "local_proof_status",
        "ec2_proof_status",
        "qa_certification_status",
        "manifest_status",
    ):
        _expect_nonempty_str_soft(release_payload.get(field), f"release_gate_decision.{field}", blockers)
    _expect_object_soft(release_payload.get("runtime_boundary_statuses"), "release_gate_decision.runtime_boundary_statuses", blockers)
    blocked_reasons = _expect_list_soft(release_payload.get("blocked_reasons"), "release_gate_decision.blocked_reasons", blockers)
    _expect_nonempty_str_soft(release_payload.get("promotion_decision"), "release_gate_decision.promotion_decision", blockers)
    if blocked_reasons is not None and any(not isinstance(item, str) or not item.strip() for item in blocked_reasons):
        blockers.append("release_gate_decision.blocked_reasons entries must be non-empty strings")

    manifest_release_id = manifest_payload.get("release_id")
    decision_release_id = release_payload.get("release_id")
    if isinstance(manifest_release_id, str) and isinstance(decision_release_id, str):
        if manifest_release_id.strip() and decision_release_id.strip() and manifest_release_id != decision_release_id:
            blockers.append("artifact_manifest.release_id must match release_gate_decision.release_id")


def _resolve_authority_binding(binding: Any, label: str) -> dict[str, Any]:
    if not isinstance(binding, dict):
        raise EvaluatorError(f"{label} must be object")
    _expect_exact_object_keys(binding, {"path", "sha256", "bytes"}, label)
    path_value = _expect_str(binding["path"], f"{label}.path")
    if path_value.startswith("/") or ":" in path_value:
        raise EvaluatorError(f"{label}.path must be canonical repo-relative path")
    sha = _expect_str(binding["sha256"], f"{label}.sha256")
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise EvaluatorError(f"{label}.sha256 must be lowercase SHA-256")
    size = binding["bytes"]
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise EvaluatorError(f"{label}.bytes must be a positive integer")
    return {"path": path_value, "sha256": sha, "bytes": size}


def _parse_exact_authority_object(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise EvaluatorError(f"{label} must be object")
    required = {
        "authority_id",
        "bundle_id",
        "artifact_id",
        "run_id",
        "scene_id",
        "shot_id",
        "take_id",
        "release_id",
        "is_synthetic",
        "input_bindings",
    }
    optional = {"expected_strict_audio_producer_ids"}
    observed = set(raw.keys())
    missing = sorted(required - observed)
    extra = sorted(observed - (required | optional))
    if missing or extra:
        parts: list[str] = []
        if missing:
            parts.append(f"missing={','.join(missing)}")
        if extra:
            parts.append(f"unknown={','.join(extra)}")
        raise EvaluatorError(f"{label} key mismatch ({'; '.join(parts)})")
    parsed: dict[str, Any] = {
        "authority_id": _expect_str(raw["authority_id"], f"{label}.authority_id"),
        "bundle_id": _expect_str(raw["bundle_id"], f"{label}.bundle_id"),
        "artifact_id": _expect_str(raw["artifact_id"], f"{label}.artifact_id"),
        "run_id": _expect_str(raw["run_id"], f"{label}.run_id"),
        "scene_id": _expect_str(raw["scene_id"], f"{label}.scene_id"),
        "shot_id": _expect_str(raw["shot_id"], f"{label}.shot_id"),
        "take_id": _expect_str(raw["take_id"], f"{label}.take_id"),
        "release_id": _expect_str(raw["release_id"], f"{label}.release_id"),
        "is_synthetic": _expect_bool(raw["is_synthetic"], f"{label}.is_synthetic"),
    }
    input_bindings = raw["input_bindings"]
    if not isinstance(input_bindings, dict):
        raise EvaluatorError(f"{label}.input_bindings must be object")
    binding_keys = {
        "image_review_binding",
        "video_review_binding",
        "strict_audio_report_binding",
        "global_audio_report_binding",
        "av_sync_report_binding",
        "artifact_manifest_binding",
        "release_gate_decision_binding",
    }
    _expect_exact_object_keys(input_bindings, binding_keys, f"{label}.input_bindings")
    parsed["input_bindings"] = {
        key: _resolve_authority_binding(input_bindings[key], f"{label}.input_bindings.{key}") for key in sorted(binding_keys)
    }
    expected_producers = raw.get("expected_strict_audio_producer_ids")
    if expected_producers is not None:
        if not isinstance(expected_producers, dict):
            raise EvaluatorError(f"{label}.expected_strict_audio_producer_ids must be object when present")
        _expect_exact_object_keys(
            expected_producers,
            {"prompt_alignment_producer_id", "playback_review_producer_id", "production_review_producer_id"},
            f"{label}.expected_strict_audio_producer_ids",
        )
        parsed["expected_strict_audio_producer_ids"] = {
            key: _expect_str(expected_producers[key], f"{label}.expected_strict_audio_producer_ids.{key}")
            for key in (
                "prompt_alignment_producer_id",
                "playback_review_producer_id",
                "production_review_producer_id",
            )
        }
    else:
        parsed["expected_strict_audio_producer_ids"] = None
    return parsed


def _collect_structured_blockers(
    payload: dict[str, Any], label: str, field: str, dependency_blockers: list[str], *, dict_reason_key: str = "reason"
) -> None:
    if field not in payload:
        return
    raw_blockers = payload.get(field)
    if not isinstance(raw_blockers, list):
        dependency_blockers.append(f"{label}.{field} must be a list")
        return
    for index, item in enumerate(raw_blockers):
        text = ""
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            raw_reason = item.get(dict_reason_key)
            if isinstance(raw_reason, str):
                text = raw_reason.strip()
            else:
                text = json.dumps(item, sort_keys=True)
        else:
            text = str(item)
        if text:
            dependency_blockers.append(f"{label}.{field}[{index}]: {text}")


def _match_exact_authority_object(
    authority_object: dict[str, Any],
    request_lineage: dict[str, Any],
    artifact_id: str,
    release_id: str,
    request_bindings_rel: dict[str, dict[str, Any]],
) -> tuple[bool, bool, bool, list[str]]:
    mismatches: list[str] = []
    for field, expected in (
        ("artifact_id", artifact_id),
        ("run_id", request_lineage["run_id"]),
        ("scene_id", request_lineage["scene_id"]),
        ("shot_id", request_lineage["shot_id"]),
        ("take_id", request_lineage["take_id"]),
        ("is_synthetic", request_lineage["is_synthetic"]),
    ):
        if authority_object[field] != expected:
            mismatches.append(f"authority binding mismatch for {field}")
    release_ok = authority_object["release_id"] == release_id
    if not release_ok:
        mismatches.append("authority binding mismatch for release_id")
    artifact_ok = len([m for m in mismatches if "release_id" not in m]) == 0
    for binding_name, expected_binding in request_bindings_rel.items():
        if authority_object["input_bindings"][binding_name] != expected_binding:
            mismatches.append(f"authority input binding mismatch for {binding_name}")
            artifact_ok = False
    return len(mismatches) == 0, release_ok, artifact_ok, mismatches


def _score_from_checks(checks: list[bool]) -> int:
    if not checks:
        return 0
    ratio = float(sum(1 for item in checks if item)) / float(len(checks))
    return max(0, min(5, int(math.floor((ratio * 5.0) + 1e-9))))


def _extract_canonical_promotion_decisions(decision_contract: dict[str, Any]) -> set[str]:
    candidates: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = key.lower()
                if "promotion" in lowered and isinstance(value, list):
                    if all(isinstance(item, str) and item.strip() for item in value):
                        for item in value:
                            candidates.add(item.strip())
                if key == "promotion_decision":
                    if isinstance(value, dict):
                        enum_values = value.get("enum")
                        if isinstance(enum_values, list):
                            for item in enum_values:
                                if isinstance(item, str) and item.strip():
                                    candidates.add(item.strip())
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and item.strip():
                                candidates.add(item.strip())
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(decision_contract)
    return candidates


def _validate_release_decision_ref_binding(
    manifest_binding: dict[str, Any],
    release_binding: dict[str, Any],
    manifest_payload: dict[str, Any],
    blockers: list[str],
) -> bool:
    ref_value = manifest_payload.get("release_gate_decision_ref")
    if not isinstance(ref_value, str) or not ref_value.strip():
        blockers.append("artifact_manifest.release_gate_decision_ref must be a non-empty string")
        return False
    ref = ref_value.strip()
    manifest_path = Path(manifest_binding["path"]).resolve()
    bound_release_path = Path(release_binding["path"]).resolve()
    bound_release_rel = bound_release_path.relative_to(CANONICAL_ROOT).as_posix()

    candidate_paths: list[Path] = []
    if ref.startswith("/"):
        blockers.append("artifact_manifest.release_gate_decision_ref must be repo-relative or manifest-relative")
        return False
    ref_path = Path(ref)
    if ":" in ref:
        blockers.append("artifact_manifest.release_gate_decision_ref must not contain drive-like prefixes")
        return False
    if len(ref_path.parts) > 1:
        candidate_paths.append((CANONICAL_ROOT / ref_path).resolve())
    else:
        candidate_paths.append((manifest_path.parent / ref_path).resolve())
        candidate_paths.append((CANONICAL_ROOT / ref_path).resolve())

    for candidate in candidate_paths:
        if not _is_under_root(candidate, CANONICAL_ROOT):
            continue
        if candidate == bound_release_path:
            return True
        if candidate.relative_to(CANONICAL_ROOT).as_posix() == bound_release_rel:
            return True

    blockers.append("artifact_manifest.release_gate_decision_ref does not resolve to bound release_gate_decision artifact")
    return False


def _validate_image_video_contract_types(
    payload: dict[str, Any],
    *,
    label: str,
    expected_tracker_id: str,
    expected_item_id: str,
    request_artifact_id: str,
    required_boolean_gates: list[str],
    blockers: list[str],
) -> dict[str, bool | None]:
    tracker_id = payload.get("tracker_id")
    item_id = payload.get("item_id")
    evidence_id = payload.get("evidence_id")
    if tracker_id != expected_tracker_id:
        blockers.append(f"{label}.tracker_id mismatch ({tracker_id!r} != {expected_tracker_id!r})")
    if item_id != expected_item_id:
        blockers.append(f"{label}.item_id mismatch ({item_id!r} != {expected_item_id!r})")
    if evidence_id != request_artifact_id:
        blockers.append(f"{label}.evidence_id must equal request.artifact_id")
    if not isinstance(payload.get("acceptance_gates"), dict):
        blockers.append(f"{label}.acceptance_gates must be an object")
    if not isinstance(payload.get("strict_decision"), dict):
        blockers.append(f"{label}.strict_decision must be an object")
    if not isinstance(payload.get("lineage"), dict):
        blockers.append(f"{label}.lineage must be an object")
    overall_pass = payload.get("overall_pass")
    if not isinstance(overall_pass, bool):
        blockers.append(f"{label}.overall_pass must be boolean")
    if label == "image_review":
        technical_pass = payload.get("technical_pass")
        if not isinstance(technical_pass, bool):
            blockers.append("image_review.technical_pass must be boolean")
    row_complete = _expect_bool_path_soft(payload, "strict_decision.row_complete", label, blockers)
    gate_results: dict[str, bool | None] = {"strict_decision.row_complete": row_complete}
    for gate in required_boolean_gates:
        gate_value = _expect_bool_path_soft(payload, f"acceptance_gates.{gate}", label, blockers)
        gate_results[f"acceptance_gates.{gate}"] = gate_value
    return gate_results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    if not _is_under_root(input_path, CANONICAL_ROOT):
        print(f"ERROR: input path escapes canonical project root: {input_path}")
        return 1
    if not _is_under_root(output_path, CANONICAL_ROOT):
        print(f"ERROR: output path escapes canonical project root: {output_path}")
        return 1
    if output_path.exists():
        print(f"ERROR: output collision detected: {output_path}")
        return 1

    try:
        request_payload = _load_json_strict(input_path)
        request_schema = _load_json_strict(REQUEST_SCHEMA)
        report_schema = _load_json_strict(REPORT_SCHEMA)
        strict_audio_schema = _load_json_strict(STRICT_AUDIO_SCHEMA)
        global_audio_schema = _load_json_strict(GLOBAL_AUDIO_SCHEMA)
        av_sync_schema = _load_json_strict(AV_SYNC_SCHEMA)
        manifest_contract = _load_json_strict(W34_MANIFEST_CONTRACT)
        decision_contract = _load_json_strict(W34_DECISION_CONTRACT)
        rules = _load_json_strict(RULES_PATH)

        _validate_with_schema(request_payload, request_schema, "request")

        req_output_path = _resolve_under_root(
            _expect_str(request_payload["output_report_path"], "request.output_report_path"),
            "request.output_report_path",
        )
        if req_output_path != output_path:
            raise EvaluatorError("request.output_report_path must exactly match --output path")

        _expect_exact_object_keys(
            rules,
            {
                "schema_name",
                "registry_version",
                "required_categories",
                "minimum_required_category_score",
                "required_upstream_gates",
                "release_allowed_promotion_decisions",
                "authority_rules",
                "contracts",
            },
            "rules",
        )
        if rules["schema_name"] != "wave64_multimodal_scorecard_rules":
            raise EvaluatorError("rules.schema_name mismatch")
        if rules["registry_version"] != 1:
            raise EvaluatorError("rules.registry_version must be 1")

        run_id = _expect_str(request_payload["run_id"], "request.run_id")
        scene_id = _expect_str(request_payload["scene_id"], "request.scene_id")
        shot_id = _expect_str(request_payload["shot_id"], "request.shot_id")
        take_id = _expect_str(request_payload["take_id"], "request.take_id")
        artifact_id = _expect_str(request_payload["artifact_id"], "request.artifact_id")
        artifact_type = _expect_str(request_payload["artifact_type"], "request.artifact_type")
        generation_test_method = _expect_str(request_payload["generation_test_method"], "request.generation_test_method")
        is_synthetic = _expect_bool(request_payload["is_synthetic"], "request.is_synthetic")
        dependency_blockers: list[str] = []

        bindings = {
            "image_review": _resolve_binding(request_payload["image_review_binding"], "request.image_review_binding"),
            "video_review": _resolve_binding(request_payload["video_review_binding"], "request.video_review_binding"),
            "strict_audio_report": _resolve_binding(
                request_payload["strict_audio_report_binding"], "request.strict_audio_report_binding"
            ),
            "global_audio_report": _resolve_binding(
                request_payload["global_audio_report_binding"], "request.global_audio_report_binding"
            ),
            "av_sync_report": _resolve_binding(request_payload["av_sync_report_binding"], "request.av_sync_report_binding"),
            "artifact_manifest": _resolve_binding(
                request_payload["artifact_manifest_binding"], "request.artifact_manifest_binding"
            ),
            "release_gate_decision": _resolve_binding(
                request_payload["release_gate_decision_binding"], "request.release_gate_decision_binding"
            ),
        }

        payloads = {name: _load_json_strict(Path(info["path"])) for name, info in bindings.items()}
        if not isinstance(payloads["image_review"], dict):
            raise EvaluatorError("image review record must be object")
        if not isinstance(payloads["video_review"], dict):
            raise EvaluatorError("video review record must be object")
        if not isinstance(payloads["strict_audio_report"], dict):
            raise EvaluatorError("strict audio report must be object")
        if not isinstance(payloads["global_audio_report"], dict):
            raise EvaluatorError("global audio report must be object")
        if not isinstance(payloads["av_sync_report"], dict):
            raise EvaluatorError("av sync report must be object")
        if not isinstance(payloads["artifact_manifest"], dict):
            raise EvaluatorError("artifact manifest record must be object")
        if not isinstance(payloads["release_gate_decision"], dict):
            raise EvaluatorError("release gate decision record must be object")

        _validate_with_schema(payloads["strict_audio_report"], strict_audio_schema, "strict_audio_report")
        _validate_with_schema(payloads["global_audio_report"], global_audio_schema, "global_audio_report")
        _validate_with_schema(payloads["av_sync_report"], av_sync_schema, "av_sync_report")

        contracts = rules["contracts"]
        if not isinstance(contracts, dict):
            raise EvaluatorError("rules.contracts must be object")
        image_contract = contracts.get("image_review")
        video_contract = contracts.get("video_review")
        if not isinstance(image_contract, dict) or not isinstance(video_contract, dict):
            raise EvaluatorError("rules contracts for image/video must be objects")
        for contract_name, payload in (("image_review", payloads["image_review"]), ("video_review", payloads["video_review"])):
            contract = image_contract if contract_name == "image_review" else video_contract
            required_fields = contract.get("required_fields")
            if not isinstance(required_fields, list) or not required_fields:
                raise EvaluatorError(f"{contract_name} contract required_fields missing")
            for field_name in required_fields:
                if field_name not in payload:
                    dependency_blockers.append(f"{contract_name} missing required contract field: {field_name}")
            for required_contract_field in ("expected_tracker_id", "expected_item_id", "source_artifact_id_field"):
                if required_contract_field not in contract:
                    raise EvaluatorError(f"{contract_name} contract missing {required_contract_field}")

        if payloads["strict_audio_report"].get("schema_name") != contracts["strict_audio_report"]["schema_name"]:
            raise EvaluatorError("strict_audio_report schema_name mismatch")
        if payloads["global_audio_report"].get("schema_name") != contracts["global_audio_report"]["schema_name"]:
            raise EvaluatorError("global_audio_report schema_name mismatch")
        if payloads["av_sync_report"].get("schema_name") != contracts["av_sync_report"]["schema_name"]:
            raise EvaluatorError("av_sync_report schema_name mismatch")

        _validate_legacy_contract(payloads["artifact_manifest"], manifest_contract, "artifact_manifest", dependency_blockers)
        _validate_legacy_contract(payloads["release_gate_decision"], decision_contract, "release_gate_decision", dependency_blockers)
        _collect_legacy_semantic_blockers(
            payloads["artifact_manifest"],
            payloads["release_gate_decision"],
            dependency_blockers,
        )

        lineage_blockers: list[str] = []
        request_lineage = {
            "run_id": run_id,
            "scene_id": scene_id,
            "shot_id": shot_id,
            "take_id": take_id,
            "is_synthetic": is_synthetic,
        }
        image_lineage = _extract_lineage_optional(payloads["image_review"], "image_review", lineage_blockers)
        video_lineage = _extract_lineage_optional(payloads["video_review"], "video_review", lineage_blockers)
        av_payload = payloads["av_sync_report"]
        av_lineage = {
            "run_id": _expect_nonempty_str_soft(av_payload.get("run_id"), "av_sync_report.run_id", lineage_blockers),
            "scene_id": _expect_nonempty_str_soft(av_payload.get("scene_id"), "av_sync_report.scene_id", lineage_blockers),
            "shot_id": _expect_nonempty_str_soft(av_payload.get("shot_id"), "av_sync_report.shot_id", lineage_blockers),
            "take_id": _expect_nonempty_str_soft(av_payload.get("take_id"), "av_sync_report.take_id", lineage_blockers),
            "is_synthetic": av_payload.get("is_synthetic") if isinstance(av_payload.get("is_synthetic"), bool) else None,
        }
        if av_lineage["is_synthetic"] is None:
            lineage_blockers.append("av_sync_report.is_synthetic must be boolean")
        strict_run_id = _expect_nonempty_str_soft(payloads["strict_audio_report"].get("run_id"), "strict_audio_report.run_id", lineage_blockers)
        global_review_run_id = _expect_nonempty_str_soft(
            payloads["global_audio_report"].get("review_run_id"), "global_audio_report.review_run_id", lineage_blockers
        )
        if strict_run_id is not None and strict_run_id != run_id:
            lineage_blockers.append("strict audio report run_id mismatches request lineage")
        if global_review_run_id is not None and global_review_run_id != run_id:
            lineage_blockers.append("global audio report review_run_id mismatches request lineage")
        strict_audio_synthetic = payloads["strict_audio_report"].get("is_synthetic")
        if not isinstance(strict_audio_synthetic, bool):
            lineage_blockers.append("strict_audio_report.is_synthetic must be boolean")
            strict_audio_synthetic = None
        global_audio_synthetic = payloads["global_audio_report"].get("is_synthetic")
        if not isinstance(global_audio_synthetic, bool):
            lineage_blockers.append("global_audio_report.is_synthetic must be boolean")
            global_audio_synthetic = None
        if strict_audio_synthetic is not None and strict_audio_synthetic != is_synthetic:
            lineage_blockers.append("strict audio synthetic provenance mismatches request")
        if global_audio_synthetic is not None and global_audio_synthetic != is_synthetic:
            lineage_blockers.append("global audio synthetic provenance mismatches request")
        for label, lineage in (("image", image_lineage), ("video", video_lineage), ("av_sync", av_lineage)):
            if lineage is None:
                continue
            for key, expected in request_lineage.items():
                observed_value = lineage.get(key)
                if observed_value is None:
                    continue
                if observed_value != expected:
                    lineage_blockers.append(f"{label} lineage mismatch for {key}")

        failing_evidence: list[str] = []
        nonblocking_defects: list[str] = []
        source_identity_check_results: list[str] = []

        image_required_boolean_gates = [
            "camera_spec_check",
            "crop_boundary_check",
            "visual_runtime_ready",
            "image_realism_check",
            "anatomy_check",
            "hyperreal_visual_review",
            "global_visual_review",
            "multi_sample_certification",
            "prompt_alignment_check",
            "contamination_resistance_check",
        ]
        video_required_boolean_gates = [
            "per_frame_qa",
            "temporal_identity_check",
            "flicker_detection",
            "motion_consistency",
            "frame_grid_and_playback_visual_review",
            "runtime_proof",
            "final_temporal_visual_pass",
        ]
        image_contract_tracker = _expect_str(image_contract["expected_tracker_id"], "rules.contracts.image_review.expected_tracker_id")
        image_contract_item = _expect_str(image_contract["expected_item_id"], "rules.contracts.image_review.expected_item_id")
        video_contract_tracker = _expect_str(video_contract["expected_tracker_id"], "rules.contracts.video_review.expected_tracker_id")
        video_contract_item = _expect_str(video_contract["expected_item_id"], "rules.contracts.video_review.expected_item_id")
        image_gate_results = _validate_image_video_contract_types(
            payloads["image_review"],
            label="image_review",
            expected_tracker_id=image_contract_tracker,
            expected_item_id=image_contract_item,
            request_artifact_id=artifact_id,
            required_boolean_gates=image_required_boolean_gates,
            blockers=dependency_blockers,
        )
        video_gate_results = _validate_image_video_contract_types(
            payloads["video_review"],
            label="video_review",
            expected_tracker_id=video_contract_tracker,
            expected_item_id=video_contract_item,
            request_artifact_id=artifact_id,
            required_boolean_gates=video_required_boolean_gates,
            blockers=dependency_blockers,
        )
        source_identity_check_results.extend(
            [
                f"image_review.tracker_id={'ok' if payloads['image_review'].get('tracker_id') == image_contract_tracker else 'mismatch'}",
                f"image_review.item_id={'ok' if payloads['image_review'].get('item_id') == image_contract_item else 'mismatch'}",
                f"image_review.evidence_id={'ok' if payloads['image_review'].get('evidence_id') == artifact_id else 'mismatch'}",
                f"video_review.tracker_id={'ok' if payloads['video_review'].get('tracker_id') == video_contract_tracker else 'mismatch'}",
                f"video_review.item_id={'ok' if payloads['video_review'].get('item_id') == video_contract_item else 'mismatch'}",
                f"video_review.evidence_id={'ok' if payloads['video_review'].get('evidence_id') == artifact_id else 'mismatch'}",
            ]
        )

        authority_rules = rules["authority_rules"]
        if not isinstance(authority_rules, dict):
            raise EvaluatorError("rules.authority_rules must be object")
        _expect_exact_object_keys(
            authority_rules,
            {
                "production_authority_exact_objects",
                "fixture_authority_exact_objects",
                "require_genuine_non_synthetic_provenance_for_approved",
            },
            "rules.authority_rules",
        )
        production_objects_raw = authority_rules["production_authority_exact_objects"]
        fixture_objects_raw = authority_rules["fixture_authority_exact_objects"]
        if not isinstance(production_objects_raw, list) or not isinstance(fixture_objects_raw, list):
            raise EvaluatorError("rules.authority_rules exact object lists must be arrays")
        production_objects = [
            _parse_exact_authority_object(item, f"rules.authority_rules.production_authority_exact_objects[{idx}]")
            for idx, item in enumerate(production_objects_raw)
        ]
        fixture_objects = [
            _parse_exact_authority_object(item, f"rules.authority_rules.fixture_authority_exact_objects[{idx}]")
            for idx, item in enumerate(fixture_objects_raw)
        ]
        all_authority_objects = production_objects + fixture_objects
        pair_to_index: dict[tuple[str, str], int] = {}
        authority_to_bundle: dict[str, str] = {}
        bundle_to_authority: dict[str, str] = {}
        for idx, item in enumerate(all_authority_objects):
            pair = (item["authority_id"], item["bundle_id"])
            if pair in pair_to_index:
                dependency_blockers.append("duplicate authority_id + bundle_id pair in authority registry")
            else:
                pair_to_index[pair] = idx
            if item["authority_id"] in authority_to_bundle and authority_to_bundle[item["authority_id"]] != item["bundle_id"]:
                dependency_blockers.append("authority registry cross-product mapping rejected (authority_id maps to multiple bundle_id)")
            authority_to_bundle[item["authority_id"]] = item["bundle_id"]
            if item["bundle_id"] in bundle_to_authority and bundle_to_authority[item["bundle_id"]] != item["authority_id"]:
                dependency_blockers.append("authority registry cross-product mapping rejected (bundle_id maps to multiple authority_id)")
            bundle_to_authority[item["bundle_id"]] = item["authority_id"]

        claim = request_payload["production_authority_claim"]
        claim_authority = _expect_str(claim["authority_id"], "request.production_authority_claim.authority_id")
        claim_bundle = _expect_str(claim["bundle_id"], "request.production_authority_claim.bundle_id")
        matched_production = [item for item in production_objects if item["authority_id"] == claim_authority and item["bundle_id"] == claim_bundle]
        matched_fixture = [item for item in fixture_objects if item["authority_id"] == claim_authority and item["bundle_id"] == claim_bundle]
        if len(matched_production) > 1 or len(matched_fixture) > 1:
            dependency_blockers.append("duplicate authority pair match found in registry")

        manifest_release_id = str(payloads["artifact_manifest"].get("release_id", "")).strip()
        decision_release_id = str(payloads["release_gate_decision"].get("release_id", "")).strip()
        release_binding_id = decision_release_id or manifest_release_id
        release_decision_ref_valid = _validate_release_decision_ref_binding(
            bindings["artifact_manifest"], bindings["release_gate_decision"], payloads["artifact_manifest"], dependency_blockers
        )
        request_bindings_rel = {
            "image_review_binding": _binding_to_repo_relative(bindings["image_review"]),
            "video_review_binding": _binding_to_repo_relative(bindings["video_review"]),
            "strict_audio_report_binding": _binding_to_repo_relative(bindings["strict_audio_report"]),
            "global_audio_report_binding": _binding_to_repo_relative(bindings["global_audio_report"]),
            "av_sync_report_binding": _binding_to_repo_relative(bindings["av_sync_report"]),
            "artifact_manifest_binding": _binding_to_repo_relative(bindings["artifact_manifest"]),
            "release_gate_decision_binding": _binding_to_repo_relative(bindings["release_gate_decision"]),
        }
        production_authority_exact_match = False
        fixture_authority_exact_match = False
        authority_release_binding_valid = False
        authority_artifact_binding_valid = False

        if matched_production:
            matched, release_ok, artifact_ok, mismatch_reasons = _match_exact_authority_object(
                matched_production[0], request_lineage, artifact_id, release_binding_id, request_bindings_rel
            )
            production_authority_exact_match = matched
            authority_release_binding_valid = release_ok
            authority_artifact_binding_valid = artifact_ok
            if not matched:
                dependency_blockers.extend([f"production authority exact match failed: {reason}" for reason in mismatch_reasons])
        if matched_fixture:
            matched, release_ok, artifact_ok, mismatch_reasons = _match_exact_authority_object(
                matched_fixture[0], request_lineage, artifact_id, release_binding_id, request_bindings_rel
            )
            fixture_authority_exact_match = matched
            authority_release_binding_valid = authority_release_binding_valid or release_ok
            authority_artifact_binding_valid = authority_artifact_binding_valid or artifact_ok
            if not matched:
                dependency_blockers.extend([f"fixture authority exact match failed: {reason}" for reason in mismatch_reasons])

        if not production_authority_exact_match and not fixture_authority_exact_match:
            dependency_blockers.append("no exact authority object match for claimed authority_id + bundle_id")
        if production_authority_exact_match and is_synthetic:
            dependency_blockers.append("synthetic-to-production claim is not trusted")
        if payloads["release_gate_decision"].get("blocked_reasons"):
            dependency_blockers.append("release gate decision contains blocked_reasons")
        if manifest_release_id and decision_release_id and manifest_release_id != decision_release_id:
            dependency_blockers.append("artifact_manifest.release_id and release_gate_decision.release_id mismatch")

        canonical_promotion_decisions = _extract_canonical_promotion_decisions(decision_contract)
        if not canonical_promotion_decisions:
            raise EvaluatorError("wave34 release decision contract does not expose canonical promotion_decision values")
        release_allowed_set = set(rules["release_allowed_promotion_decisions"])
        promotion_decision_raw = payloads["release_gate_decision"].get("promotion_decision")
        promotion_decision = promotion_decision_raw if isinstance(promotion_decision_raw, str) and promotion_decision_raw.strip() else None
        promotion_decision_classification = "unknown_or_ill_typed"
        release_allowed = False
        if promotion_decision is None:
            dependency_blockers.append("release_gate_decision.promotion_decision must be a non-empty string")
        elif promotion_decision not in canonical_promotion_decisions:
            dependency_blockers.append("release_gate_decision.promotion_decision is unknown in canonical wave34 decision schema")
        elif promotion_decision == "blocked_missing_proof":
            dependency_blockers.append("release gate decision is blocked_missing_proof")
            promotion_decision_classification = "canonical_blocked_missing_proof"
        elif promotion_decision in {"repair_required", "blocked_failed_QA"}:
            failing_evidence.append(f"release gate decision indicates failure state: {promotion_decision}")
            promotion_decision_classification = "canonical_present_failure"
        elif promotion_decision in release_allowed_set:
            release_allowed = True
            promotion_decision_classification = "canonical_release_allowed"
        else:
            failing_evidence.append(f"release gate decision is canonical but non-release: {promotion_decision}")
            promotion_decision_classification = "canonical_non_release"

        required_upstream = rules["required_upstream_gates"]
        if not isinstance(required_upstream, dict):
            raise EvaluatorError("rules.required_upstream_gates must be object")
        gate_checks: list[tuple[str, bool]] = []
        gate_kind_by_source = {
            "image_review": "bool",
            "video_review": "bool",
            "strict_audio_report": "pass",
            "global_audio_report": "pass",
            "av_sync_report": "pass",
        }
        for source_name in (
            "image_review",
            "video_review",
            "strict_audio_report",
            "global_audio_report",
            "av_sync_report",
        ):
            gate_paths = required_upstream.get(source_name)
            if not isinstance(gate_paths, list) or not gate_paths:
                raise EvaluatorError(f"rules.required_upstream_gates.{source_name} must be non-empty list")
            payload = payloads[source_name]
            gate_kind = gate_kind_by_source[source_name]
            for gate_path in gate_paths:
                validated_path = _expect_str(gate_path, f"rules.required_upstream_gates.{source_name}[]")
                if source_name == "image_review" and validated_path.startswith("acceptance_gates."):
                    ok = image_gate_results.get(validated_path)
                    if ok is None:
                        gate_checks.append((f"{source_name}.{validated_path}", False))
                        continue
                elif source_name == "video_review" and validated_path.startswith("acceptance_gates."):
                    ok = video_gate_results.get(validated_path)
                    if ok is None:
                        gate_checks.append((f"{source_name}.{validated_path}", False))
                        continue
                else:
                    if gate_kind == "bool":
                        ok_value = _expect_bool_path_soft(payload, validated_path, source_name, dependency_blockers)
                    else:
                        ok_value = _expect_pass_path_soft(payload, validated_path, source_name, dependency_blockers)
                    ok = bool(ok_value) if ok_value is not None else False
                gate_checks.append((f"{source_name}.{gate_path}", ok))
                if not ok:
                    failing_evidence.append(f"required upstream gate not passing: {source_name}.{gate_path}")

        if not release_allowed and promotion_decision_classification in {"canonical_release_allowed"}:
            dependency_blockers.append("release gate decision classification is inconsistent with release_allowed set")

        for source_name in ("image_review", "video_review", "strict_audio_report", "global_audio_report", "av_sync_report"):
            _collect_structured_blockers(payloads[source_name], source_name, "blockers", dependency_blockers)
        _collect_structured_blockers(
            payloads["global_audio_report"], "global_audio_report", "review_lineage_blockers", dependency_blockers
        )

        strict_final_status = _expect_str_path_soft(
            payloads["strict_audio_report"], "final_decision.overall_status", "strict_audio_report", dependency_blockers
        )
        global_final_status = _expect_str_path_soft(
            payloads["global_audio_report"], "final_decision.overall_status", "global_audio_report", dependency_blockers
        )
        strict_final_pass = strict_final_status == "PASS"
        global_final_pass = global_final_status == "PASS"
        if strict_final_status is not None and not strict_final_pass:
            failing_evidence.append("strict_audio_report final decision is not PASS")
        if global_final_status is not None and not global_final_pass:
            failing_evidence.append("global_audio_report final decision is not PASS")

        dependency_blockers.extend(lineage_blockers)
        dependency_blockers = sorted(set(dependency_blockers))
        failing_evidence = sorted(set(failing_evidence))

        strict_producer_payload = payloads["strict_audio_report"].get("producer_identities")
        if production_authority_exact_match:
            if not isinstance(strict_producer_payload, dict):
                dependency_blockers.append("strict_audio_report.producer_identities missing or non-object for production claim")
            else:
                producer_keys = (
                    "prompt_alignment_producer_id",
                    "playback_review_producer_id",
                    "production_review_producer_id",
                )
                for key in producer_keys:
                    producer_identity = strict_producer_payload.get(key)
                    if not isinstance(producer_identity, dict):
                        dependency_blockers.append(f"strict audio producer identity missing for {key}")
                        continue
                    authority_id = producer_identity.get("authority_id")
                    synthetic_only = producer_identity.get("synthetic_only")
                    if not isinstance(authority_id, str) or not authority_id.strip():
                        dependency_blockers.append(f"strict audio producer authority_id missing for {key}")
                    if synthetic_only is not False:
                        dependency_blockers.append(f"strict audio producer identity is synthetic for {key}")
                expected_ids = matched_production[0].get("expected_strict_audio_producer_ids") if matched_production else None
                if isinstance(expected_ids, dict):
                    for key in producer_keys:
                        actual = strict_producer_payload.get(key)
                        actual_authority_id = actual.get("authority_id") if isinstance(actual, dict) else None
                        if actual_authority_id != expected_ids.get(key):
                            dependency_blockers.append(f"strict audio producer identity mismatch for {key}")
            global_authority_evidence = payloads["global_audio_report"].get("production_authority_evidence")
            if not isinstance(global_authority_evidence, dict):
                dependency_blockers.append("global_audio_report.production_authority_evidence missing or non-object")
            else:
                for key in ("baseline_authority_match", "bundle_authority_match", "bundle_content_match"):
                    if global_authority_evidence.get(key) is not True:
                        dependency_blockers.append(f"global_audio_report.production_authority_evidence.{key} must be true")
            av_prod_pass = _expect_pass_path_soft(
                av_payload, "gates.production_av_sync_authority.status", "av_sync_report", dependency_blockers
            )
            if av_prod_pass is not True:
                dependency_blockers.append("av_sync_report production_av_sync_authority gate must be PASS for production claim")

        dependency_blockers = sorted(set(dependency_blockers))

        evidence_completeness_checks = [not dependency_blockers]
        quality_checks = [
            payloads["image_review"].get("overall_pass") is True,
            payloads["video_review"].get("overall_pass") is True,
            strict_final_pass,
            global_final_pass,
            payloads["av_sync_report"].get("overall_pass") is True,
        ]
        technical_integrity_checks = [not dependency_blockers, not failing_evidence, release_allowed]
        spec_checks = [item[1] for item in gate_checks]
        usability_checks = [
            image_gate_results.get("strict_decision.row_complete") is True,
            video_gate_results.get("strict_decision.row_complete") is True,
            strict_final_pass,
            global_final_pass,
            payloads["av_sync_report"].get("overall_pass") is True,
            release_allowed,
        ]
        image_checks = [
            payloads["image_review"].get("technical_pass") is True,
            image_gate_results.get("acceptance_gates.image_realism_check") is True,
            image_gate_results.get("acceptance_gates.anatomy_check") is True,
            image_gate_results.get("acceptance_gates.hyperreal_visual_review") is True,
            image_gate_results.get("acceptance_gates.global_visual_review") is True,
            image_gate_results.get("acceptance_gates.multi_sample_certification") is True,
        ]
        video_checks = [
            video_gate_results.get("acceptance_gates.temporal_identity_check") is True,
            video_gate_results.get("acceptance_gates.motion_consistency") is True,
            payloads["video_review"].get("overall_pass") is True,
        ]
        audio_checks = [
            strict_final_pass,
            global_final_pass,
            payloads["av_sync_report"].get("overall_pass") is True,
        ]
        prompt_checks = [
            image_gate_results.get("acceptance_gates.prompt_alignment_check") is True,
            image_gate_results.get("acceptance_gates.contamination_resistance_check") is True,
            _expect_pass_path_soft(payloads["strict_audio_report"], "gates.prompt_alignment", "strict_audio_report", dependency_blockers)
            is True,
            _expect_pass_path_soft(
                payloads["global_audio_report"], "gates.required_target_audio_check", "global_audio_report", dependency_blockers
            )
            is True,
        ]

        categories = [
            (
                "specification compliance",
                _score_from_checks(spec_checks),
                f"pass_ratio={sum(1 for item in spec_checks if item)}/{len(spec_checks)} across required upstream gates",
            ),
            (
                "technical integrity",
                _score_from_checks(technical_integrity_checks),
                f"dependency_blockers={len(dependency_blockers)}, present_failures={len(failing_evidence)}",
            ),
            (
                "quality level",
                _score_from_checks(quality_checks),
                f"quality_pass_ratio={sum(1 for item in quality_checks if item)}/{len(quality_checks)}",
            ),
            (
                "usability / deployability",
                _score_from_checks(usability_checks),
                f"deployability_pass_ratio={sum(1 for item in usability_checks if item)}/{len(usability_checks)}",
            ),
            (
                "evidence completeness",
                _score_from_checks(evidence_completeness_checks),
                f"trusted_prerequisites={'yes' if not dependency_blockers else 'no'}",
            ),
            (
                "image realism and anatomy",
                _score_from_checks(image_checks),
                f"image_pass_ratio={sum(1 for item in image_checks if item)}/{len(image_checks)}",
            ),
            (
                "video temporal consistency and motion realism",
                _score_from_checks(video_checks),
                f"video_pass_ratio={sum(1 for item in video_checks if item)}/{len(video_checks)}",
            ),
            (
                "audio clarity and content accuracy",
                _score_from_checks(audio_checks),
                f"audio_pass_ratio={sum(1 for item in audio_checks if item)}/{len(audio_checks)}",
            ),
            (
                "prompt control and contamination resistance",
                _score_from_checks(prompt_checks),
                f"prompt_pass_ratio={sum(1 for item in prompt_checks if item)}/{len(prompt_checks)}",
            ),
        ]

        required_categories = rules["required_categories"]
        min_required = int(rules["minimum_required_category_score"])
        score_by_name = {name: score for name, score, _ in categories}
        missing_required = [name for name in required_categories if name not in score_by_name]
        if missing_required:
            raise EvaluatorError(f"required categories are missing from computed scorecard: {missing_required}")
        all_required_meet_min = all(score_by_name[name] >= min_required for name in required_categories)
        required_upstream_gates_pass = not failing_evidence and not dependency_blockers

        caller_claimed = _expect_str(request_payload["caller_claimed_approval_decision"], "request.caller_claimed_approval_decision")
        if dependency_blockers:
            decision = "blocked"
            next_action = "Resolve missing/untrusted prerequisites and rerun strict multimodal aggregation."
        elif (not required_upstream_gates_pass) or (not all_required_meet_min) or failing_evidence:
            decision = "rejected"
            next_action = "Fix failing upstream evidence or category deficits, then resubmit the same bound records."
        else:
            if fixture_authority_exact_match and not production_authority_exact_match:
                nonblocking_defects.append("fixture-only authority path; non-production result")
                decision = "conditionally_approved"
                next_action = "Proceed with caution; convert fixture/nonblocking defects to production-safe evidence before release."
            else:
                decision = "approved"
                next_action = "Proceed with release packaging and downstream gates."

        exit_code = 0 if decision in {"approved", "conditionally_approved"} else 2
        production_eligible = bool(
            decision == "approved"
            and production_authority_exact_match
            and (not is_synthetic)
            and release_allowed
        )

        blockers = dependency_blockers if decision == "blocked" else []
        defects_summary = sorted(set(dependency_blockers + failing_evidence + nonblocking_defects))
        report_payload: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave64_multimodal_scorecard_report",
            "report_version": 1,
            "artifact_id": artifact_id,
            "reviewer_role": "Codex Desktop autonomous QA",
            "artifact_type": artifact_type,
            "generation_test_method": generation_test_method,
            "lineage": {
                "run_id": run_id,
                "scene_id": scene_id,
                "shot_id": shot_id,
                "take_id": take_id,
                "is_synthetic": is_synthetic,
                "lineage_match": not lineage_blockers,
            },
            "artifact_bindings": bindings,
            "validation": {
                "request_schema_valid": True,
                "upstream_schema_contracts_valid": True,
                "production_authority_exact_match": production_authority_exact_match,
                "fixture_authority_exact_match": fixture_authority_exact_match,
                "authority_release_binding_valid": authority_release_binding_valid,
                "authority_artifact_binding_valid": authority_artifact_binding_valid,
                "release_gate_decision_ref_binding_valid": release_decision_ref_valid,
                "source_identity_checks": source_identity_check_results,
                "source_identity_match": all(item.endswith("=ok") for item in source_identity_check_results),
                "lineage_checks": sorted(set(lineage_blockers)) or ["ok"],
                "binding_checks": [f"{name}:ok" for name in sorted(bindings.keys())],
            },
            "scorecard": {
                "categories": [
                    {"category": name, "score": score, "derivation": derivation}
                    for name, score, derivation in categories
                ],
                "required_categories": required_categories,
                "min_required_score": min_required,
                "all_required_categories_meet_minimum": all_required_meet_min,
            },
            "defects_summary": defects_summary,
            "approval_decision": decision,
            "next_action": next_action,
            "blockers": blockers,
            "production_eligibility": {
                "eligible_for_production": production_eligible,
                "fixture_only_result": fixture_authority_exact_match and not production_authority_exact_match,
                "authority_id": claim_authority,
                "bundle_id": claim_bundle,
            },
            "release_decision": {
                "promotion_decision": promotion_decision or "unknown_or_ill_typed",
                "classification": promotion_decision_classification,
                "is_release_allowed": release_allowed,
            },
            "final_decision": {
                "status": decision,
                "exit_code": exit_code,
            },
            "decision_derivation": {
                "caller_claim_ignored": True,
                "caller_claim_matches_recomputed": caller_claimed == decision,
                "required_upstream_gates_pass": required_upstream_gates_pass,
                "missing_or_untrusted_dependencies": dependency_blockers,
                "present_failing_evidence": failing_evidence,
                "nonblocking_defects": nonblocking_defects,
            },
        }
        _validate_with_schema(report_payload, report_schema, "report")
        _write_json_atomic(output_path, report_payload)
        print(str(output_path))
        return exit_code
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
