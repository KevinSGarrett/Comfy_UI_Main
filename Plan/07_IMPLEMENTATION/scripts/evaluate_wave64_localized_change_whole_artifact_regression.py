#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover
    Draft202012Validator = None  # type: ignore[assignment]


CANONICAL_ROOT = Path(__file__).resolve().parents[3]
REQUEST_SCHEMA = (
    CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_localized_change_whole_artifact_regression_request.schema.json"
)
REPORT_SCHEMA = (
    CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_localized_change_whole_artifact_regression_report.schema.json"
)
RULES_PATH = CANONICAL_ROOT / "Plan/10_REGISTRIES/wave64_localized_change_whole_artifact_regression_rules.json"
ROW033_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_multimodal_scorecard_report.schema.json"
ROW032_SCHEMA = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave64_global_audio_review_report.schema.json"
WAVE33_CONTRACT = CANONICAL_ROOT / "Plan/08_SCHEMAS/wave33_preview_qa_report.schema.json"
REVIEWER_ROLE = "Codex Desktop autonomous QA"


class EvaluatorError(ValueError):
    pass


class OperationalError(RuntimeError):
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
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OperationalError(f"failed reading JSON file {path}: {exc}") from exc
    try:
        return json.loads(
            raw,
            parse_constant=_reject_nonfinite_json,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except json.JSONDecodeError as exc:
        raise EvaluatorError(f"invalid JSON in {path}: {exc}") from exc


def _validate_with_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    if Draft202012Validator is None:
        raise OperationalError("jsonschema Draft 2020-12 validation is unavailable")
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


def _stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        os.unlink(temporary)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


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
    return value


def _expect_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise EvaluatorError(f"{label} must be integer")
    return value


def _expect_float(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvaluatorError(f"{label} must be number")
    out = float(value)
    if not math.isfinite(out):
        raise EvaluatorError(f"{label} must be finite")
    return out


def _expect_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvaluatorError(f"{label} must be an object")
    return value


def _expect_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise EvaluatorError(f"{label} must be a list")
    return value


def _expect_sha256(value: Any, label: str) -> str:
    sha = _expect_str(value, label)
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise EvaluatorError(f"{label} must be lowercase SHA-256")
    return sha


def _expect_keys(obj: dict[str, Any], required: set[str], label: str) -> None:
    observed = set(obj.keys())
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
    obj = _expect_dict(binding, label)
    _expect_keys(obj, {"path", "sha256", "bytes"}, label)
    path = _resolve_under_root(_expect_str(obj["path"], f"{label}.path"), f"{label}.path")
    sha = _expect_sha256(obj["sha256"], f"{label}.sha256")
    size = _expect_int(obj["bytes"], f"{label}.bytes")
    if size <= 0:
        raise EvaluatorError(f"{label}.bytes must be positive")
    if not path.is_file():
        raise EvaluatorError(f"{label}.path does not exist: {path}")
    observed_size = path.stat().st_size
    observed_sha = _sha256_of(path)
    if observed_size != size:
        raise EvaluatorError(f"{label}.bytes mismatch ({size} != {observed_size})")
    if observed_sha != sha:
        raise EvaluatorError(f"{label}.sha256 mismatch ({sha} != {observed_sha})")
    return {"path": str(path), "sha256": sha, "bytes": size}


def _relative_binding(binding: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": Path(binding["path"]).resolve().relative_to(CANONICAL_ROOT).as_posix(),
        "sha256": binding["sha256"],
        "bytes": binding["bytes"],
    }


def _set_from_strings(value: Any, label: str) -> set[str]:
    out: set[str] = set()
    for idx, item in enumerate(_expect_list(value, label)):
        out.add(_expect_str(item, f"{label}[{idx}]"))
    return out


def _binding_matches_exact(obj: Any, expected: dict[str, Any], label: str) -> None:
    rec = _expect_dict(obj, label)
    _expect_keys(rec, {"path", "sha256", "bytes"}, label)
    if _expect_str(rec["path"], f"{label}.path") != expected["path"]:
        raise EvaluatorError(f"{label}.path mismatch")
    if _expect_sha256(rec["sha256"], f"{label}.sha256") != expected["sha256"]:
        raise EvaluatorError(f"{label}.sha256 mismatch")
    if _expect_int(rec["bytes"], f"{label}.bytes") != expected["bytes"]:
        raise EvaluatorError(f"{label}.bytes mismatch")


def _validate_embedded_binding_shape(obj: Any, label: str) -> None:
    rec = _expect_dict(obj, label)
    _expect_keys(rec, {"path", "sha256", "bytes"}, label)
    _expect_str(rec["path"], f"{label}.path")
    _expect_sha256(rec["sha256"], f"{label}.sha256")
    if _expect_int(rec["bytes"], f"{label}.bytes") <= 0:
        raise EvaluatorError(f"{label}.bytes must be positive")


def _parse_canonical_partitions(
    canonical: Any,
) -> tuple[dict[str, Any], set[str], set[str], str]:
    node = _expect_dict(canonical, "request.canonical_partitions")
    _expect_keys(
        node,
        {"visual_domain", "audio_domain", "visual_partitions", "audio_partitions"},
        "request.canonical_partitions",
    )

    visual_domain = _expect_dict(node["visual_domain"], "request.canonical_partitions.visual_domain")
    _expect_keys(
        visual_domain,
        {"total_frames", "width", "height", "timeline_start_frame", "timeline_end_frame"},
        "request.canonical_partitions.visual_domain",
    )
    total_frames = _expect_int(visual_domain["total_frames"], "request.canonical_partitions.visual_domain.total_frames")
    width = _expect_int(visual_domain["width"], "request.canonical_partitions.visual_domain.width")
    height = _expect_int(visual_domain["height"], "request.canonical_partitions.visual_domain.height")
    timeline_start = _expect_int(
        visual_domain["timeline_start_frame"], "request.canonical_partitions.visual_domain.timeline_start_frame"
    )
    timeline_end = _expect_int(
        visual_domain["timeline_end_frame"], "request.canonical_partitions.visual_domain.timeline_end_frame"
    )
    if total_frames <= 0 or width <= 0 or height <= 0:
        raise EvaluatorError("request.canonical_partitions.visual_domain dimensions must be positive")
    if timeline_start != 0 or timeline_end != total_frames - 1:
        raise EvaluatorError("request.canonical_partitions.visual_domain timeline must exactly cover [0,total_frames-1]")

    audio_domain = _expect_dict(node["audio_domain"], "request.canonical_partitions.audio_domain")
    _expect_keys(
        audio_domain,
        {"total_samples", "sample_rate_hz", "channel_count", "duration_seconds"},
        "request.canonical_partitions.audio_domain",
    )
    total_samples = _expect_int(audio_domain["total_samples"], "request.canonical_partitions.audio_domain.total_samples")
    sample_rate = _expect_int(audio_domain["sample_rate_hz"], "request.canonical_partitions.audio_domain.sample_rate_hz")
    channel_count = _expect_int(audio_domain["channel_count"], "request.canonical_partitions.audio_domain.channel_count")
    duration_seconds = _expect_float(
        audio_domain["duration_seconds"], "request.canonical_partitions.audio_domain.duration_seconds"
    )
    if total_samples <= 0 or sample_rate <= 0 or channel_count <= 0:
        raise EvaluatorError("request.canonical_partitions.audio_domain dimensions must be positive")
    expected_duration = total_samples / sample_rate
    if abs(duration_seconds - expected_duration) > 1e-6:
        raise EvaluatorError("request.canonical_partitions.audio_domain duration_seconds mismatch with sample_rate_hz")

    visual_ids: set[str] = set()
    audio_ids: set[str] = set()
    all_ids: set[str] = set()

    visual_parts: list[tuple[int, int, str]] = []
    for idx, item in enumerate(_expect_list(node["visual_partitions"], "request.canonical_partitions.visual_partitions")):
        part = _expect_dict(item, f"request.canonical_partitions.visual_partitions[{idx}]")
        _expect_keys(
            part,
            {"partition_id", "start_frame", "end_frame", "x", "y", "width", "height"},
            f"request.canonical_partitions.visual_partitions[{idx}]",
        )
        pid = _expect_str(part["partition_id"], f"request.canonical_partitions.visual_partitions[{idx}].partition_id")
        if pid in all_ids:
            raise EvaluatorError(f"duplicate partition_id across domains: {pid}")
        start = _expect_int(part["start_frame"], f"request.canonical_partitions.visual_partitions[{idx}].start_frame")
        end = _expect_int(part["end_frame"], f"request.canonical_partitions.visual_partitions[{idx}].end_frame")
        px = _expect_int(part["x"], f"request.canonical_partitions.visual_partitions[{idx}].x")
        py = _expect_int(part["y"], f"request.canonical_partitions.visual_partitions[{idx}].y")
        pw = _expect_int(part["width"], f"request.canonical_partitions.visual_partitions[{idx}].width")
        ph = _expect_int(part["height"], f"request.canonical_partitions.visual_partitions[{idx}].height")
        if start < 0 or end < 0 or start > end:
            raise EvaluatorError(f"invalid visual frame range in partition {pid}")
        if end >= total_frames:
            raise EvaluatorError(f"visual partition {pid} exceeds total_frames")
        if px < 0 or py < 0 or pw <= 0 or ph <= 0:
            raise EvaluatorError(f"invalid visual geometry in partition {pid}")
        if px + pw > width or py + ph > height:
            raise EvaluatorError(f"visual partition {pid} rectangle exceeds visual domain bounds")
        all_ids.add(pid)
        visual_ids.add(pid)
        visual_parts.append((start, end, pid))

    audio_parts: list[tuple[int, int, str]] = []
    for idx, item in enumerate(_expect_list(node["audio_partitions"], "request.canonical_partitions.audio_partitions")):
        part = _expect_dict(item, f"request.canonical_partitions.audio_partitions[{idx}]")
        _expect_keys(
            part,
            {
                "partition_id",
                "start_sample",
                "end_sample",
                "start_seconds",
                "end_seconds",
                "channel_start",
                "channel_end",
                "sample_rate_hz",
                "channel_count",
            },
            f"request.canonical_partitions.audio_partitions[{idx}]",
        )
        pid = _expect_str(part["partition_id"], f"request.canonical_partitions.audio_partitions[{idx}].partition_id")
        if pid in all_ids:
            raise EvaluatorError(f"duplicate partition_id across domains: {pid}")
        start = _expect_int(part["start_sample"], f"request.canonical_partitions.audio_partitions[{idx}].start_sample")
        end = _expect_int(part["end_sample"], f"request.canonical_partitions.audio_partitions[{idx}].end_sample")
        start_t = _expect_float(part["start_seconds"], f"request.canonical_partitions.audio_partitions[{idx}].start_seconds")
        end_t = _expect_float(part["end_seconds"], f"request.canonical_partitions.audio_partitions[{idx}].end_seconds")
        ch_start = _expect_int(part["channel_start"], f"request.canonical_partitions.audio_partitions[{idx}].channel_start")
        ch_end = _expect_int(part["channel_end"], f"request.canonical_partitions.audio_partitions[{idx}].channel_end")
        part_sr = _expect_int(part["sample_rate_hz"], f"request.canonical_partitions.audio_partitions[{idx}].sample_rate_hz")
        part_channels = _expect_int(
            part["channel_count"], f"request.canonical_partitions.audio_partitions[{idx}].channel_count"
        )
        if part_sr != sample_rate or part_channels != channel_count:
            raise EvaluatorError(f"audio partition {pid} sample_rate_hz/channel_count mismatch with audio domain")
        if start < 0 or end < 0 or start > end:
            raise EvaluatorError(f"invalid audio sample range in partition {pid}")
        if end >= total_samples:
            raise EvaluatorError(f"audio partition {pid} exceeds total_samples")
        if ch_start < 0 or ch_end < ch_start or ch_end >= channel_count:
            raise EvaluatorError(f"audio partition {pid} has invalid channel range")
        expected_start_t = start / sample_rate
        expected_end_t = (end + 1) / sample_rate
        if abs(start_t - expected_start_t) > 1e-6 or abs(end_t - expected_end_t) > 1e-6:
            raise EvaluatorError(f"audio partition {pid} sample/time conversion mismatch")
        all_ids.add(pid)
        audio_ids.add(pid)
        audio_parts.append((start, end, pid))

    def _check_coverage(parts: list[tuple[int, int, str]], max_end: int, label: str) -> None:
        if not parts:
            raise EvaluatorError(f"{label} must be non-empty")
        sorted_parts = sorted(parts, key=lambda x: (x[0], x[1], x[2]))
        if sorted_parts[0][0] != 0:
            raise EvaluatorError(f"{label} must start at 0")
        if sorted_parts[-1][1] != max_end:
            raise EvaluatorError(f"{label} must end at {max_end}")
        prev_end = -1
        for start, end, pid in sorted_parts:
            if start <= prev_end:
                raise EvaluatorError(f"{label} overlap at partition {pid}")
            if prev_end >= 0 and start != prev_end + 1:
                raise EvaluatorError(f"{label} gap detected before partition {pid}")
            prev_end = end

    _check_coverage(visual_parts, total_frames - 1, "visual partitions")
    _check_coverage(audio_parts, total_samples - 1, "audio partitions")
    digest = _stable_sha256(node)
    return node, visual_ids, audio_ids, digest


def _parse_finding(
    item: Any,
    label: str,
    finding_ids_seen: set[str],
    allowed_ids: set[str],
    classifications: set[str],
    severities: set[str],
    dispositions: set[str],
) -> tuple[str, bool]:
    finding = _expect_dict(item, label)
    _expect_keys(
        finding,
        {"finding_id", "partition_id", "classification", "severity", "baseline_present", "candidate_present", "disposition"},
        label,
    )
    finding_id = _expect_str(finding["finding_id"], f"{label}.finding_id")
    if finding_id in finding_ids_seen:
        raise EvaluatorError(f"duplicate finding_id across arrays: {finding_id}")
    finding_ids_seen.add(finding_id)
    partition_id = _expect_str(finding["partition_id"], f"{label}.partition_id")
    if partition_id not in allowed_ids:
        raise EvaluatorError(f"{label}.partition_id not in canonical partition set: {partition_id}")
    classification = _expect_str(finding["classification"], f"{label}.classification")
    severity = _expect_str(finding["severity"], f"{label}.severity")
    disposition = _expect_str(finding["disposition"], f"{label}.disposition")
    baseline_present = _expect_bool(finding["baseline_present"], f"{label}.baseline_present")
    candidate_present = _expect_bool(finding["candidate_present"], f"{label}.candidate_present")
    if classification not in classifications:
        raise EvaluatorError(f"{label}.classification unsupported: {classification}")
    if severity not in severities:
        raise EvaluatorError(f"{label}.severity unsupported: {severity}")
    if disposition not in dispositions:
        raise EvaluatorError(f"{label}.disposition unsupported: {disposition}")
    allowed_dispositions = {
        (False, False): {"pass"},
        (False, True): {"new_defect", "regression"},
        (True, False): {"resolved"},
        (True, True): {"unresolved", "persisting"},
    }
    if disposition not in allowed_dispositions[(baseline_present, candidate_present)]:
        raise EvaluatorError(
            f"{label}.disposition {disposition} contradicts "
            f"baseline_present={baseline_present}/candidate_present={candidate_present}"
        )
    regression = (
        (candidate_present and not baseline_present and disposition in {"new_defect", "regression"})
        or (candidate_present and baseline_present and disposition in {"unresolved", "persisting"})
    )
    return finding_id, regression


def _path_type(path: str) -> str:
    return "audio" if path.endswith(".wav") else "visual"


def _build_report(
    req: dict[str, Any],
    bindings: dict[str, Any],
    blockers: list[str],
    failures: list[str],
    material_change: bool,
    gates: dict[str, bool],
    claim_authority: str,
    claim_bundle: str,
    authority_match_kind: str,
    prod_match: bool,
    fixture_match: bool,
    attempt_number: int,
    similar_failure_count: int,
    attempt_policy_ok: bool,
    change_summary_hash: str,
    canonical_partition_digest: str,
    attempt_history_digest: str,
    producer_id: str,
    reviewer_id: str,
    unverified_binding_names: list[str],
) -> dict[str, Any]:
    blockers = sorted(set(blockers))
    failures = sorted(set(failures))
    required_gates = ["before_after_delta", "target_region_pass", "global_region_pass", "unrelated_defect_scan", "audio_visual_regression_scan", "reject_on_new_defect"]
    all_required_gates = all(gates.get(name, False) for name in required_gates)

    if failures:
        decision = "rejected"
    elif all_required_gates and not blockers and material_change and prod_match:
        decision = "approved"
    elif all_required_gates and not blockers and material_change and fixture_match and not prod_match:
        decision = "conditionally_approved"
    else:
        decision = "blocked"
    exit_code = 0 if decision in {"approved", "conditionally_approved"} else 2

    report_payload: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_name": "wave64_localized_change_whole_artifact_regression_report",
        "report_version": 3,
        "tracker_id": req["tracker_id"],
        "item_id": req["item_id"],
        "regression_id": req["regression_id"],
        "change_id": req["change_id"],
        "lineage": {
            "scene_id": req["scene_id"],
            "shot_id": req["shot_id"],
            "take_id": req["take_id"],
            "baseline_artifact_id": req["baseline_artifact_id"],
            "candidate_artifact_id": req["candidate_artifact_id"],
            "baseline_run_id": req["baseline_run_id"],
            "candidate_run_id": req["candidate_run_id"],
            "review_run_id": req["review_run_id"],
            "producer_id": producer_id,
            "reviewer_id": reviewer_id,
            "reviewer_role": REVIEWER_ROLE,
        },
        "artifact_bindings": bindings,
        "validation": {
            "request_schema_valid": True,
            "upstream_contracts_valid": len(blockers) == 0,
            "unverified_artifact_binding_names": sorted(set(unverified_binding_names)),
            "material_change_recomputed": material_change,
            "change_summary_hash": change_summary_hash,
            "change_kind": req["change_kind"],
            "audio_change_expected": req["audio_change_expected"],
            "canonical_partition_digest": canonical_partition_digest,
            "attempt_history_digest": attempt_history_digest,
            "authority_match_kind": authority_match_kind,
            "authority_exact_match": prod_match or fixture_match,
            "production_authority_exact_match": prod_match,
            "fixture_authority_exact_match": fixture_match,
            "mask_authority_promoted": False,
            "candidate_masks_used_as_truth": False,
            "wave70_hard_gate_claimed": False,
            "wave71_activated": False,
        },
        "recomputed_gate_results": gates,
        "decision": decision,
        "production_eligibility": {
            "eligible_for_production": decision == "approved" and prod_match,
            "fixture_only_result": decision == "conditionally_approved" and fixture_match and not prod_match,
            "authority_id": claim_authority,
            "bundle_id": claim_bundle,
        },
        "protocol": {
            "attempt_number": attempt_number,
            "similar_failure_count": similar_failure_count,
            "attempt_policy_ok": attempt_policy_ok,
        },
        "defects_summary": sorted(set(failures + blockers)),
        "blockers": blockers,
        "final_decision": {"status": decision, "exit_code": exit_code},
    }
    return report_payload


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
        request_schema = _expect_dict(_load_json_strict(REQUEST_SCHEMA), "request_schema")
        report_schema = _expect_dict(_load_json_strict(REPORT_SCHEMA), "report_schema")
        row033_schema = _expect_dict(_load_json_strict(ROW033_SCHEMA), "row033_schema")
        row032_schema = _expect_dict(_load_json_strict(ROW032_SCHEMA), "row032_schema")
        wave33_contract = _expect_dict(_load_json_strict(WAVE33_CONTRACT), "wave33_contract")
        rules = _expect_dict(_load_json_strict(RULES_PATH), "rules")
        _validate_with_schema(request_payload, request_schema, "request")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    try:
        req_output_path = _resolve_under_root(
            _expect_str(request_payload["output_report_path"], "request.output_report_path"),
            "request.output_report_path",
        )
        if req_output_path != output_path:
            raise EvaluatorError("request.output_report_path must exactly match --output path")

        req = {
            "tracker_id": _expect_str(request_payload["tracker_id"], "request.tracker_id"),
            "item_id": _expect_str(request_payload["item_id"], "request.item_id"),
            "regression_id": _expect_str(request_payload["regression_id"], "request.regression_id"),
            "change_id": _expect_str(request_payload["change_id"], "request.change_id"),
            "scene_id": _expect_str(request_payload["scene_id"], "request.scene_id"),
            "shot_id": _expect_str(request_payload["shot_id"], "request.shot_id"),
            "take_id": _expect_str(request_payload["take_id"], "request.take_id"),
            "baseline_artifact_id": _expect_str(request_payload["baseline_artifact_id"], "request.baseline_artifact_id"),
            "candidate_artifact_id": _expect_str(request_payload["candidate_artifact_id"], "request.candidate_artifact_id"),
            "baseline_run_id": _expect_str(request_payload["baseline_run_id"], "request.baseline_run_id"),
            "candidate_run_id": _expect_str(request_payload["candidate_run_id"], "request.candidate_run_id"),
            "review_run_id": _expect_str(request_payload["review_run_id"], "request.review_run_id"),
            "change_kind": _expect_str(request_payload["change_kind"], "request.change_kind"),
            "audio_change_expected": _expect_bool(request_payload["audio_change_expected"], "request.audio_change_expected"),
        }
        claim = _expect_dict(request_payload["production_authority_claim"], "request.production_authority_claim")
        _expect_keys(claim, {"authority_id", "bundle_id"}, "request.production_authority_claim")
        claim_authority = _expect_str(claim["authority_id"], "request.production_authority_claim.authority_id")
        claim_bundle = _expect_str(claim["bundle_id"], "request.production_authority_claim.bundle_id")

        matrix = _expect_dict(rules["change_kind_audio_expectation_matrix"], "rules.change_kind_audio_expectation_matrix")
        if req["change_kind"] not in matrix:
            raise EvaluatorError(f"unsupported change_kind: {req['change_kind']}")
        if _expect_bool(matrix[req["change_kind"]], f"rules.change_kind_audio_expectation_matrix.{req['change_kind']}") != req["audio_change_expected"]:
            raise EvaluatorError("change_kind/audio_change_expected mismatch with canonical rules")

        raw_bindings = _expect_dict(request_payload["bindings"], "request.bindings")
        bindings: dict[str, dict[str, Any]] = {}
        binding_blockers: list[str] = []
        unverified_binding_names: list[str] = []
        binding_integrity_ok = True
        for name, raw_binding in raw_bindings.items():
            binding_obj = _expect_dict(raw_binding, f"request.bindings.{name}")
            binding_path = _resolve_under_root(
                _expect_str(binding_obj["path"], f"request.bindings.{name}.path"),
                f"request.bindings.{name}.path",
            )
            fallback_binding = {
                "path": str(binding_path),
                "sha256": _expect_sha256(binding_obj["sha256"], f"request.bindings.{name}.sha256"),
                "bytes": _expect_int(binding_obj["bytes"], f"request.bindings.{name}.bytes"),
            }
            try:
                bindings[name] = _resolve_binding(binding_obj, f"request.bindings.{name}")
            except (EvaluatorError, OSError) as exc:
                binding_integrity_ok = False
                bindings[name] = fallback_binding
                unverified_binding_names.append(name)
                binding_blockers.append(f"untrusted top-level binding {name}: {exc}")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    blockers: list[str] = list(binding_blockers)
    failures: list[str] = []
    change_summary_hash = "0" * 64
    canonical_partition_digest = "0" * 64
    attempt_history_digest = "0" * 64
    material_change = False
    authority_match_kind = "none"
    prod_match = False
    fixture_match = False
    attempt_number = 1
    similar_failure_count = 0
    attempt_policy_ok = False
    producer_id = ""
    reviewer_id = ""
    gates = {
        "before_after_delta": False,
        "target_region_pass": False,
        "global_region_pass": False,
        "unrelated_defect_scan": False,
        "audio_visual_regression_scan": False,
        "reject_on_new_defect": False,
    }

    try:
        if not binding_integrity_ok:
            raise EvaluatorError("top-level binding integrity verification failed")
        json_binding_names = [
            "baseline_row033_report_binding",
            "candidate_row033_report_binding",
            "row032_global_audio_report_binding",
            "wave33_preview_qa_binding",
            "baseline_artifact_manifest_binding",
            "candidate_artifact_manifest_binding",
            "failure_record_binding",
            "retest_record_binding",
            "whole_artifact_delta_binding",
            "whole_artifact_review_binding",
            "runtime_proof_binding",
            "change_manifest_binding",
        ]
        payloads = {
            name: _load_json_strict(Path(bindings[name]["path"]))
            for name in json_binding_names
        }

        row033_base = _expect_dict(payloads["baseline_row033_report_binding"], "baseline_row033")
        row033_cand = _expect_dict(payloads["candidate_row033_report_binding"], "candidate_row033")
        row032 = _expect_dict(payloads["row032_global_audio_report_binding"], "row032")
        wave33 = _expect_dict(payloads["wave33_preview_qa_binding"], "wave33")
        manifest_base = _expect_dict(payloads["baseline_artifact_manifest_binding"], "baseline_manifest")
        manifest_cand = _expect_dict(payloads["candidate_artifact_manifest_binding"], "candidate_manifest")
        delta = _expect_dict(payloads["whole_artifact_delta_binding"], "delta")
        review = _expect_dict(payloads["whole_artifact_review_binding"], "review")
        runtime = _expect_dict(payloads["runtime_proof_binding"], "runtime_proof")
        change_manifest = _expect_dict(payloads["change_manifest_binding"], "change_manifest")
        failure_record = _expect_dict(payloads["failure_record_binding"], "failure_record")
        retest_record = _expect_dict(payloads["retest_record_binding"], "retest_record")

        for label, payload, schema in (
            ("baseline_row033", row033_base, row033_schema),
            ("candidate_row033", row033_cand, row033_schema),
            ("row032", row032, row032_schema),
        ):
            _validate_with_schema(payload, schema, label)

        canonical_partitions, visual_ids, audio_ids, canonical_partition_digest = _parse_canonical_partitions(
            request_payload["canonical_partitions"]
        )
        canonical_ids = visual_ids | audio_ids
        target_ids = _set_from_strings(request_payload["target_partition_ids"], "request.target_partition_ids")
        non_target_ids = _set_from_strings(request_payload["non_target_partition_ids"], "request.non_target_partition_ids")
        if target_ids & non_target_ids:
            blockers.append("target and non-target partition sets must be disjoint")
        if target_ids | non_target_ids != canonical_ids:
            blockers.append("target/non-target partition union must exactly equal canonical partition IDs")

        _expect_keys(
            change_manifest,
            {
                "schema_name",
                "change_kind",
                "audio_change_expected",
                "baseline_primary_media",
                "candidate_primary_media",
                "canonical_partition_digest",
                "canonical_target_partition_ids",
                "change_summary_hash",
                "partition_changes",
            },
            "change_manifest",
        )
        if _expect_str(change_manifest["schema_name"], "change_manifest.schema_name") != "wave64_localized_change_manifest":
            blockers.append("change_manifest schema_name mismatch")
        if _expect_str(change_manifest["change_kind"], "change_manifest.change_kind") != req["change_kind"]:
            blockers.append("change_manifest change_kind mismatch")
        if _expect_bool(change_manifest["audio_change_expected"], "change_manifest.audio_change_expected") != req["audio_change_expected"]:
            blockers.append("change_manifest audio_change_expected mismatch")
        _binding_matches_exact(change_manifest["baseline_primary_media"], bindings["baseline_primary_media_binding"], "change_manifest.baseline_primary_media")
        _binding_matches_exact(change_manifest["candidate_primary_media"], bindings["candidate_primary_media_binding"], "change_manifest.candidate_primary_media")
        if _expect_sha256(change_manifest["canonical_partition_digest"], "change_manifest.canonical_partition_digest") != canonical_partition_digest:
            blockers.append("change_manifest canonical partition digest mismatch")
        if _set_from_strings(change_manifest["canonical_target_partition_ids"], "change_manifest.canonical_target_partition_ids") != target_ids:
            blockers.append("change_manifest canonical target set mismatch")

        change_summary_hash = _expect_sha256(change_manifest["change_summary_hash"], "change_manifest.change_summary_hash")
        partition_changes = _expect_list(change_manifest["partition_changes"], "change_manifest.partition_changes")
        mapped_ids: set[str] = set()
        partition_change_detected = False
        for idx, item in enumerate(partition_changes):
            part = _expect_dict(item, f"change_manifest.partition_changes[{idx}]")
            _expect_keys(
                part,
                {
                    "partition_id",
                    "mapped_from_partition_id",
                    "change_summary_hash",
                    "before_sha256",
                    "after_sha256",
                    "before_region_hash",
                    "after_region_hash",
                    "visual_region",
                    "audio_region",
                },
                f"change_manifest.partition_changes[{idx}]",
            )
            pid = _expect_str(part["partition_id"], f"change_manifest.partition_changes[{idx}].partition_id")
            mapped_from = _expect_str(
                part["mapped_from_partition_id"], f"change_manifest.partition_changes[{idx}].mapped_from_partition_id"
            )
            if pid in mapped_ids:
                blockers.append(f"change_manifest duplicate mapped partition_id: {pid}")
            mapped_ids.add(pid)
            if pid != mapped_from:
                blockers.append(f"change_manifest mapped_from_partition_id mismatch for {pid}")
            if pid not in target_ids:
                blockers.append(f"change_manifest partition_id outside target set: {pid}")
            part_summary = _expect_sha256(
                part["change_summary_hash"], f"change_manifest.partition_changes[{idx}].change_summary_hash"
            )
            if part_summary != change_summary_hash:
                blockers.append("change_manifest partition change_summary_hash mismatch")

            before_sha = _expect_sha256(part["before_sha256"], f"change_manifest.partition_changes[{idx}].before_sha256")
            after_sha = _expect_sha256(part["after_sha256"], f"change_manifest.partition_changes[{idx}].after_sha256")
            before_region_hash = _expect_sha256(
                part["before_region_hash"], f"change_manifest.partition_changes[{idx}].before_region_hash"
            )
            after_region_hash = _expect_sha256(
                part["after_region_hash"], f"change_manifest.partition_changes[{idx}].after_region_hash"
            )

            visual_region = _expect_dict(part["visual_region"], f"change_manifest.partition_changes[{idx}].visual_region")
            _expect_keys(
                visual_region,
                {"x", "y", "width", "height", "start_frame", "end_frame"},
                f"change_manifest.partition_changes[{idx}].visual_region",
            )
            audio_region = _expect_dict(part["audio_region"], f"change_manifest.partition_changes[{idx}].audio_region")
            _expect_keys(
                audio_region,
                {
                    "start_sample",
                    "end_sample",
                    "start_seconds",
                    "end_seconds",
                    "channel_start",
                    "channel_end",
                    "sample_rate_hz",
                    "channel_count",
                },
                f"change_manifest.partition_changes[{idx}].audio_region",
            )

            vis = {p["partition_id"]: p for p in _expect_list(canonical_partitions["visual_partitions"], "visual_partitions")}
            aud = {p["partition_id"]: p for p in _expect_list(canonical_partitions["audio_partitions"], "audio_partitions")}
            if pid in vis:
                v = vis[pid]
                vstart = _expect_int(visual_region["start_frame"], "visual_region.start_frame")
                vend = _expect_int(visual_region["end_frame"], "visual_region.end_frame")
                if vstart < v["start_frame"] or vend > v["end_frame"] or vstart > vend:
                    blockers.append(f"change_manifest visual range out of bounds for {pid}")
            if pid in aud:
                a = aud[pid]
                astart = _expect_int(audio_region["start_sample"], "audio_region.start_sample")
                aend = _expect_int(audio_region["end_sample"], "audio_region.end_sample")
                if astart < a["start_sample"] or aend > a["end_sample"] or astart > aend:
                    blockers.append(f"change_manifest audio range out of bounds for {pid}")

            if before_sha != after_sha or before_region_hash != after_region_hash:
                partition_change_detected = True
        if mapped_ids != target_ids:
            blockers.append("change_manifest partition mapping must exactly match canonical target partitions")
        primary_media_changed = (
            bindings["baseline_primary_media_binding"]["sha256"]
            != bindings["candidate_primary_media_binding"]["sha256"]
        )
        material_change = partition_change_detected and primary_media_changed
        if partition_change_detected and not primary_media_changed:
            blockers.append("material change requires distinct baseline and candidate primary-media SHA-256")

        for manifest, label, art, run, media in (
            (manifest_base, "baseline_manifest", req["baseline_artifact_id"], req["baseline_run_id"], bindings["baseline_primary_media_binding"]),
            (manifest_cand, "candidate_manifest", req["candidate_artifact_id"], req["candidate_run_id"], bindings["candidate_primary_media_binding"]),
        ):
            _expect_keys(
                manifest,
                {
                    "schema_name",
                    "artifact_id",
                    "run_id",
                    "scene_id",
                    "shot_id",
                    "take_id",
                    "is_synthetic",
                    "primary_media",
                    "canonical_partition_digest",
                    "partition_ids",
                    "domain_descriptor",
                },
                label,
            )
            if _expect_str(manifest["schema_name"], f"{label}.schema_name") != "wave64_artifact_manifest":
                blockers.append(f"{label} schema_name mismatch")
            if _expect_str(manifest["artifact_id"], f"{label}.artifact_id") != art:
                blockers.append(f"{label} artifact_id mismatch")
            if _expect_str(manifest["run_id"], f"{label}.run_id") != run:
                blockers.append(f"{label} run_id mismatch")
            if _expect_str(manifest["scene_id"], f"{label}.scene_id") != req["scene_id"]:
                blockers.append(f"{label} scene_id mismatch")
            if _expect_str(manifest["shot_id"], f"{label}.shot_id") != req["shot_id"]:
                blockers.append(f"{label} shot_id mismatch")
            if _expect_str(manifest["take_id"], f"{label}.take_id") != req["take_id"]:
                blockers.append(f"{label} take_id mismatch")
            if _expect_bool(manifest["is_synthetic"], f"{label}.is_synthetic"):
                blockers.append(f"{label} is_synthetic must be false")
            _binding_matches_exact(manifest["primary_media"], media, f"{label}.primary_media")
            if _expect_sha256(manifest["canonical_partition_digest"], f"{label}.canonical_partition_digest") != canonical_partition_digest:
                blockers.append(f"{label} canonical partition digest mismatch")
            if _set_from_strings(manifest["partition_ids"], f"{label}.partition_ids") != canonical_ids:
                blockers.append(f"{label} partition IDs mismatch")
            if _expect_dict(manifest["domain_descriptor"], f"{label}.domain_descriptor") != canonical_partitions:
                blockers.append(f"{label} domain descriptor mismatch")

        finding_enums = _expect_dict(rules["finding_enums"], "rules.finding_enums")
        classifications = _set_from_strings(finding_enums["classification"], "rules.finding_enums.classification")
        severities = _set_from_strings(finding_enums["severity"], "rules.finding_enums.severity")
        dispositions = _set_from_strings(finding_enums["disposition"], "rules.finding_enums.disposition")

        _expect_keys(
            delta,
            {
                "schema_name",
                "target_partition_ids",
                "non_target_partition_ids",
                "visual_alignment_transform_verified",
                "audio_alignment_transform_verified",
                "target_findings",
                "unrelated_findings",
                "baseline_primary_media",
                "candidate_primary_media",
                "canonical_partition_digest",
            },
            "delta",
        )
        _expect_keys(
            review,
            {
                "schema_name",
                "regression_id",
                "change_id",
                "scene_id",
                "shot_id",
                "take_id",
                "baseline_artifact_id",
                "candidate_artifact_id",
                "baseline_run_id",
                "candidate_run_id",
                "review_run_id",
                "target_partition_ids",
                "non_target_partition_ids",
                "visual_alignment_transform_verified",
                "audio_alignment_transform_verified",
                "target_only_review",
                "candidate_masks_used_as_truth",
                "audio_target_proof",
                "audio_non_target_proof",
                "row032_no_audio_change_identity_proof",
                "target_findings",
                "unrelated_findings",
                "reviewer_identity",
                "baseline_primary_media",
                "candidate_primary_media",
                "canonical_partition_digest",
                "change_manifest_binding",
            },
            "review",
        )
        _expect_keys(
            runtime,
            {
                "schema_name",
                "regression_id",
                "change_id",
                "scene_id",
                "shot_id",
                "take_id",
                "baseline_artifact_id",
                "candidate_artifact_id",
                "baseline_run_id",
                "candidate_run_id",
                "review_run_id",
                "identity",
                "baseline_primary_media",
                "candidate_primary_media",
                "canonical_partition_digest",
                "upstream_report_bindings",
                "change_manifest_binding",
            },
            "runtime_proof",
        )
        contracts = _expect_dict(rules["contracts"], "rules.contracts")
        for label, record, contract_key in (
            ("delta", delta, "whole_artifact_delta_schema_name"),
            ("review", review, "whole_artifact_review_schema_name"),
            ("runtime_proof", runtime, "runtime_proof_schema_name"),
        ):
            expected_schema_name = _expect_str(contracts[contract_key], f"rules.contracts.{contract_key}")
            if _expect_str(record["schema_name"], f"{label}.schema_name") != expected_schema_name:
                blockers.append(f"{label} schema_name mismatch")

        if _set_from_strings(delta["target_partition_ids"], "delta.target_partition_ids") != target_ids:
            blockers.append("delta target partition IDs mismatch")
        if _set_from_strings(delta["non_target_partition_ids"], "delta.non_target_partition_ids") != non_target_ids:
            blockers.append("delta non-target partition IDs mismatch")
        if _set_from_strings(review["target_partition_ids"], "review.target_partition_ids") != target_ids:
            blockers.append("review target partition IDs mismatch")
        if _set_from_strings(review["non_target_partition_ids"], "review.non_target_partition_ids") != non_target_ids:
            blockers.append("review non-target partition IDs mismatch")

        for label, record in (("delta", delta), ("review", review), ("runtime_proof", runtime)):
            if _expect_sha256(record["canonical_partition_digest"], f"{label}.canonical_partition_digest") != canonical_partition_digest:
                blockers.append(f"{label} canonical partition digest mismatch")
            _binding_matches_exact(record["baseline_primary_media"], bindings["baseline_primary_media_binding"], f"{label}.baseline_primary_media")
            _binding_matches_exact(record["candidate_primary_media"], bindings["candidate_primary_media_binding"], f"{label}.candidate_primary_media")

        if not _expect_bool(delta["visual_alignment_transform_verified"], "delta.visual_alignment_transform_verified"):
            blockers.append("delta visual_alignment_transform_verified must be true")
        if not _expect_bool(delta["audio_alignment_transform_verified"], "delta.audio_alignment_transform_verified"):
            blockers.append("delta audio_alignment_transform_verified must be true")
        if not _expect_bool(review["visual_alignment_transform_verified"], "review.visual_alignment_transform_verified"):
            blockers.append("review visual_alignment_transform_verified must be true")
        if not _expect_bool(review["audio_alignment_transform_verified"], "review.audio_alignment_transform_verified"):
            blockers.append("review audio_alignment_transform_verified must be true")
        if _expect_bool(review["target_only_review"], "review.target_only_review"):
            blockers.append("target_only_review must be false")
        if _expect_bool(review["candidate_masks_used_as_truth"], "review.candidate_masks_used_as_truth"):
            blockers.append("candidate_masks_used_as_truth must be false")
        if req["audio_change_expected"]:
            if not _expect_bool(review["audio_target_proof"], "review.audio_target_proof"):
                blockers.append("audio_target_proof required when audio_change_expected=true")
            if not _expect_bool(review["audio_non_target_proof"], "review.audio_non_target_proof"):
                blockers.append("audio_non_target_proof required when audio_change_expected=true")
        elif not _expect_bool(review["row032_no_audio_change_identity_proof"], "review.row032_no_audio_change_identity_proof"):
            blockers.append("row032_no_audio_change_identity_proof required when audio_change_expected=false")

        delta_target_findings = _expect_list(delta["target_findings"], "delta.target_findings")
        delta_unrelated_findings = _expect_list(delta["unrelated_findings"], "delta.unrelated_findings")
        review_target_findings = _expect_list(review["target_findings"], "review.target_findings")
        review_unrelated_findings = _expect_list(review["unrelated_findings"], "review.unrelated_findings")

        delta_seen: set[str] = set()
        review_seen: set[str] = set()
        delta_target_ids: set[str] = set()
        delta_unrelated_ids: set[str] = set()
        review_target_ids: set[str] = set()
        review_unrelated_ids: set[str] = set()
        target_regressions = 0
        unrelated_regressions = 0
        for idx, item in enumerate(delta_target_findings):
            fid, reg = _parse_finding(
                item,
                f"delta.target_findings[{idx}]",
                delta_seen,
                target_ids,
                classifications,
                severities,
                dispositions,
            )
            delta_target_ids.add(fid)
            target_regressions += 1 if reg else 0
        for idx, item in enumerate(delta_unrelated_findings):
            fid, reg = _parse_finding(
                item,
                f"delta.unrelated_findings[{idx}]",
                delta_seen,
                non_target_ids,
                classifications,
                severities,
                dispositions,
            )
            delta_unrelated_ids.add(fid)
            unrelated_regressions += 1 if reg else 0
        for idx, item in enumerate(review_target_findings):
            fid, reg = _parse_finding(
                item,
                f"review.target_findings[{idx}]",
                review_seen,
                target_ids,
                classifications,
                severities,
                dispositions,
            )
            review_target_ids.add(fid)
            target_regressions += 1 if reg else 0
        for idx, item in enumerate(review_unrelated_findings):
            fid, reg = _parse_finding(
                item,
                f"review.unrelated_findings[{idx}]",
                review_seen,
                non_target_ids,
                classifications,
                severities,
                dispositions,
            )
            review_unrelated_ids.add(fid)
            unrelated_regressions += 1 if reg else 0
        if delta_target_ids != review_target_ids:
            blockers.append("delta/review target finding-ID mismatch")
        if delta_unrelated_ids != review_unrelated_ids:
            blockers.append("delta/review unrelated finding-ID mismatch")
        if delta_target_ids & delta_unrelated_ids:
            blockers.append("delta finding IDs must not overlap between target and unrelated arrays")
        if review_target_ids & review_unrelated_ids:
            blockers.append("review finding IDs must not overlap between target and unrelated arrays")
        if target_regressions > 0:
            failures.append("target regressions present")
        if unrelated_regressions > 0:
            failures.append("unrelated regressions present")

        for label, row033, exp_art, exp_run, manifest_binding_name in (
            (
                "baseline_row033",
                row033_base,
                req["baseline_artifact_id"],
                req["baseline_run_id"],
                "baseline_artifact_manifest_binding",
            ),
            (
                "candidate_row033",
                row033_cand,
                req["candidate_artifact_id"],
                req["candidate_run_id"],
                "candidate_artifact_manifest_binding",
            ),
        ):
            if _expect_str(row033["artifact_id"], f"{label}.artifact_id") != exp_art:
                blockers.append(f"{label}.artifact_id mismatch")
            lineage = _expect_dict(row033["lineage"], f"{label}.lineage")
            if _expect_str(lineage["run_id"], f"{label}.lineage.run_id") != exp_run:
                blockers.append(f"{label}.lineage.run_id mismatch")
            for field in ("scene_id", "shot_id", "take_id"):
                if _expect_str(lineage[field], f"{label}.lineage.{field}") != req[field]:
                    blockers.append(f"{label}.lineage.{field} mismatch")
            if _expect_bool(lineage["is_synthetic"], f"{label}.lineage.is_synthetic"):
                blockers.append(f"{label}.lineage.is_synthetic must be false")
            if not _expect_bool(lineage["lineage_match"], f"{label}.lineage.lineage_match"):
                blockers.append(f"{label}.lineage.lineage_match must be true")
            if _expect_str(row033["reviewer_role"], f"{label}.reviewer_role") != REVIEWER_ROLE:
                blockers.append(f"{label}.reviewer_role mismatch")
            validation = _expect_dict(row033["validation"], f"{label}.validation")
            for field in (
                "request_schema_valid",
                "upstream_schema_contracts_valid",
                "production_authority_exact_match",
                "authority_release_binding_valid",
                "authority_artifact_binding_valid",
                "release_gate_decision_ref_binding_valid",
                "source_identity_match",
            ):
                if not _expect_bool(validation[field], f"{label}.validation.{field}"):
                    blockers.append(f"{label}.validation.{field} must be true")
            if _expect_bool(validation["fixture_authority_exact_match"], f"{label}.validation.fixture_authority_exact_match"):
                blockers.append(f"{label}.validation.fixture_authority_exact_match must be false")
            _binding_matches_exact(
                _expect_dict(row033["artifact_bindings"], f"{label}.artifact_bindings")["artifact_manifest"],
                bindings[manifest_binding_name],
                f"{label}.artifact_bindings.artifact_manifest",
            )
            if _expect_list(row033["defects_summary"], f"{label}.defects_summary"):
                failures.append(f"{label} defects_summary must be empty")
            if _expect_list(row033["blockers"], f"{label}.blockers"):
                blockers.append(f"{label}.blockers must be empty")
            if _expect_str(row033["approval_decision"], f"{label}.approval_decision") != _expect_str(
                rules["required_row033_approval_decision"], "rules.required_row033_approval_decision"
            ):
                failures.append(f"{label} approval decision mismatch")
            final_decision = _expect_dict(row033["final_decision"], f"{label}.final_decision")
            if _expect_str(final_decision["status"], f"{label}.final_decision.status") != "approved":
                failures.append(f"{label} final status mismatch")
            if _expect_int(final_decision["exit_code"], f"{label}.final_decision.exit_code") != 0:
                failures.append(f"{label} final exit code mismatch")
            prod_elig = _expect_dict(row033["production_eligibility"], f"{label}.production_eligibility")
            if not _expect_bool(prod_elig["eligible_for_production"], f"{label}.production_eligibility.eligible_for_production"):
                failures.append(f"{label} not production eligible")
            release = _expect_dict(row033["release_decision"], f"{label}.release_decision")
            if not _expect_bool(release["is_release_allowed"], f"{label}.release_decision.is_release_allowed"):
                failures.append(f"{label} release is not allowed")
            if _expect_str(release["classification"], f"{label}.release_decision.classification") != "canonical_release_allowed":
                failures.append(f"{label} release classification mismatch")
            derivation = _expect_dict(row033["decision_derivation"], f"{label}.decision_derivation")
            for field in ("caller_claim_ignored", "caller_claim_matches_recomputed", "required_upstream_gates_pass"):
                if not _expect_bool(derivation[field], f"{label}.decision_derivation.{field}"):
                    blockers.append(f"{label}.decision_derivation.{field} must be true")
            for field in ("missing_or_untrusted_dependencies", "present_failing_evidence"):
                if _expect_list(derivation[field], f"{label}.decision_derivation.{field}"):
                    blockers.append(f"{label}.decision_derivation.{field} must be empty")

        if _expect_str(row032["baseline_run_id"], "row032.baseline_run_id") != req["baseline_run_id"]:
            blockers.append("row032 baseline_run_id mismatch")
        if _expect_str(row032["candidate_run_id"], "row032.candidate_run_id") != req["candidate_run_id"]:
            blockers.append("row032 candidate_run_id mismatch")
        if _expect_str(row032["review_run_id"], "row032.review_run_id") != req["review_run_id"]:
            blockers.append("row032 review_run_id mismatch")
        if _expect_bool(row032["is_synthetic"], "row032.is_synthetic"):
            blockers.append("row032 is_synthetic must be false")
        row032_context = _expect_dict(row032["localized_change_context"], "row032.localized_change_context")
        expected_row032_change_kind = "audio_localized" if req["audio_change_expected"] else "visual_localized"
        if _expect_str(row032_context["change_kind"], "row032.localized_change_context.change_kind") != expected_row032_change_kind:
            blockers.append("row032 localized change_kind mismatch")
        if _expect_bool(
            row032_context["audio_change_expected"],
            "row032.localized_change_context.audio_change_expected",
        ) != req["audio_change_expected"]:
            blockers.append("row032 localized audio_change_expected mismatch")
        row032_gates = _expect_dict(row032["gates"], "row032.gates")
        for gate_name, gate_value in row032_gates.items():
            if _expect_str(gate_value, f"row032.gates.{gate_name}") != "PASS":
                failures.append(f"row032 gate {gate_name} must be PASS")
        row032_final = _expect_dict(row032["final_decision"], "row032.final_decision")
        if _expect_str(row032_final["overall_status"], "row032.final_decision.overall_status") != _expect_str(
            rules["required_row032_overall_status"], "rules.required_row032_overall_status"
        ):
            failures.append("row032 overall_status mismatch")
        if _expect_int(row032_final["exit_code"], "row032.final_decision.exit_code") != 0:
            failures.append("row032 final exit_code must be 0")
        if len(_expect_list(row032["blockers"], "row032.blockers")) != 0:
            blockers.append("row032 blockers must be empty")
        if len(_expect_list(row032["review_lineage_blockers"], "row032.review_lineage_blockers")) != 0:
            blockers.append("row032 review_lineage_blockers must be empty")
        prod_auth = _expect_dict(row032["production_authority_evidence"], "row032.production_authority_evidence")
        _expect_keys(
            prod_auth,
            {"baseline_authority_match", "bundle_authority_match", "bundle_content_match"},
            "row032.production_authority_evidence",
        )
        if not all(_expect_bool(prod_auth[k], f"row032.production_authority_evidence.{k}") for k in prod_auth):
            failures.append("row032 production authority booleans must all be true")
        no_audio_kinds = _set_from_strings(
            rules["no_audio_identity_required_change_kinds"], "rules.no_audio_identity_required_change_kinds"
        )
        if req["change_kind"] in no_audio_kinds and not req["audio_change_expected"]:
            bmix = _expect_dict(row032["artifact_bindings"]["baseline_mix_wav"], "row032.artifact_bindings.baseline_mix_wav")
            cmix = _expect_dict(row032["artifact_bindings"]["candidate_mix_wav"], "row032.artifact_bindings.candidate_mix_wav")
            if _expect_sha256(bmix["sha256"], "row032.artifact_bindings.baseline_mix_wav.sha256") != _expect_sha256(
                cmix["sha256"], "row032.artifact_bindings.candidate_mix_wav.sha256"
            ):
                failures.append("row032 no-audio identity hash mismatch")
            if _expect_int(bmix["bytes"], "row032.artifact_bindings.baseline_mix_wav.bytes") != _expect_int(
                cmix["bytes"], "row032.artifact_bindings.candidate_mix_wav.bytes"
            ):
                failures.append("row032 no-audio identity bytes mismatch")

        _expect_keys(
            wave33_contract,
            {"schema_name", "required_fields", "promotion_decisions"},
            "wave33_contract",
        )
        wave33_contract_name = _expect_str(wave33_contract["schema_name"], "wave33_contract.schema_name")
        if wave33_contract_name != _expect_str(
            contracts["wave33_preview_contract_schema_name"],
            "rules.contracts.wave33_preview_contract_schema_name",
        ):
            raise EvaluatorError("Wave33 canonical contract name disagrees with registry")
        wave33_required_fields = _set_from_strings(
            wave33_contract["required_fields"], "wave33_contract.required_fields"
        )
        wave33_identity_fields = {
            "candidate_artifact_id",
            "candidate_run_id",
            "scene_id",
            "shot_id",
            "take_id",
        }
        _expect_keys(wave33, {"schema_name"} | wave33_required_fields | wave33_identity_fields, "wave33")
        if _expect_str(wave33["schema_name"], "wave33.schema_name") != wave33_contract_name:
            blockers.append("wave33 schema_name mismatch")
        _expect_str(wave33["preview_qa_id"], "wave33.preview_qa_id")
        _expect_str(wave33["preview_id"], "wave33.preview_id")
        wave33_artifacts = _expect_dict(wave33["artifacts"], "wave33.artifacts")
        _expect_keys(
            wave33_artifacts,
            {"candidate_primary_media", "candidate_artifact_manifest_binding"},
            "wave33.artifacts",
        )
        _binding_matches_exact(
            wave33_artifacts["candidate_primary_media"],
            bindings["candidate_primary_media_binding"],
            "wave33.artifacts.candidate_primary_media",
        )
        _binding_matches_exact(
            wave33_artifacts["candidate_artifact_manifest_binding"],
            bindings["candidate_artifact_manifest_binding"],
            "wave33.artifacts.candidate_artifact_manifest_binding",
        )
        rerun_recommendation = _expect_str(wave33["rerun_recommendation"], "wave33.rerun_recommendation")
        if _expect_str(wave33["candidate_artifact_id"], "wave33.candidate_artifact_id") != req["candidate_artifact_id"]:
            blockers.append("wave33 candidate_artifact_id mismatch")
        if _expect_str(wave33["candidate_run_id"], "wave33.candidate_run_id") != req["candidate_run_id"]:
            blockers.append("wave33 candidate_run_id mismatch")
        for field in ("scene_id", "shot_id", "take_id"):
            if _expect_str(wave33[field], f"wave33.{field}") != req[field]:
                blockers.append(f"wave33 {field} mismatch")
        scores = _expect_dict(wave33["scores"], "wave33.scores")
        _expect_keys(scores, {"overall"}, "wave33.scores")
        overall = _expect_float(scores["overall"], "wave33.scores.overall")
        if overall < 0 or overall > 1:
            blockers.append("wave33.scores.overall must be in [0,1]")
        flags = _expect_dict(wave33["failure_flags"], "wave33.failure_flags")
        if not flags:
            blockers.append("wave33.failure_flags must be non-empty")
        for key, value in flags.items():
            _expect_bool(value, f"wave33.failure_flags.{key}")
            if value:
                failures.append("wave33 failure flag raised")
        wave33_promotion = _expect_str(wave33["promotion_decision"], "wave33.promotion_decision")
        canonical_wave33_decisions = _set_from_strings(
            wave33_contract["promotion_decisions"], "wave33_contract.promotion_decisions"
        )
        if wave33_promotion not in canonical_wave33_decisions:
            blockers.append("wave33 promotion_decision is outside canonical contract")
        if wave33_promotion != _expect_str(
            rules["required_wave33_promotion_decision"], "rules.required_wave33_promotion_decision"
        ):
            failures.append("wave33 promotion decision mismatch")
        if wave33_promotion == "pass_preview" and rerun_recommendation != "none":
            blockers.append("wave33 pass_preview requires rerun_recommendation=none")
        if overall < _expect_float(rules["required_wave33_score_floor"], "rules.required_wave33_score_floor"):
            failures.append("wave33 score below floor")

        reviewer_identity = _expect_dict(review["reviewer_identity"], "review.reviewer_identity")
        _expect_keys(reviewer_identity, {"reviewer_id", "reviewer_role"}, "review.reviewer_identity")
        reviewer_id = _expect_str(reviewer_identity["reviewer_id"], "review.reviewer_identity.reviewer_id")
        if _expect_str(reviewer_identity["reviewer_role"], "review.reviewer_identity.reviewer_role") != REVIEWER_ROLE:
            blockers.append("reviewer_role mismatch")
        runtime_identity = _expect_dict(runtime["identity"], "runtime_proof.identity")
        _expect_keys(runtime_identity, {"producer_id"}, "runtime_proof.identity")
        producer_id = _expect_str(runtime_identity["producer_id"], "runtime_proof.identity.producer_id")
        if producer_id == reviewer_id:
            blockers.append("producer_id and reviewer_id must differ")
        for field in (
            "regression_id",
            "change_id",
            "scene_id",
            "shot_id",
            "take_id",
            "baseline_artifact_id",
            "candidate_artifact_id",
            "baseline_run_id",
            "candidate_run_id",
            "review_run_id",
        ):
            if _expect_str(review[field], f"review.{field}") != req[field]:
                blockers.append(f"review {field} mismatch")
            if _expect_str(runtime[field], f"runtime_proof.{field}") != req[field]:
                blockers.append(f"runtime_proof {field} mismatch")

        _binding_matches_exact(
            review["change_manifest_binding"], bindings["change_manifest_binding"], "review.change_manifest_binding"
        )
        _binding_matches_exact(
            runtime["change_manifest_binding"], bindings["change_manifest_binding"], "runtime_proof.change_manifest_binding"
        )
        upstream_bindings = _expect_dict(runtime["upstream_report_bindings"], "runtime_proof.upstream_report_bindings")
        _expect_keys(
            upstream_bindings,
            {"row032_global_audio_report_binding", "baseline_row033_report_binding", "candidate_row033_report_binding"},
            "runtime_proof.upstream_report_bindings",
        )
        for key in upstream_bindings:
            _binding_matches_exact(upstream_bindings[key], bindings[key], f"runtime_proof.upstream_report_bindings.{key}")

        protocol_blocker_count_before = len(blockers)
        _expect_keys(
            failure_record,
            {
                "schema_name",
                "failure_id",
                "failure_classification",
                "severity",
                "suspected_cause",
                "change_hash",
                "expected_result_hash",
                "original_failure_binding",
            },
            "failure_record",
        )
        _expect_keys(
            retest_record,
            {
                "schema_name",
                "retest_id",
                "failure_id",
                "attempt_number",
                "change_hash",
                "expected_result_hash",
                "material_change",
                "final_decision",
            },
            "retest_record",
        )
        if _expect_str(failure_record["schema_name"], "failure_record.schema_name") != _expect_str(
            contracts["failure_record_schema_name"], "rules.contracts.failure_record_schema_name"
        ):
            blockers.append("failure_record schema_name mismatch")
        if _expect_str(retest_record["schema_name"], "retest_record.schema_name") != _expect_str(
            contracts["retest_record_schema_name"], "rules.contracts.retest_record_schema_name"
        ):
            blockers.append("retest_record schema_name mismatch")
        required_failure_classes = _set_from_strings(
            rules["required_failure_classifications"], "rules.required_failure_classifications"
        )
        if _expect_str(failure_record["failure_classification"], "failure_record.failure_classification") not in required_failure_classes:
            blockers.append("failure_record.failure_classification unsupported")
        if _expect_str(failure_record["failure_id"], "failure_record.failure_id") != _expect_str(
            retest_record["failure_id"], "retest_record.failure_id"
        ):
            blockers.append("failure_record/retest_record failure_id mismatch")
        _expect_sha256(failure_record["change_hash"], "failure_record.change_hash")
        _expect_sha256(failure_record["expected_result_hash"], "failure_record.expected_result_hash")
        _validate_embedded_binding_shape(failure_record["original_failure_binding"], "failure_record.original_failure_binding")

        attempts_node = _expect_dict(request_payload["attempt_history"], "request.attempt_history")
        _expect_keys(
            attempts_node,
            {"attempts", "attempt_history_digest", "deeper_diagnosis", "new_direction_hash"},
            "request.attempt_history",
        )
        attempts = _expect_list(attempts_node["attempts"], "request.attempt_history.attempts")
        attempt_history_digest = _expect_sha256(
            attempts_node["attempt_history_digest"], "request.attempt_history.attempt_history_digest"
        )
        if attempt_history_digest != _stable_sha256(attempts):
            blockers.append("request.attempt_history.attempt_history_digest mismatch")

        last_number = 0
        seen_direction_hashes: set[str] = set()
        diagnosis_hashes: set[str] = set()
        for idx, item in enumerate(attempts):
            rec = _expect_dict(item, f"request.attempt_history.attempts[{idx}]")
            _expect_keys(
                rec,
                {
                    "attempt_number",
                    "failure_classification",
                    "severity",
                    "diagnosis_id",
                    "diagnosis_hash",
                    "change_hash",
                    "expected_result_hash",
                    "change_summary_hash",
                    "result",
                    "result_report_binding",
                    "similar_to_current",
                    "new_direction_hash",
                },
                f"request.attempt_history.attempts[{idx}]",
            )
            n = _expect_int(rec["attempt_number"], f"request.attempt_history.attempts[{idx}].attempt_number")
            if n != idx + 1:
                blockers.append("attempt numbers must be sequential starting at 1")
            last_number = max(last_number, n)
            if _expect_str(rec["failure_classification"], f"request.attempt_history.attempts[{idx}].failure_classification") not in required_failure_classes:
                blockers.append("attempt failure_classification unsupported")
            _expect_str(rec["severity"], f"request.attempt_history.attempts[{idx}].severity")
            _expect_str(rec["diagnosis_id"], f"request.attempt_history.attempts[{idx}].diagnosis_id")
            diag_hash = _expect_sha256(rec["diagnosis_hash"], f"request.attempt_history.attempts[{idx}].diagnosis_hash")
            diagnosis_hashes.add(diag_hash)
            _expect_sha256(rec["change_hash"], f"request.attempt_history.attempts[{idx}].change_hash")
            _expect_sha256(rec["expected_result_hash"], f"request.attempt_history.attempts[{idx}].expected_result_hash")
            historical_change_summary_hash = _expect_sha256(
                rec["change_summary_hash"],
                f"request.attempt_history.attempts[{idx}].change_summary_hash",
            )
            result = _expect_str(rec["result"], f"request.attempt_history.attempts[{idx}].result")
            if result not in {"failed", "passed", "blocked"}:
                blockers.append("attempt result unsupported")
            _binding_matches_exact(
                rec["result_report_binding"],
                bindings["whole_artifact_review_binding"],
                f"request.attempt_history.attempts[{idx}].result_report_binding",
            )
            declared_similar = _expect_bool(
                rec["similar_to_current"],
                f"request.attempt_history.attempts[{idx}].similar_to_current",
            )
            derived_similar = historical_change_summary_hash == change_summary_hash
            if declared_similar != derived_similar:
                blockers.append(
                    f"attempt {n} similar_to_current contradicts change_summary_hash comparison"
                )
            effective_similar = derived_similar or declared_similar
            direction_hash = _expect_sha256(
                rec["new_direction_hash"], f"request.attempt_history.attempts[{idx}].new_direction_hash"
            )
            seen_direction_hashes.add(direction_hash)
            if result == "failed" and effective_similar:
                similar_failure_count += 1
        attempt_number = last_number + 1 if attempts else 1

        deeper = _expect_dict(attempts_node["deeper_diagnosis"], "request.attempt_history.deeper_diagnosis")
        _expect_keys(
            deeper,
            {"diagnosis_hash", "binding"},
            "request.attempt_history.deeper_diagnosis",
        )
        deeper_hash = _expect_sha256(deeper["diagnosis_hash"], "request.attempt_history.deeper_diagnosis.diagnosis_hash")
        _binding_matches_exact(
            deeper["binding"],
            bindings["retest_record_binding"],
            "request.attempt_history.deeper_diagnosis.binding",
        )
        new_direction_hash = _expect_sha256(
            attempts_node["new_direction_hash"], "request.attempt_history.new_direction_hash"
        )
        if similar_failure_count >= 2:
            if deeper_hash in diagnosis_hashes:
                blockers.append("deeper diagnosis hash must be new on third similar failure")
            if new_direction_hash in seen_direction_hashes:
                blockers.append("new direction hash must be new on third similar failure")
        if similar_failure_count >= 3:
            blockers.append("three or more prior similar failures block the fourth attempt pending redesign")

        if _expect_int(retest_record["attempt_number"], "retest_record.attempt_number") != attempt_number:
            blockers.append("retest_record.attempt_number mismatch")
        if _expect_sha256(retest_record["change_hash"], "retest_record.change_hash") != change_summary_hash:
            blockers.append("retest_record.change_hash must equal change_summary_hash")
        _expect_sha256(retest_record["expected_result_hash"], "retest_record.expected_result_hash")
        if _expect_bool(retest_record["material_change"], "retest_record.material_change") != material_change:
            blockers.append("retest_record.material_change mismatch")
        if _expect_str(retest_record["final_decision"], "retest_record.final_decision") not in {"approved", "conditionally_approved", "rejected", "blocked"}:
            blockers.append("retest_record.final_decision unsupported")
        attempt_policy_ok = len(blockers) == protocol_blocker_count_before

        authority_rules = _expect_dict(rules["authority_rules"], "rules.authority_rules")
        prod_objects = _expect_list(authority_rules["production_authority_exact_objects"], "rules.authority_rules.production_authority_exact_objects")
        fixture_objects = _expect_list(authority_rules["fixture_authority_exact_objects"], "rules.authority_rules.fixture_authority_exact_objects")
        seen_pairs: set[tuple[str, str]] = set()
        seen_prod_pairs: set[tuple[str, str]] = set()
        seen_fixture_pairs: set[tuple[str, str]] = set()
        def _authority_pair(value: Any) -> tuple[str, str] | None:
            if not isinstance(value, dict):
                return None
            authority_id = value.get("authority_id")
            bundle_id = value.get("bundle_id")
            if not isinstance(authority_id, str) or not authority_id.strip():
                return None
            if not isinstance(bundle_id, str) or not bundle_id.strip():
                return None
            return authority_id.strip(), bundle_id.strip()

        for obj in prod_objects:
            pair = _authority_pair(obj)
            if pair is None:
                continue
            if pair in seen_pairs:
                blockers.append("duplicate authority_id+bundle_id pair detected")
            seen_pairs.add(pair)
            seen_prod_pairs.add(pair)
        for obj in fixture_objects:
            pair = _authority_pair(obj)
            if pair is None:
                continue
            if pair in seen_pairs:
                blockers.append("duplicate authority_id+bundle_id pair detected")
            seen_pairs.add(pair)
            seen_fixture_pairs.add(pair)
        overlap = seen_prod_pairs & seen_fixture_pairs
        if overlap:
            blockers.append("production and fixture authority objects may not overlap")

        required_authority_keys = {
            "authority_id",
            "bundle_id",
            "regression_id",
            "change_id",
            "scene_id",
            "shot_id",
            "take_id",
            "baseline_artifact_id",
            "candidate_artifact_id",
            "baseline_run_id",
            "candidate_run_id",
            "review_run_id",
            "change_kind",
            "audio_change_expected",
            "current_attempt_number",
            "attempt_history_digest",
            "canonical_partition_digest",
            "producer_id",
            "reviewer_id",
            "reviewer_role",
            "change_summary_hash",
            "input_bindings",
        }
        def _matches_authority(authority_obj: Any, kind: str) -> bool:
            obj = _expect_dict(authority_obj, f"{kind}_authority")
            _expect_keys(obj, required_authority_keys, f"{kind}_authority")
            if _expect_str(obj["authority_id"], f"{kind}_authority.authority_id") != claim_authority:
                return False
            if _expect_str(obj["bundle_id"], f"{kind}_authority.bundle_id") != claim_bundle:
                return False
            for field in (
                "regression_id",
                "change_id",
                "scene_id",
                "shot_id",
                "take_id",
                "baseline_artifact_id",
                "candidate_artifact_id",
                "baseline_run_id",
                "candidate_run_id",
                "review_run_id",
                "change_kind",
            ):
                if obj[field] != req[field]:
                    return False
            if _expect_bool(obj["audio_change_expected"], f"{kind}_authority.audio_change_expected") != req["audio_change_expected"]:
                return False
            if _expect_int(obj["current_attempt_number"], f"{kind}_authority.current_attempt_number") != attempt_number:
                return False
            if _expect_sha256(obj["attempt_history_digest"], f"{kind}_authority.attempt_history_digest") != attempt_history_digest:
                return False
            if _expect_sha256(obj["canonical_partition_digest"], f"{kind}_authority.canonical_partition_digest") != canonical_partition_digest:
                return False
            if _expect_str(obj["producer_id"], f"{kind}_authority.producer_id") != producer_id:
                return False
            if _expect_str(obj["reviewer_id"], f"{kind}_authority.reviewer_id") != reviewer_id:
                return False
            if _expect_str(obj["reviewer_role"], f"{kind}_authority.reviewer_role") != REVIEWER_ROLE:
                return False
            if _expect_sha256(obj["change_summary_hash"], f"{kind}_authority.change_summary_hash") != change_summary_hash:
                return False
            input_bindings = _expect_dict(obj["input_bindings"], f"{kind}_authority.input_bindings")
            if set(input_bindings.keys()) != set(bindings.keys()):
                return False
            for name in bindings.keys():
                if _expect_dict(input_bindings[name], f"{kind}_authority.input_bindings.{name}") != _relative_binding(bindings[name]):
                    return False
            return True

        for item in prod_objects:
            if _authority_pair(item) != (claim_authority, claim_bundle):
                continue
            if _matches_authority(item, "production"):
                prod_match = True
                authority_match_kind = "production"
        for item in fixture_objects:
            if _authority_pair(item) != (claim_authority, claim_bundle):
                continue
            if _matches_authority(item, "fixture"):
                fixture_match = True
                if not prod_match:
                    authority_match_kind = "fixture"
        if not prod_match and not fixture_match:
            blockers.append("no exact production or fixture authority object matched the request")

        gates = {
            "before_after_delta": material_change,
            "target_region_pass": len([f for f in failures if "target regressions" in f]) == 0 and not blockers,
            "global_region_pass": not blockers,
            "unrelated_defect_scan": delta_unrelated_ids == review_unrelated_ids,
            "audio_visual_regression_scan": len(failures) == 0,
            "reject_on_new_defect": len([f for f in failures if "unrelated regressions" in f]) == 0,
        }
    except OperationalError as exc:
        print(f"ERROR: {exc}")
        return 1
    except EvaluatorError as exc:
        blockers.append(f"malformed nested custom record: {exc}")
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: operational failure: {exc}")
        return 1

    report_payload = _build_report(
        req=req,
        bindings=bindings,
        blockers=blockers,
        failures=failures,
        material_change=material_change,
        gates=gates,
        claim_authority=claim_authority,
        claim_bundle=claim_bundle,
        authority_match_kind=authority_match_kind,
        prod_match=prod_match,
        fixture_match=fixture_match,
        attempt_number=attempt_number,
        similar_failure_count=similar_failure_count,
        attempt_policy_ok=attempt_policy_ok,
        change_summary_hash=change_summary_hash,
        canonical_partition_digest=canonical_partition_digest,
        attempt_history_digest=attempt_history_digest,
        producer_id=producer_id or "unknown_producer",
        reviewer_id=reviewer_id or "unknown_reviewer",
        unverified_binding_names=unverified_binding_names,
    )

    try:
        _validate_with_schema(report_payload, _expect_dict(_load_json_strict(REPORT_SCHEMA), "report_schema"), "report")
        _write_json_atomic(output_path, report_payload)
        print(str(output_path))
        return _expect_int(report_payload["final_decision"]["exit_code"], "report.final_decision.exit_code")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
