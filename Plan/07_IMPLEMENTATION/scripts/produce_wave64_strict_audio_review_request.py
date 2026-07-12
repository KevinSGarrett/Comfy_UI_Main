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
OPTIONAL_FILES = {
    "playback_proof_binding": "playback_proof.json",
    "row030_av_sync_report_binding": "row030_av_sync_report.json",
    "production_review_bundle_binding": "production_review_bundle.json",
}


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
    if not path.is_file():
        raise ValueError(f"{label} missing: {path}")
    if path.stat().st_size < 1:
        raise ValueError(f"{label} must not be empty: {path}")


def binding(path: Path) -> dict[str, Any]:
    return {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def require_identity(payload: dict[str, Any], label: str, run_id: str, is_synthetic: bool) -> None:
    if payload.get("run_id") != run_id:
        raise ValueError(f"{label}.run_id mismatch")
    if payload.get("is_synthetic") is not is_synthetic:
        raise ValueError(f"{label}.is_synthetic mismatch")


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


def produce(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    root = Path(args.root).resolve()
    if root != CANONICAL_ROOT:
        raise ValueError(f"root must match canonical project root ({CANONICAL_ROOT})")
    names = (
        "mix_wav",
        "wave30_event_manifest",
        "wave30_mix_manifest",
        "wave30_qa_report",
        "prompt_reference",
        "prompt_alignment_proof",
        "optional_dir",
        "output",
    )
    paths = {name: resolve_under(root, Path(getattr(args, name)), name) for name in names}
    output = paths["output"]
    optional_dir = paths["optional_dir"]
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    if output == optional_dir or optional_dir in output.parents:
        raise ValueError("output must not be inside optional artifact directory")
    if not optional_dir.is_dir():
        raise ValueError(f"optional_dir missing: {optional_dir}")
    required_names = tuple(name for name in names if name not in {"optional_dir", "output"})
    for name in required_names:
        require_file(paths[name], name)
    if len({paths[name] for name in required_names}) != len(required_names):
        raise ValueError("all required artifacts must use distinct paths")

    payloads = {
        name: load_json(paths[name])
        for name in (
            "wave30_event_manifest",
            "wave30_mix_manifest",
            "wave30_qa_report",
            "prompt_reference",
            "prompt_alignment_proof",
        )
    }
    if not all(isinstance(payload, dict) for payload in payloads.values()):
        raise ValueError("all required JSON artifacts must contain objects")
    run_id = args.run_id.strip()
    if not run_id:
        raise ValueError("run_id must be non-empty")
    is_synthetic = not args.production_input
    for name in ("wave30_event_manifest", "wave30_mix_manifest", "wave30_qa_report"):
        require_identity(payloads[name], name, run_id, is_synthetic)

    event_binding = binding(paths["wave30_event_manifest"])
    mix_binding = binding(paths["wave30_mix_manifest"])
    wav_binding = binding(paths["mix_wav"])
    mix = payloads["wave30_mix_manifest"]
    event_links = mix.get("event_manifest_bindings")
    expected_event_link = {key: event_binding[key] for key in ("path", "sha256")}
    if not isinstance(event_links, list) or event_links != [expected_event_link]:
        raise ValueError("wave30_mix_manifest event binding mismatch")
    mixdown = mix.get("mixdown_artifact")
    if not isinstance(mixdown, dict):
        raise ValueError("wave30_mix_manifest.mixdown_artifact missing")
    for key in ("path", "sha256"):
        if mixdown.get(key) != wav_binding[key]:
            raise ValueError(f"wave30_mix_manifest.mixdown_artifact.{key} mismatch")
    if "bytes" in mixdown and mixdown["bytes"] != wav_binding["bytes"]:
        raise ValueError("wave30_mix_manifest.mixdown_artifact.bytes mismatch")

    qa = payloads["wave30_qa_report"]
    for field, expected in (
        ("event_manifest_binding", expected_event_link),
        ("mix_manifest_binding", {key: mix_binding[key] for key in ("path", "sha256")}),
    ):
        if qa.get(field) != expected:
            raise ValueError(f"wave30_qa_report.{field} mismatch")

    prompt_reference = payloads["prompt_reference"]
    alignment = payloads["prompt_alignment_proof"]
    if prompt_reference.get("schema_name") != "wave64_prompt_reference":
        raise ValueError("prompt_reference.schema_name mismatch")
    if alignment.get("schema_name") != "wave64_prompt_alignment_proof":
        raise ValueError("prompt_alignment_proof.schema_name mismatch")
    if alignment.get("proof_kind") != "prompt_alignment":
        raise ValueError("prompt_alignment_proof.proof_kind mismatch")
    if alignment.get("audio_sha256") != wav_binding["sha256"]:
        raise ValueError("prompt_alignment_proof.audio_sha256 mismatch")
    if alignment.get("prompt_reference_sha256") != sha256(paths["prompt_reference"]):
        raise ValueError("prompt_alignment_proof.prompt_reference_sha256 mismatch")
    if alignment.get("self_authorized") is not False:
        raise ValueError("prompt_alignment_proof.self_authorized must be false")
    if alignment.get("is_synthetic") is not is_synthetic:
        raise ValueError("prompt_alignment_proof.is_synthetic mismatch")
    if args.production_input and alignment.get("production_evidence") is not True:
        raise ValueError("production input requires prompt alignment production evidence")

    optional_bindings: dict[str, dict[str, Any] | None] = {}
    for field, filename in OPTIONAL_FILES.items():
        path = optional_dir / filename
        if not path.is_file():
            optional_bindings[field] = None
            continue
        require_file(path, field)
        payload = load_json(path)
        if not isinstance(payload, dict):
            raise ValueError(f"{field} must contain a JSON object")
        if field == "playback_proof_binding":
            if payload.get("schema_name") != "wave64_playback_review_proof" or payload.get("proof_kind") != "playback_review":
                raise ValueError("playback_proof_binding schema or proof kind mismatch")
            if payload.get("audio_sha256") != wav_binding["sha256"]:
                raise ValueError("playback_proof_binding.audio_sha256 mismatch")
            if payload.get("is_synthetic") is not is_synthetic:
                raise ValueError("playback_proof_binding.is_synthetic mismatch")
            if payload.get("self_authorized") is not False:
                raise ValueError("playback_proof_binding.self_authorized must be false")
        elif field == "row030_av_sync_report_binding":
            if payload.get("schema_name") != "wave64_av_sync_certification_report":
                raise ValueError("row030_av_sync_report_binding.schema_name mismatch")
            source_audio = payload.get("artifact_bindings", {}).get("source_audio_mix_artifact")
            if not isinstance(source_audio, dict):
                raise ValueError("row030 AV sync report source audio binding missing")
            for key in ("path", "sha256", "bytes"):
                if source_audio.get(key) != wav_binding[key]:
                    raise ValueError(f"row030 AV sync report source audio {key} mismatch")
        else:
            if payload.get("schema_name") != "wave64_production_review_bundle" or payload.get("proof_kind") != "production_review":
                raise ValueError("production_review_bundle_binding schema or proof kind mismatch")
        optional_bindings[field] = binding(path)

    request = {
        "schema_name": "wave64_strict_audio_review_request",
        "request_version": 1,
        "run_id": run_id,
        "is_synthetic": is_synthetic,
        "capture_mode": args.capture_mode,
        "mix_wav_binding": wav_binding,
        "wave30_event_manifest_binding": event_binding,
        "wave30_mix_manifest_binding": mix_binding,
        "wave30_qa_report_binding": binding(paths["wave30_qa_report"]),
        "prompt_reference_binding": binding(paths["prompt_reference"]),
        "prompt_alignment_proof_binding": binding(paths["prompt_alignment_proof"]),
        **{field: value for field, value in optional_bindings.items() if value is not None},
    }
    schema = load_json(root / "Plan/08_SCHEMAS/wave64_strict_audio_review_request.schema.json")
    Draft202012Validator(schema).validate(request)
    write_atomic_no_clobber(output, request)
    return output, request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mix-wav", required=True)
    parser.add_argument("--wave30-event-manifest", required=True)
    parser.add_argument("--wave30-mix-manifest", required=True)
    parser.add_argument("--wave30-qa-report", required=True)
    parser.add_argument("--prompt-reference", required=True)
    parser.add_argument("--prompt-alignment-proof", required=True)
    parser.add_argument("--optional-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--capture-mode", choices=("technical_capture", "hand_authored_relabel"), default="technical_capture")
    parser.add_argument("--production-input", action="store_true")
    parser.add_argument("--root", default=str(CANONICAL_ROOT))
    args = parser.parse_args()
    try:
        output, request = produce(args)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "pass", "output": str(output), "missing_optional_count": sum(field not in request for field in OPTIONAL_FILES)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
