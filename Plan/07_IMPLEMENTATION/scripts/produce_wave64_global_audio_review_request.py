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

from jsonschema import Draft202012Validator


CANONICAL_ROOT = Path("C:/Comfy_UI_Main").resolve()


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON: {value}")),
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside project root") from exc
    return path


def require_file(path: Path, label: str) -> None:
    if not path.is_file() or path.stat().st_size < 1:
        raise ValueError(f"{label} missing or empty: {path}")


def binding(path: Path) -> dict[str, Any]:
    return {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def link_only(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in ("path", "sha256")}


def require_identity(payload: dict[str, Any], label: str, run_id: str, is_synthetic: bool) -> None:
    if payload.get("run_id") != run_id:
        raise ValueError(f"{label}.run_id mismatch")
    if payload.get("is_synthetic") is not is_synthetic:
        raise ValueError(f"{label}.is_synthetic mismatch")


def parse_windows(raw_windows: list[str]) -> list[dict[str, float]]:
    result: list[dict[str, float]] = []
    previous_end = -1.0
    for index, raw in enumerate(raw_windows):
        parts = raw.split(":")
        if len(parts) != 2:
            raise ValueError(f"allowed_window[{index}] must be start:end")
        start, end = (float(part.strip()) for part in parts)
        if not math.isfinite(start) or not math.isfinite(end) or start < 0.0 or end <= start:
            raise ValueError(f"allowed_window[{index}] must be finite and end after start")
        if start < previous_end:
            raise ValueError("allowed windows must be ordered and non-overlapping")
        result.append({"start_seconds": start, "end_seconds": end})
        previous_end = end
    return result


def write_atomic_no_clobber(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        os.unlink(temporary)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def validate_side(
    side: str,
    paths: dict[str, Path],
    run_id: str,
    is_synthetic: bool,
    capture_mode: str,
) -> set[str]:
    wav = binding(paths[f"{side}_mix_wav"])
    event_binding = binding(paths[f"{side}_wave30_event_manifest"])
    mix_binding = binding(paths[f"{side}_wave30_mix_manifest"])
    qa_binding = binding(paths[f"{side}_wave30_qa_report"])
    event = load_json(paths[f"{side}_wave30_event_manifest"])
    mix = load_json(paths[f"{side}_wave30_mix_manifest"])
    qa = load_json(paths[f"{side}_wave30_qa_report"])
    row031 = load_json(paths[f"{side}_row031_strict_report"])
    if not all(isinstance(payload, dict) for payload in (event, mix, qa, row031)):
        raise ValueError(f"{side} JSON artifacts must contain objects")
    for label, payload in (("event", event), ("mix", mix), ("qa", qa)):
        require_identity(payload, f"{side}_{label}", run_id, is_synthetic)
    if mix.get("event_manifest_bindings") != [link_only(event_binding)]:
        raise ValueError(f"{side} mix event binding mismatch")
    mixdown = mix.get("mixdown_artifact")
    if not isinstance(mixdown, dict):
        raise ValueError(f"{side} mixdown artifact missing")
    for key in ("path", "sha256", "bytes"):
        if mixdown.get(key) != wav[key]:
            raise ValueError(f"{side} mixdown {key} mismatch")
    if qa.get("event_manifest_binding") != link_only(event_binding):
        raise ValueError(f"{side} QA event binding mismatch")
    if qa.get("mix_manifest_binding") != link_only(mix_binding):
        raise ValueError(f"{side} QA mix binding mismatch")
    if row031.get("schema_name") != "wave64_strict_audio_review_report":
        raise ValueError(f"{side} Row031 schema_name mismatch")
    require_identity(row031, f"{side}_row031", run_id, is_synthetic)
    if row031.get("capture_mode") != capture_mode:
        raise ValueError(f"{side} Row031 capture_mode mismatch")
    artifacts = row031.get("artifact_bindings")
    if not isinstance(artifacts, dict):
        raise ValueError(f"{side} Row031 artifact_bindings missing")
    expected = {
        "mix_wav": wav,
        "wave30_event_manifest": event_binding,
        "wave30_mix_manifest": mix_binding,
        "wave30_qa_report": qa_binding,
    }
    for field, expected_binding in expected.items():
        actual = artifacts.get(field)
        if not isinstance(actual, dict):
            raise ValueError(f"{side} Row031 {field} binding missing")
        for key in ("path", "sha256", "bytes"):
            if actual.get(key) != expected_binding[key]:
                raise ValueError(f"{side} Row031 {field}.{key} mismatch")
    events = event.get("audio_events")
    if not isinstance(events, list):
        raise ValueError(f"{side} audio_events must be an array")
    ids: list[str] = []
    for index, item in enumerate(events):
        if not isinstance(item, dict) or not isinstance(item.get("audio_event_id"), str) or not item["audio_event_id"]:
            raise ValueError(f"{side} audio_events[{index}].audio_event_id invalid")
        ids.append(item["audio_event_id"])
    if len(ids) != len(set(ids)):
        raise ValueError(f"{side} audio event IDs must be unique")
    return set(ids)


def produce(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    root = Path(args.root).resolve()
    if root != CANONICAL_ROOT:
        raise ValueError(f"root must match canonical project root ({CANONICAL_ROOT})")
    artifact_names = tuple(
        f"{side}_{suffix}"
        for side in ("baseline", "candidate")
        for suffix in (
            "mix_wav", "row031_strict_report", "wave30_event_manifest", "wave30_mix_manifest", "wave30_qa_report"
        )
    )
    paths = {name: resolve_under(root, Path(getattr(args, name)), name) for name in artifact_names}
    paths["optional_dir"] = resolve_under(root, Path(args.optional_dir), "optional_dir")
    paths["output"] = resolve_under(root, Path(args.output), "output")
    output_report = resolve_under(root, Path(args.output_report), "output_report")
    if paths["output"].exists():
        raise ValueError(f"output already exists: {paths['output']}")
    if output_report.exists():
        raise ValueError(f"output_report already exists: {output_report}")
    if paths["output"] == output_report:
        raise ValueError("request output and evaluator report output must differ")
    if not paths["optional_dir"].is_dir():
        raise ValueError("optional_dir missing")
    if paths["output"] == paths["optional_dir"] or paths["optional_dir"] in paths["output"].parents:
        raise ValueError("request output must not be inside optional_dir")
    for name in artifact_names:
        require_file(paths[name], name)
    if len({paths[name] for name in artifact_names}) != len(artifact_names):
        raise ValueError("all baseline and candidate artifacts must use distinct paths")

    ids = {
        "review_run_id": args.review_run_id.strip(),
        "baseline_run_id": args.baseline_run_id.strip(),
        "candidate_run_id": args.candidate_run_id.strip(),
    }
    if any(not value for value in ids.values()) or len(set(ids.values())) != 3:
        raise ValueError("review, baseline, and candidate run IDs must be non-empty and distinct")
    is_synthetic = not args.production_input
    baseline_events = validate_side("baseline", paths, ids["baseline_run_id"], is_synthetic, args.capture_mode)
    candidate_events = validate_side("candidate", paths, ids["candidate_run_id"], is_synthetic, args.capture_mode)
    if baseline_events != candidate_events:
        raise ValueError("baseline and candidate audio event ID sets must match")
    target_ids = list(dict.fromkeys(args.target_event_id))
    if len(target_ids) != len(args.target_event_id):
        raise ValueError("target event IDs must be unique")
    unknown_targets = set(target_ids) - candidate_events
    if unknown_targets:
        raise ValueError(f"unknown target event IDs: {','.join(sorted(unknown_targets))}")
    non_target_ids = sorted(candidate_events - set(target_ids))
    windows = parse_windows(args.allowed_window)
    if args.change_kind == "audio_localized" and (not args.audio_change_expected or not target_ids or not windows):
        raise ValueError("audio_localized requires expected audio change, target events, and windows")
    if args.change_kind == "visual_localized" and not args.audio_change_expected and (target_ids or windows):
        raise ValueError("visual_localized without audio change must not declare targets or windows")
    if args.audio_change_expected and (not target_ids or not windows):
        raise ValueError("expected audio change requires target events and windows")

    optional_bundle = paths["optional_dir"] / "production_bundle.json"
    production_binding = None
    if optional_bundle.is_file():
        require_file(optional_bundle, "production_bundle")
        bundle = load_json(optional_bundle)
        required_bundle_keys = {
            "schema_name", "schema_version", "bundle_id", "scene_id", "baseline_authority_id",
            "bundle_authority_id", "baseline_run_id", "candidate_run_id", "review_run_id", "synthetic_only",
            "baseline_mix_wav_sha256", "baseline_row031_sha256", "candidate_mix_wav_sha256",
            "candidate_row031_sha256", "candidate_wave30_qa_sha256",
        }
        if not isinstance(bundle, dict) or set(bundle) != required_bundle_keys:
            raise ValueError("production bundle keys mismatch")
        if bundle.get("schema_name") != "wave64_global_audio_production_bundle":
            raise ValueError("production bundle schema_name mismatch")
        if bundle.get("schema_version") != 1 or bundle.get("synthetic_only") is not False:
            raise ValueError("production bundle version or synthetic_only mismatch")
        for field in ("bundle_id", "scene_id", "baseline_authority_id", "bundle_authority_id"):
            if not isinstance(bundle.get(field), str) or not bundle[field].strip():
                raise ValueError(f"production bundle {field} must be non-empty")
        if bundle["baseline_authority_id"].casefold() == bundle["bundle_authority_id"].casefold():
            raise ValueError("production bundle authorities must be independent")
        if bundle.get("review_run_id") != ids["review_run_id"]:
            raise ValueError("production bundle review_run_id mismatch")
        if bundle.get("baseline_run_id") != ids["baseline_run_id"] or bundle.get("candidate_run_id") != ids["candidate_run_id"]:
            raise ValueError("production bundle baseline/candidate run mismatch")
        baseline_event = load_json(paths["baseline_wave30_event_manifest"])
        if not isinstance(baseline_event, dict) or bundle.get("scene_id") != baseline_event.get("scene_id"):
            raise ValueError("production bundle scene_id mismatch")
        expected_hashes = {
            "baseline_mix_wav_sha256": sha256(paths["baseline_mix_wav"]),
            "baseline_row031_sha256": sha256(paths["baseline_row031_strict_report"]),
            "candidate_mix_wav_sha256": sha256(paths["candidate_mix_wav"]),
            "candidate_row031_sha256": sha256(paths["candidate_row031_strict_report"]),
            "candidate_wave30_qa_sha256": sha256(paths["candidate_wave30_qa_report"]),
        }
        for field, expected in expected_hashes.items():
            if bundle.get(field) != expected:
                raise ValueError(f"production bundle {field} mismatch")
        production_binding = binding(optional_bundle)

    request = {
        "schema_name": "wave64_global_audio_review_request",
        "request_version": 1,
        **ids,
        "is_synthetic": is_synthetic,
        "capture_mode": args.capture_mode,
        **{f"{name}_binding": binding(paths[name]) for name in artifact_names},
        "localized_change_declaration": {
            "change_kind": args.change_kind,
            "audio_change_expected": args.audio_change_expected,
            "target_audio_event_ids": target_ids,
            "non_target_audio_event_ids": non_target_ids,
            "allowed_change_windows_seconds": windows,
        },
        "output_report_path": str(output_report),
    }
    if production_binding is not None:
        request["production_bundle_binding"] = production_binding
    schema = load_json(root / "Plan/08_SCHEMAS/wave64_global_audio_review_request.schema.json")
    Draft202012Validator(schema).validate(request)
    write_atomic_no_clobber(paths["output"], request)
    return paths["output"], request


def main() -> int:
    parser = argparse.ArgumentParser()
    for side in ("baseline", "candidate"):
        parser.add_argument(f"--{side}-mix-wav", required=True)
        parser.add_argument(f"--{side}-row031-strict-report", required=True)
        parser.add_argument(f"--{side}-wave30-event-manifest", required=True)
        parser.add_argument(f"--{side}-wave30-mix-manifest", required=True)
        parser.add_argument(f"--{side}-wave30-qa-report", required=True)
    parser.add_argument("--review-run-id", required=True)
    parser.add_argument("--baseline-run-id", required=True)
    parser.add_argument("--candidate-run-id", required=True)
    parser.add_argument("--change-kind", choices=("audio_localized", "visual_localized"), required=True)
    parser.add_argument("--audio-change-expected", action="store_true")
    parser.add_argument("--target-event-id", action="append", default=[])
    parser.add_argument("--allowed-window", action="append", default=[])
    parser.add_argument("--capture-mode", choices=("technical_capture", "hand_authored_relabel", "synthetic_fixture"), default="technical_capture")
    parser.add_argument("--optional-dir", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--production-input", action="store_true")
    parser.add_argument("--root", default=str(CANONICAL_ROOT))
    args = parser.parse_args()
    try:
        output, request = produce(args)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "pass", "output": str(output), "target_count": len(request["localized_change_declaration"]["target_audio_event_ids"]), "non_target_count": len(request["localized_change_declaration"]["non_target_audio_event_ids"]), "production_bundle_present": "production_bundle_binding" in request}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
