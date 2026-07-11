#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import re
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, UnidentifiedImageError

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
DEFAULT_LAST_FRAME_DURATION_MS = 100
MIN_GIF_DURATION_MS = 20
MAX_PREVIEW_EDGE = 960
VERIFIED_REF_REQUIRED_KEYS = {"status", "path", "sha256"}
INACTIVE_REF_REQUIRED_KEYS = {"status", "reason"}
EVIDENCE_REQUIRED_KEYS = {"evidence_type", "sequence_sha256", "result", "notes"}
NON_AUDIO_REQUIRED_KEYS = (
    "identity_detector",
    "face_detector",
    "body_silhouette_evidence",
    "hand_finger_evidence",
    "trusted_contact_mask_evidence",
    "motion_analysis",
    "object_background_camera_analysis",
)
AUDIO_KEYS = ("audio_asset_evidence", "audio_timing_evidence")
CODEX_VERDICT_KEY = "codex_visual_verdict"
PREREQUISITE_ORDER = NON_AUDIO_REQUIRED_KEYS + AUDIO_KEYS + (CODEX_VERDICT_KEY,)


def _error(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def _reject_nonfinite_json(token: str) -> Any:
    raise ValueError(f"non-finite numeric token is not allowed: {token}")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite_json)


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_roots(root_arg: str) -> tuple[Path, Path]:
    root = Path(root_arg).resolve()
    if (root / "Plan").is_dir():
        return root, root / "Plan"
    if root.name == "Plan" and root.is_dir():
        return root.parent, root
    raise ValueError(f"unable to resolve repository or Plan root from --root={root}")


def _type_ok(expected: str, value: Any) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )
    if expected == "boolean":
        return isinstance(value, bool)
    return False


class _SchemaContext:
    def __init__(self, schema_path: Path, root_schema: dict[str, Any]) -> None:
        self.schema_path = schema_path.resolve()
        self.root_schema = root_schema


def _resolve_json_pointer(root: Any, pointer: str) -> Any:
    if pointer == "":
        return root
    if not pointer.startswith("/"):
        raise ValueError(f"unsupported JSON pointer fragment: {pointer!r}")
    current = root
    for part in pointer.lstrip("/").split("/"):
        token = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise ValueError(f"JSON pointer not found: /{pointer.lstrip('/')}")
        current = current[token]
    return current


def _resolve_schema_ref(
    ref: str,
    context: _SchemaContext,
) -> tuple[dict[str, Any], _SchemaContext]:
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError("schema $ref must be a non-empty string")
    raw_ref = ref.strip()
    if "#" in raw_ref:
        file_part, frag_part = raw_ref.split("#", 1)
        pointer = frag_part
    else:
        file_part = raw_ref
        pointer = ""

    if not file_part:
        target_schema = context.root_schema
        target_path = context.schema_path
    else:
        target_path = (context.schema_path.parent / file_part).resolve()
        target_schema_raw = _load_json(target_path)
        if not isinstance(target_schema_raw, dict):
            raise ValueError(f"schema at {target_path} must be an object")
        target_schema = target_schema_raw

    resolved = _resolve_json_pointer(target_schema, pointer)
    if not isinstance(resolved, dict):
        raise ValueError(f"schema $ref {raw_ref!r} must resolve to an object")
    return resolved, _SchemaContext(schema_path=target_path, root_schema=target_schema)


