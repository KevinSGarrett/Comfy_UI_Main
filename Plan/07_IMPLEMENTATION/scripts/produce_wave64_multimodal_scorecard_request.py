#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


CANONICAL_ROOT = Path("C:/Comfy_UI_Main").resolve()
BINDING_ARGUMENTS = {
    "image_review_binding": "image_review",
    "video_review_binding": "video_review",
    "strict_audio_report_binding": "strict_audio_report",
    "global_audio_report_binding": "global_audio_report",
    "av_sync_report_binding": "av_sync_report",
    "artifact_manifest_binding": "artifact_manifest",
    "release_gate_decision_binding": "release_gate_decision",
}


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON: {value}")),
    )


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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(path: Path) -> dict[str, Any]:
    return {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def relative_binding(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    return {**value, "path": Path(value["path"]).resolve().relative_to(root).as_posix()}


def require_object(payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return payload


def require_lineage(payload: dict[str, Any], label: str, expected: dict[str, Any]) -> None:
    lineage = payload.get("lineage")
    if not isinstance(lineage, dict):
        raise ValueError(f"{label}.lineage missing")
    for key, value in expected.items():
        if lineage.get(key) != value:
            raise ValueError(f"{label}.lineage.{key} mismatch")


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


def main() -> int:
    parser = argparse.ArgumentParser()
    for argument in BINDING_ARGUMENTS.values():
        parser.add_argument(f"--{argument.replace('_', '-')}", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--shot-id", required=True)
    parser.add_argument("--take-id", required=True)
    parser.add_argument("--generation-test-method", required=True)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--authority-id", required=True)
    parser.add_argument("--bundle-id", required=True)
    parser.add_argument(
        "--caller-claimed-approval-decision",
        choices=("approved", "conditionally_approved", "rejected", "blocked"),
        default="blocked",
    )
    parser.add_argument("--production-input", action="store_true")
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--root", default=str(CANONICAL_ROOT))
    args = parser.parse_args()

    try:
        root = Path(args.root).resolve()
        if root != CANONICAL_ROOT:
            raise ValueError("root must be the canonical project root")
        output = resolve_under(root, Path(args.output), "output")
        output_report = resolve_under(root, Path(args.output_report), "output_report")
        if output == output_report:
            raise ValueError("request and report output paths must be distinct")
        if output.exists() or output_report.exists():
            raise ValueError("request or report output collision")

        paths: dict[str, Path] = {}
        for field, argument in BINDING_ARGUMENTS.items():
            path = resolve_under(root, Path(getattr(args, argument)), argument)
            require_file(path, argument)
            paths[field] = path
        if len(set(paths.values())) != len(paths):
            raise ValueError("all seven upstream artifacts must be distinct")

        payloads = {field: require_object(load_json(path), field) for field, path in paths.items()}
        bindings = {field: binding(path) for field, path in paths.items()}
        lineage = {
            "run_id": args.run_id,
            "scene_id": args.scene_id,
            "shot_id": args.shot_id,
            "take_id": args.take_id,
            "is_synthetic": args.synthetic,
        }

        rules_path = root / "Plan/10_REGISTRIES/wave64_multimodal_scorecard_rules.json"
        schema_path = root / "Plan/08_SCHEMAS/wave64_multimodal_scorecard_request.schema.json"
        rules = require_object(load_json(rules_path), "rules")
        schema = require_object(load_json(schema_path), "request_schema")
        contracts = require_object(rules.get("contracts"), "rules.contracts")

        for field in ("image_review_binding", "video_review_binding"):
            label = field.removesuffix("_binding")
            payload = payloads[field]
            contract = require_object(contracts.get(label), f"rules.contracts.{label}")
            if payload.get("tracker_id") != contract.get("expected_tracker_id"):
                raise ValueError(f"{label}.tracker_id mismatch")
            if payload.get("item_id") != contract.get("expected_item_id"):
                raise ValueError(f"{label}.item_id mismatch")
            if payload.get(contract.get("source_artifact_id_field")) != args.artifact_id:
                raise ValueError(f"{label} artifact identity mismatch")
            require_lineage(payload, label, lineage)

        strict_audio = payloads["strict_audio_report_binding"]
        if strict_audio.get("schema_name") != contracts["strict_audio_report"].get("schema_name"):
            raise ValueError("strict_audio_report schema_name mismatch")
        if strict_audio.get("run_id") != args.run_id or strict_audio.get("is_synthetic") is not args.synthetic:
            raise ValueError("strict_audio_report lineage mismatch")

        global_audio = payloads["global_audio_report_binding"]
        if global_audio.get("schema_name") != contracts["global_audio_report"].get("schema_name"):
            raise ValueError("global_audio_report schema_name mismatch")
        if global_audio.get("review_run_id") != args.run_id or global_audio.get("is_synthetic") is not args.synthetic:
            raise ValueError("global_audio_report lineage mismatch")

        av_sync = payloads["av_sync_report_binding"]
        if av_sync.get("schema_name") != contracts["av_sync_report"].get("schema_name"):
            raise ValueError("av_sync_report schema_name mismatch")
        for key, value in lineage.items():
            if av_sync.get(key) != value:
                raise ValueError(f"av_sync_report.{key} mismatch")

        manifest = payloads["artifact_manifest_binding"]
        release = payloads["release_gate_decision_binding"]
        release_id = release.get("release_id")
        if not isinstance(release_id, str) or not release_id or manifest.get("release_id") != release_id:
            raise ValueError("artifact manifest and release decision release_id mismatch")

        request = {
            "schema_name": "wave64_multimodal_scorecard_request",
            "request_version": 1,
            "artifact_id": args.artifact_id,
            **lineage,
            "artifact_type": "multimodal_cross_review",
            "generation_test_method": args.generation_test_method,
            **bindings,
            "production_authority_claim": {"authority_id": args.authority_id, "bundle_id": args.bundle_id},
            "caller_claimed_approval_decision": args.caller_claimed_approval_decision,
            "output_report_path": str(output_report),
        }
        validation_errors = sorted(Draft202012Validator(schema).iter_errors(request), key=lambda item: list(item.path))
        if validation_errors:
            raise ValueError(f"request schema validation failed: {validation_errors[0].message}")

        if args.production_input:
            if args.synthetic:
                raise ValueError("production input cannot be synthetic")
            authorities = rules.get("authority_rules", {}).get("production_authority_exact_objects", [])
            matches = [
                item
                for item in authorities
                if isinstance(item, dict)
                and item.get("authority_id") == args.authority_id
                and item.get("bundle_id") == args.bundle_id
            ]
            if len(matches) != 1:
                raise ValueError("exact production authority object is required")
            authority = matches[0]
            for key, value in {"artifact_id": args.artifact_id, **lineage, "release_id": release_id}.items():
                if authority.get(key) != value:
                    raise ValueError(f"production authority {key} mismatch")
            expected_bindings = authority.get("input_bindings")
            actual_bindings = {field: relative_binding(root, value) for field, value in bindings.items()}
            if expected_bindings != actual_bindings:
                raise ValueError("production authority input bindings mismatch")

        write_atomic_no_clobber(output, request)
        print(json.dumps({"output": str(output), "production_input": args.production_input, "status": "pass"}, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