def _validate_schema_instance(
    schema: dict[str, Any],
    instance: Any,
    path: str,
    errors: list[str],
    context: _SchemaContext,
) -> None:
    ref_value = schema.get("$ref")
    if ref_value is not None:
        try:
            resolved_schema, resolved_context = _resolve_schema_ref(ref_value, context)
        except Exception as exc:
            errors.append(f"{path}: unable to resolve $ref {ref_value!r}: {exc}")
            return
        _validate_schema_instance(resolved_schema, instance, path, errors, resolved_context)

    schema_without_ref = {k: v for k, v in schema.items() if k != "$ref"}

    if "allOf" in schema_without_ref:
        for branch in schema_without_ref["allOf"]:
            _validate_schema_instance(branch, instance, path, errors, context)

    if "if" in schema_without_ref:
        condition_errors: list[str] = []
        _validate_schema_instance(schema_without_ref["if"], instance, path, condition_errors, context)
        if not condition_errors and "then" in schema_without_ref:
            _validate_schema_instance(schema_without_ref["then"], instance, path, errors, context)
        if condition_errors and "else" in schema_without_ref:
            _validate_schema_instance(schema_without_ref["else"], instance, path, errors, context)

    if "oneOf" in schema_without_ref:
        branches = schema_without_ref["oneOf"]
        branch_valid_count = 0
        for branch in branches:
            branch_errors: list[str] = []
            _validate_schema_instance(branch, instance, path, branch_errors, context)
            if not branch_errors:
                branch_valid_count += 1
        if branch_valid_count != 1:
            errors.append(f"{path}: must satisfy exactly one oneOf branch")
        return

    expected_type = schema_without_ref.get("type")
    if expected_type is not None and not _type_ok(expected_type, instance):
        errors.append(f"{path}: expected {expected_type}, got {type(instance).__name__}")
        return

    if "const" in schema_without_ref and instance != schema_without_ref["const"]:
        errors.append(f"{path}: expected const {schema_without_ref['const']!r}, got {instance!r}")
        return

    if "enum" in schema_without_ref and instance not in schema_without_ref["enum"]:
        errors.append(f"{path}: value {instance!r} not in enum {schema_without_ref['enum']!r}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if not math.isfinite(float(instance)):
            errors.append(f"{path}: number must be finite")
            return
        if "minimum" in schema_without_ref and instance < schema_without_ref["minimum"]:
            errors.append(f"{path}: value {instance} < minimum {schema_without_ref['minimum']}")
        if "maximum" in schema_without_ref and instance > schema_without_ref["maximum"]:
            errors.append(f"{path}: value {instance} > maximum {schema_without_ref['maximum']}")

    if isinstance(instance, str):
        min_length = schema_without_ref.get("minLength")
        if min_length is not None and len(instance) < min_length:
            errors.append(f"{path}: string length < minLength {min_length}")
        pattern = schema_without_ref.get("pattern")
        if pattern is not None and re.match(pattern, instance) is None:
            errors.append(f"{path}: string does not match pattern {pattern!r}")

    if isinstance(instance, list):
        min_items = schema_without_ref.get("minItems")
        if min_items is not None and len(instance) < min_items:
            errors.append(f"{path}: item count < minItems {min_items}")
        if schema_without_ref.get("uniqueItems") is True:
            seen: list[Any] = []
            for item in instance:
                if item in seen:
                    errors.append(f"{path}: duplicate item violates uniqueItems")
                    break
                seen.append(item)
        item_schema = schema_without_ref.get("items")
        if item_schema is not None:
            for idx, item in enumerate(instance):
                _validate_schema_instance(item_schema, item, f"{path}[{idx}]", errors, context)

    if isinstance(instance, dict):
        props = schema_without_ref.get("properties", {})
        required = schema_without_ref.get("required", [])
        for field in required:
            if field not in instance:
                errors.append(f"{path}: missing required field {field!r}")
        if schema_without_ref.get("additionalProperties") is False:
            unknown = sorted(set(instance.keys()) - set(props.keys()))
            for field in unknown:
                errors.append(f"{path}: unknown field {field!r}")
        for field, value in instance.items():
            if field in props:
                _validate_schema_instance(props[field], value, f"{path}.{field}", errors, context)


def _require_verified_or_missing(
    prerequisites: dict[str, Any], key: str, errors: list[str]
) -> None:
    value = prerequisites.get(key)
    if not isinstance(value, dict):
        errors.append(f"prerequisites.{key}: must be an object")
        return
    status = value.get("status")
    if status not in {"verified", "missing"}:
        errors.append(f"prerequisites.{key}.status: non-audio fields cannot be not_required")


def _validate_evidence_ref(
    value: Any,
    key_path: str,
    allow_not_required: bool,
    errors: list[str],
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{key_path}: must be an object")
        return
    status = value.get("status")
    allowed_statuses = {"verified", "missing"}
    if allow_not_required:
        allowed_statuses.add("not_required")
    if status not in allowed_statuses:
        errors.append(f"{key_path}.status: must be one of {sorted(allowed_statuses)}")
        return

    if status == "verified":
        expected_keys = {"status", "path", "sha256"}
        unknown_keys = sorted(set(value.keys()) - expected_keys)
        if unknown_keys:
            errors.append(f"{key_path}: unknown fields for verified ref: {', '.join(unknown_keys)}")
        path_value = value.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            errors.append(f"{key_path}.path: required for verified ref")
        sha_value = value.get("sha256")
        if not isinstance(sha_value, str) or SHA256_RE.fullmatch(sha_value) is None:
            errors.append(f"{key_path}.sha256: must be lowercase SHA256 for verified ref")
        return

    expected_keys = {"status", "reason"}
    unknown_keys = sorted(set(value.keys()) - expected_keys)
    if unknown_keys:
        errors.append(f"{key_path}: unknown fields for {status} ref: {', '.join(unknown_keys)}")
    reason_value = value.get("reason")
    if not isinstance(reason_value, str) or not reason_value.strip():
        errors.append(f"{key_path}.reason: required for {status} ref")


def _parse_strict_evidence_payload(
    evidence_path: Path,
    category: str,
    expected_sequence_sha256: str,
) -> tuple[str, bool, bool, bool]:
    payload = _load_json(evidence_path)
    if not isinstance(payload, dict):
        raise ValueError("evidence payload must be an object")
    if set(payload.keys()) != EVIDENCE_REQUIRED_KEYS:
        raise ValueError(
            "evidence payload must contain exactly keys "
            f"{sorted(EVIDENCE_REQUIRED_KEYS)}, got {sorted(payload.keys())}"
        )
    evidence_type = payload.get("evidence_type")
    sequence_sha256 = payload.get("sequence_sha256")
    result = payload.get("result")
    notes = payload.get("notes")
    if not isinstance(evidence_type, str):
        raise ValueError("evidence_type must be a string")
    if not isinstance(sequence_sha256, str) or SHA256_RE.fullmatch(sequence_sha256) is None:
        raise ValueError("sequence_sha256 must be lowercase SHA256")
    if not isinstance(notes, str):
        raise ValueError("notes must be a string")
    if category == CODEX_VERDICT_KEY:
        allowed_results = {"pass", "fail", "blocked"}
    else:
        allowed_results = {"pass", "fail"}
    if result not in allowed_results:
        raise ValueError(f"result must be one of {sorted(allowed_results)}")
    type_match = evidence_type == category
    sequence_match = sequence_sha256 == expected_sequence_sha256
    satisfied = (result == "pass") if category != CODEX_VERDICT_KEY else True
    return str(result), type_match, sequence_match, satisfied


def _resolve_evidence_ref_path(prerequisites_path: Path, value: str) -> Path:
    parsed = Path(value)
    if parsed.is_absolute():
        return parsed.resolve()
    return (prerequisites_path.parent / parsed).resolve()


def _extract_manifest_bindings(manifest: Any) -> tuple[str, int]:
    if not isinstance(manifest, dict):
        raise ValueError("manifest payload must be an object")
    sequence_sha256 = manifest.get("sequence_sha256")
    if not isinstance(sequence_sha256, str) or SHA256_RE.fullmatch(sequence_sha256) is None:
        raise ValueError("manifest.sequence_sha256 must be lowercase SHA256")
    frame_count = manifest.get("frame_count")
    if not isinstance(frame_count, int) or isinstance(frame_count, bool) or frame_count <= 0:
        raise ValueError("manifest.frame_count must be a positive integer")
    frames = manifest.get("frames")
    if not isinstance(frames, list) or len(frames) != frame_count:
        actual_count = len(frames) if isinstance(frames, list) else "not-an-array"
        raise ValueError(
            "manifest.frame_count must equal manifest.frames length "
            f"({frame_count} != {actual_count})"
        )
    return sequence_sha256, frame_count


def _evaluate_prerequisite_evidence(
    prerequisites: dict[str, Any],
    prerequisites_path: Path,
    manifest_sequence_sha256: str,
) -> tuple[list[dict[str, Any]], list[str], bool]:
    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    visual_review_complete = False

    for category in PREREQUISITE_ORDER:
        if category == CODEX_VERDICT_KEY and category not in prerequisites:
            continue
        value = prerequisites.get(category)
        if not isinstance(value, dict):
            errors.append(f"prerequisites.{category}: must be an object")
            continue
        status = value.get("status")
        entry: dict[str, Any] = {
            "category": category,
            "status": status,
            "path": None,
            "declared_sha256": None,
            "observed_sha256": None,
            "reason": None,
            "path_check": None,
            "sha256_check": None,
            "evidence_type_check": None,
            "sequence_sha256_check": None,
            "result_check": None,
            "evidence_result": None,
            "prerequisite_satisfied": False,
        }

        if status == "verified":
            unknown_keys = sorted(set(value.keys()) - VERIFIED_REF_REQUIRED_KEYS)
            if unknown_keys:
                errors.append(
                    f"prerequisites.{category}: unknown fields for verified ref: "
                    + ", ".join(unknown_keys)
                )
            raw_path = value.get("path")
            declared_sha = value.get("sha256")
            if not isinstance(raw_path, str) or not raw_path.strip():
                errors.append(f"prerequisites.{category}.path: required for verified ref")
                entries.append(entry)
                continue
            if not isinstance(declared_sha, str) or SHA256_RE.fullmatch(declared_sha) is None:
                errors.append(
                    f"prerequisites.{category}.sha256: must be lowercase SHA256 for verified ref"
                )
                entries.append(entry)
                continue

            evidence_path = _resolve_evidence_ref_path(prerequisites_path, raw_path)
            entry["path"] = raw_path
            entry["declared_sha256"] = declared_sha
            path_ok = evidence_path.is_file() and evidence_path.stat().st_size > 0
            entry["path_check"] = path_ok
            if not path_ok:
                errors.append(
                    f"prerequisites.{category}: verified evidence file missing or empty at {evidence_path}"
                )
                entries.append(entry)
                continue

            observed_sha = _sha256_of(evidence_path)
            entry["observed_sha256"] = observed_sha
            sha_ok = observed_sha == declared_sha
            entry["sha256_check"] = sha_ok
            if not sha_ok:
                errors.append(
                    f"prerequisites.{category}: SHA256 mismatch ({declared_sha} != {observed_sha})"
                )
                entries.append(entry)
                continue

            try:
                evidence_result, type_ok, sequence_ok, satisfied = _parse_strict_evidence_payload(
                    evidence_path=evidence_path,
                    category=category,
                    expected_sequence_sha256=manifest_sequence_sha256,
                )
            except Exception as exc:
                errors.append(f"prerequisites.{category}: invalid evidence payload: {exc}")
                entries.append(entry)
                continue

            entry["evidence_type_check"] = type_ok
            entry["sequence_sha256_check"] = sequence_ok
            entry["result_check"] = True
            entry["evidence_result"] = evidence_result
            entry["prerequisite_satisfied"] = satisfied and type_ok and sequence_ok and sha_ok
            if not type_ok:
                errors.append(
                    f"prerequisites.{category}: evidence_type must equal prerequisite category"
                )
            if not sequence_ok:
                errors.append(
                    f"prerequisites.{category}: sequence_sha256 must equal manifest.sequence_sha256"
                )
            if category == CODEX_VERDICT_KEY and entry["prerequisite_satisfied"]:
                visual_review_complete = True
            entries.append(entry)
            continue

        if status in {"missing", "not_required"}:
            unknown_keys = sorted(set(value.keys()) - INACTIVE_REF_REQUIRED_KEYS)
            if unknown_keys:
                errors.append(
                    f"prerequisites.{category}: unknown fields for {status} ref: "
                    + ", ".join(unknown_keys)
                )
            reason = value.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append(f"prerequisites.{category}.reason: required for {status} ref")
            entry["reason"] = reason if isinstance(reason, str) else None
            entries.append(entry)
            continue

        errors.append(f"prerequisites.{category}.status: unsupported status {status!r}")
        entries.append(entry)
    return entries, errors, visual_review_complete


def _validate_prerequisite_semantics(prerequisites: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in NON_AUDIO_REQUIRED_KEYS:
        _require_verified_or_missing(prerequisites, key, errors)
        _validate_evidence_ref(prerequisites.get(key), f"prerequisites.{key}", False, errors)

    audio_required = prerequisites.get("audio_required")
    if not isinstance(audio_required, bool):
        errors.append("prerequisites.audio_required: must be boolean")
        return errors

    for key in AUDIO_KEYS:
        value = prerequisites.get(key)
        _validate_evidence_ref(value, f"prerequisites.{key}", True, errors)
        if not isinstance(value, dict):
            continue
        status = value.get("status")
        if status == "not_required" and audio_required:
            errors.append(
                f"prerequisites.{key}.status: cannot be not_required when audio_required=true"
            )

    if "codex_visual_verdict" in prerequisites:
        _validate_evidence_ref(
            prerequisites.get("codex_visual_verdict"),
            "prerequisites.codex_visual_verdict",
            True,
            errors,
        )
    return errors


def _run_strict_packet_gate(
    repo_root: Path, plan_root: Path, manifest_path: Path, evidence_path: Path
) -> tuple[bool, str]:
    validator = plan_root / "07_IMPLEMENTATION/scripts/run_wave27_local_validation.py"
    frame_schema = plan_root / "08_SCHEMAS/wave27_frame_manifest.schema.json"
    evidence_schema = plan_root / "08_SCHEMAS/wave27_temporal_evidence.schema.json"
    cmd = [
        sys.executable,
        str(validator),
        "--root",
        str(repo_root),
        "--strict-packet",
        "--manifest",
        str(manifest_path),
        "--evidence",
        str(evidence_path),
        "--frame-schema",
        str(frame_schema),
        "--evidence-schema",
        str(evidence_schema),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root, check=False)
    if result.returncode != 0:
        output = result.stdout.strip()
        if not output:
            output = result.stderr.strip()
        if not output:
            output = "strict packet gate failed"
        return False, output
    return True, result.stdout.strip()


def _resolve_artifact(manifest_path: Path, artifact_value: str) -> Path:
    artifact_path = Path(artifact_value)
    if artifact_path.is_absolute():
        return artifact_path.resolve()
    return (manifest_path.parent / artifact_path).resolve()


def _relative_or_absolute(target: Path, base: Path) -> str:
    try:
        return target.relative_to(base).as_posix()
    except ValueError:
        return target.resolve().as_posix()


def _compute_frame_durations_ms(times: list[float]) -> list[int]:
    if len(times) == 1:
        return [DEFAULT_LAST_FRAME_DURATION_MS]
    durations: list[int] = []
    for idx in range(len(times) - 1):
        delta = max(0.0, times[idx + 1] - times[idx])
        durations.append(max(MIN_GIF_DURATION_MS, int(round(delta * 1000.0))))
    durations.append(durations[-1] if durations else DEFAULT_LAST_FRAME_DURATION_MS)
    return durations


def _render_grid(
    frames: list[Image.Image], times: list[float], output_path: Path
) -> tuple[int, int]:
    count = len(frames)
    cols = max(1, min(4, int(math.ceil(math.sqrt(float(count))))))
    rows = int(math.ceil(float(count) / float(cols)))
    thumb_max = 240
    pad = 12
    label_h = 22

    source_w, source_h = frames[0].size
    scale = min(1.0, float(thumb_max) / float(max(source_w, source_h)))
    thumb_w = max(1, int(round(source_w * scale)))
    thumb_h = max(1, int(round(source_h * scale)))

    canvas_w = (pad * (cols + 1)) + (thumb_w * cols)
    canvas_h = (pad * (rows + 1)) + ((thumb_h + label_h) * rows)
    canvas = Image.new("RGB", (canvas_w, canvas_h), color=(245, 245, 245))
    drawer = ImageDraw.Draw(canvas)

    for idx, frame in enumerate(frames):
        row = idx // cols
        col = idx % cols
        x = pad + col * (thumb_w + pad)
        y = pad + row * (thumb_h + label_h + pad)
        thumb = frame.copy().resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        canvas.paste(thumb, (x, y))
        label = f"#{idx} t={times[idx]:.3f}s"
        drawer.text((x, y + thumb_h + 3), label, fill=(0, 0, 0))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG", optimize=False, compress_level=9)
    return canvas_w, canvas_h


def _render_gif(frames: list[Image.Image], durations_ms: list[int], output_path: Path) -> None:
    gif_frames: list[Image.Image] = []
    for frame in frames:
        gif_frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=256))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gif_frames[0].save(
        output_path,
        format="GIF",
        save_all=True,
        append_images=gif_frames[1:],
        duration=durations_ms,
        loop=0,
        optimize=False,
        disposal=2,
    )


def _load_and_validate_frames(
    manifest: dict[str, Any], manifest_path: Path
) -> tuple[list[dict[str, Any]], list[Image.Image], list[float], tuple[int, int]]:
    frames_raw = manifest.get("frames")
    if not isinstance(frames_raw, list) or not frames_raw:
        raise ValueError("manifest.frames must be a non-empty list")

    validated_frames: list[dict[str, Any]] = []
    loaded_images: list[Image.Image] = []
    frame_times: list[float] = []
    expected_dims: tuple[int, int] | None = None

    for idx, frame in enumerate(frames_raw):
        if not isinstance(frame, dict):
            raise ValueError(f"manifest.frames[{idx}] must be an object")
        frame_index = frame.get("frame_index")
        if frame_index != idx:
            raise ValueError(
                f"manifest.frames[{idx}].frame_index must equal manifest order index ({idx})"
            )
        raw_time = frame.get("time_seconds")
        if not isinstance(raw_time, (int, float)) or isinstance(raw_time, bool):
            raise ValueError(f"manifest.frames[{idx}].time_seconds must be numeric")
        time_seconds = float(raw_time)
        if not math.isfinite(time_seconds):
            raise ValueError(f"manifest.frames[{idx}].time_seconds must be finite")
        if frame_times and time_seconds <= frame_times[-1]:
            raise ValueError("manifest.frames time_seconds must be strictly increasing")
        frame_times.append(time_seconds)

        artifact_path_value = frame.get("artifact_path")
        artifact_sha = frame.get("artifact_sha256")
        artifact_bytes = frame.get("artifact_bytes")
        if not isinstance(artifact_path_value, str) or not artifact_path_value.strip():
            raise ValueError(f"manifest.frames[{idx}].artifact_path must be a non-empty string")
        if not isinstance(artifact_sha, str) or SHA256_RE.fullmatch(artifact_sha) is None:
            raise ValueError(f"manifest.frames[{idx}].artifact_sha256 must be lowercase SHA256")
        if (
            not isinstance(artifact_bytes, int)
            or isinstance(artifact_bytes, bool)
            or artifact_bytes <= 0
        ):
            raise ValueError(f"manifest.frames[{idx}].artifact_bytes must be positive integer")

        artifact_path = _resolve_artifact(manifest_path, artifact_path_value)
        if not artifact_path.is_file():
            raise ValueError(f"manifest.frames[{idx}] artifact missing: {artifact_path}")
        observed_bytes = artifact_path.stat().st_size
        if observed_bytes <= 0:
            raise ValueError(f"manifest.frames[{idx}] artifact is empty: {artifact_path}")
        if observed_bytes != artifact_bytes:
            raise ValueError(
                f"manifest.frames[{idx}] artifact_bytes mismatch ({artifact_bytes} != {observed_bytes})"
            )
        observed_sha = _sha256_of(artifact_path)
        if observed_sha != artifact_sha:
            raise ValueError(
                f"manifest.frames[{idx}] artifact_sha256 mismatch ({artifact_sha} != {observed_sha})"
            )

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(artifact_path) as raw:
                    raw.load()
                    image = raw.convert("RGBA")
        except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
            raise ValueError(
                f"manifest.frames[{idx}] artifact failed decompression-bomb safety checks: {exc}"
            ) from exc
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError(f"manifest.frames[{idx}] artifact is not Pillow-decodable: {exc}") from exc
        if image.width <= 0 or image.height <= 0:
            raise ValueError(f"manifest.frames[{idx}] artifact has invalid dimensions")
        current_dims = (image.width, image.height)
        if expected_dims is None:
            expected_dims = current_dims
        elif current_dims != expected_dims:
            raise ValueError(
                f"manifest frame dimensions mismatch ({current_dims} != {expected_dims})"
            )

        validated_frames.append(frame)
        loaded_images.append(image)

    assert expected_dims is not None
    return validated_frames, loaded_images, frame_times, expected_dims


def _downscale_for_preview(image: Image.Image, max_edge: int = MAX_PREVIEW_EDGE) -> Image.Image:
    width, height = image.size
    largest = max(width, height)
    if largest <= max_edge:
        return image.copy()
    scale = float(max_edge) / float(largest)
    resized = (
        max(1, int(round(width * scale))),
        max(1, int(round(height * scale))),
    )
    return image.copy().resize(resized, Image.Resampling.LANCZOS)


def _compute_missing_categories_from_results(
    prerequisites: dict[str, Any], evidence_results: list[dict[str, Any]]
) -> list[str]:
    result_by_category = {str(item["category"]): item for item in evidence_results}
    missing: list[str] = []

    for key in NON_AUDIO_REQUIRED_KEYS:
        value = prerequisites.get(key, {})
        status = value.get("status")
        result_entry = result_by_category.get(key, {})
        if status == "missing":
            missing.append(key)
        elif status == "verified" and not bool(result_entry.get("prerequisite_satisfied")):
            missing.append(key)

    audio_required = bool(prerequisites.get("audio_required"))
    for key in AUDIO_KEYS:
        value = prerequisites.get(key, {})
        status = value.get("status")
        result_entry = result_by_category.get(key, {})
        if status == "missing":
            missing.append(key)
        elif status == "verified" and not bool(result_entry.get("prerequisite_satisfied")):
            missing.append(key)
        elif audio_required and status == "not_required":
            missing.append(key)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--prerequisites", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    try:
        repo_root, plan_root = _resolve_roots(args.root)
    except Exception as exc:
        _error(str(exc))
        return 1

    manifest_path = Path(args.manifest).resolve()
    evidence_path = Path(args.evidence).resolve()
    prerequisites_path = Path(args.prerequisites).resolve()
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists():
        if not out_dir.is_dir():
            _error(f"output path exists and is not a directory: {out_dir}")
            return 1
        if any(out_dir.iterdir()):
            _error(f"output directory already exists and is non-empty: {out_dir}")
            return 1

    try:
        manifest = _load_json(manifest_path)
        evidence = _load_json(evidence_path)
        prerequisites = _load_json(prerequisites_path)
        manifest_sequence_sha256, manifest_frame_count = _extract_manifest_bindings(manifest)
    except Exception as exc:
        _error(f"unable to load packet inputs: {exc}")
        return 1

    gate_ok, gate_message = _run_strict_packet_gate(
        repo_root=repo_root,
        plan_root=plan_root,
        manifest_path=manifest_path,
        evidence_path=evidence_path,
    )
    if not gate_ok:
        _error(f"strict packet validation failed: {gate_message}")
        return 1

    prerequisites_schema_path = (
        plan_root / "08_SCHEMAS/wave27_visual_review_prerequisites.schema.json"
    )
    packet_schema_path = plan_root / "08_SCHEMAS/wave27_visual_review_packet.schema.json"
    try:
        prerequisites_schema = _load_json(prerequisites_schema_path)
        packet_schema = _load_json(packet_schema_path)
    except Exception as exc:
        _error(f"unable to load visual review schema files: {exc}")
        return 1

    prerequisite_errors: list[str] = []
    prerequisites_schema_context = _SchemaContext(
        schema_path=prerequisites_schema_path,
        root_schema=prerequisites_schema,
    )
    _validate_schema_instance(
        prerequisites_schema,
        prerequisites,
        "prerequisites",
        prerequisite_errors,
        prerequisites_schema_context,
    )
    prerequisite_errors.extend(_validate_prerequisite_semantics(prerequisites))
    if prerequisite_errors:
        _error("invalid prerequisites payload:")
        for issue in prerequisite_errors:
            _error(f"  - {issue}")
        return 1

    try:
        ordered_frames, frame_images, frame_times, image_dims = _load_and_validate_frames(
            manifest=manifest,
            manifest_path=manifest_path,
        )
    except Exception as exc:
        _error(str(exc))
        return 1
    if len(ordered_frames) != manifest_frame_count:
        _error(
            "validated frame count does not match manifest.frame_count "
            f"({len(ordered_frames)} != {manifest_frame_count})"
        )
        return 1

    evidence_results, evidence_errors, visual_review_complete = _evaluate_prerequisite_evidence(
        prerequisites=prerequisites,
        prerequisites_path=prerequisites_path,
        manifest_sequence_sha256=manifest_sequence_sha256,
    )
    if evidence_errors:
        _error("invalid prerequisite evidence bindings:")
        for issue in evidence_errors:
            _error(f"  - {issue}")
        return 1

    preview_frames = [_downscale_for_preview(frame) for frame in frame_images]
    durations_ms = _compute_frame_durations_ms(frame_times)
    missing_categories = _compute_missing_categories_from_results(prerequisites, evidence_results)
    prerequisites_complete = not missing_categories
    if not prerequisites_complete:
        status = "blocked_missing_prerequisites"
        exit_code = 2
    elif visual_review_complete:
        status = "visual_review_recorded_pending_codex_authority"
        exit_code = 0
    else:
        status = "ready_for_visual_review"
        exit_code = 0

    frame_records: list[dict[str, Any]] = []
    for idx, frame in enumerate(ordered_frames):
        next_index: int | None = None
        delta_seconds: float | None = None
        if idx + 1 < len(ordered_frames):
            next_index = int(ordered_frames[idx + 1]["frame_index"])
            delta_seconds = round(frame_times[idx + 1] - frame_times[idx], 6)
        frame_records.append(
            {
                "frame_index": int(frame["frame_index"]),
                "time_seconds": float(frame["time_seconds"]),
                "artifact_path": str(frame["artifact_path"]),
                "artifact_sha256": str(frame["artifact_sha256"]),
                "artifact_bytes": int(frame["artifact_bytes"]),
                "image_width": image_dims[0],
                "image_height": image_dims[1],
                "adjacent_next_index": next_index,
                "adjacent_next_time_delta_seconds": delta_seconds,
            }
        )

    try:
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        staging_dir = Path(
            tempfile.mkdtemp(prefix=f".{out_dir.name}.staging-", dir=out_dir.parent)
        ).resolve()
    except OSError as exc:
        _error(f"unable to prepare output parent {out_dir.parent}: {exc}")
        return 1
    packet_path = staging_dir / "visual_review_packet.json"
    frame_grid_path = staging_dir / "frame_grid.png"
    gif_path = staging_dir / "review_playback.gif"
    try:
        grid_w, grid_h = _render_grid(preview_frames, frame_times, frame_grid_path)
        _render_gif(preview_frames, durations_ms, gif_path)

        grid_sha = _sha256_of(frame_grid_path)
        gif_sha = _sha256_of(gif_path)
        grid_bytes = frame_grid_path.stat().st_size
        gif_bytes = gif_path.stat().st_size
        if grid_bytes <= 0 or gif_bytes <= 0:
            _error("generated preview artifacts must be non-empty")
            return 1

        packet = {
            "schema_name": "wave27_visual_review_packet",
            "packet_version": 1,
            "source_bindings": {
                "manifest_path": manifest_path.as_posix(),
                "manifest_sha256": _sha256_of(manifest_path),
                "manifest_sequence_sha256": manifest_sequence_sha256,
                "evidence_path": evidence_path.as_posix(),
                "evidence_sha256": _sha256_of(evidence_path),
                "frame_count": manifest_frame_count,
            },
            "frames": frame_records,
            "preview_artifacts": {
                "frame_grid": {
                    "path": _relative_or_absolute(frame_grid_path, staging_dir),
                    "sha256": grid_sha,
                    "bytes": grid_bytes,
                    "width": grid_w,
                    "height": grid_h,
                },
                "review_playback_gif": {
                    "path": _relative_or_absolute(gif_path, staging_dir),
                    "sha256": gif_sha,
                    "bytes": gif_bytes,
                    "frame_count": len(frame_records),
                    "durations_ms": durations_ms,
                },
            },
            "prerequisites": prerequisites,
            "prerequisite_evidence_results": evidence_results,
            "missing_prerequisite_categories": missing_categories,
            "review_assets_ready": True,
            "prerequisites_complete": prerequisites_complete,
            "visual_review_complete": visual_review_complete,
            "status": status,
            "decision_scope": "review_preparation_only",
            "final_temporal_visual_pass": False,
            "final_acceptance_claimed": False,
        }

        packet_errors: list[str] = []
        packet_schema_context = _SchemaContext(schema_path=packet_schema_path, root_schema=packet_schema)
        _validate_schema_instance(packet_schema, packet, "packet", packet_errors, packet_schema_context)
        if packet_errors:
            _error("generated packet failed schema validation:")
            for issue in packet_errors:
                _error(f"  - {issue}")
            return 1

        packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        if out_dir.exists():
            if out_dir.is_dir() and not any(out_dir.iterdir()):
                out_dir.rmdir()
            elif out_dir.is_dir():
                _error(f"output directory became non-empty before move: {out_dir}")
                return 1
            else:
                _error(f"output path exists and is not a directory: {out_dir}")
                return 1
        staging_dir.replace(out_dir)
        print(str(out_dir / "visual_review_packet.json"))
        return exit_code
    except Exception as exc:
        _error(f"unable to generate visual review packet: {exc}")
        return 1
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
