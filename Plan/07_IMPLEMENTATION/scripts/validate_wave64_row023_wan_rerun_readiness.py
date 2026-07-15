#!/usr/bin/env python3
"""Validate one fail-closed Wan rerun-shot package for Wave64 Row023."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import tempfile
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path("C:/Comfy_UI_Main")
TRACKER_ID = "TRK-W64-023"
ITEM_ID = "ITEM-W64-023"
LANE_ID = "wan_2_2_ti2v_5b_primary_lane"
SEED = 2272301
STAGED_FILENAME = "wan22_row023_rerun_anchor_frame0002.png"
OUTPUT_PREFIX = "video/w64_row023_wan22_rerun_seed2272301"
SOURCE_REL = "Plan/Instructions/Operations/Pulled_Back_Artifacts/wave64_animatediff_fallback_20260713T022708-0500/extracted_frames/frame_0002.png"
SOURCE_SHA256 = "d6d5acd4579a34f0ebef9aa47a4d01e20e5bf83c3885c8e93f146eadeeb72665"
SOURCE_BYTES = 87511
SOURCE_WIDTH = 256
SOURCE_HEIGHT = 320
PROFILE_REL = "PromptProfiles/video_generation/wan_2_2_ti2v_5b_primary_lane/row023_animatediff_frame0002_rerun_seed2272301.json"
MANIFEST_REL = "Plan/Instructions/Operations/Pulled_Back_Artifacts/wave64_animatediff_fallback_20260713T022708-0500/wave27_frame_manifest.json"
VISUAL_REL = "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W64_LOCAL_ANIMATEDIFF_FALLBACK_VISUAL_QA_20260713T023500-0500.json"
ROUTING_REL = "Plan/Instructions/QA/Evidence/Wave64/VIDEO_FRAME_REPAIR_REAL_SEQUENCE_ROUTING_20260713T042629-0500.json"
ROBUSTNESS_REL = "Plan/Instructions/QA/Evidence/Workflow_Runtime/W64_WAN22_SEED_ROBUSTNESS_TARGET_RUNTIME_20260714T030930-0500.json"
DIVERSITY_REL = "Plan/Instructions/QA/Evidence/Workflow_Runtime/W64_WAN22_SOURCE_DIVERSITY_TARGET_RUNTIME_20260714T043510-0500.json"
WORKFLOW_REL = "Workflows/video_generation/wan_2_2_ti2v_5b_primary_lane/workflow.api.json"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(value: bool, label: str) -> None:
    if not value:
        raise ValueError(label)


def repo_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"path outside project root: {path}") from exc


def bind(path: Path, root: Path) -> dict[str, Any]:
    path = path.resolve()
    before = path.stat()
    digest = sha256_file(path)
    after = path.stat()
    require(path.is_file() and after.st_size > 0, f"missing or empty file: {path}")
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), f"file changed while hashing: {path}")
    return {"path": repo_path(path, root), "sha256": digest, "bytes": after.st_size}


def _paeth(left: int, up: int, upper_left: int) -> int:
    prediction = left + up - upper_left
    distances = (abs(prediction - left), abs(prediction - up), abs(prediction - upper_left))
    return (left, up, upper_left)[distances.index(min(distances))]


def decode_png_rgb(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    require(data[:8] == b"\x89PNG\r\n\x1a\n", f"not a PNG: {path}")
    offset = 8
    ihdr: tuple[int, int, int, int, int, int, int] | None = None
    compressed = bytearray()
    while offset < len(data):
        require(offset + 12 <= len(data), f"truncated PNG chunk: {path}")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : offset + 12 + length])[0]
        require(zlib.crc32(kind + payload) & 0xFFFFFFFF == expected_crc, f"PNG CRC mismatch: {path}")
        offset += 12 + length
        if kind == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    require(ihdr is not None and compressed, f"PNG IHDR or IDAT missing: {path}")
    width, height, bit_depth, color_type, compression, filtering, interlace = ihdr
    require(bit_depth == 8 and color_type in {0, 2, 6}, f"unsupported PNG color format: {path}")
    require(compression == 0 and filtering == 0 and interlace == 0, f"unsupported PNG encoding: {path}")
    channels = {0: 1, 2: 3, 6: 4}[color_type]
    stride = width * channels
    raw = zlib.decompress(bytes(compressed))
    require(len(raw) == height * (stride + 1), f"PNG payload length mismatch: {path}")
    rows: list[bytearray] = []
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        encoded = raw[cursor : cursor + stride]
        cursor += stride
        require(filter_type in {0, 1, 2, 3, 4}, f"unsupported PNG row filter: {path}")
        prior = rows[-1] if rows else bytearray(stride)
        decoded = bytearray(stride)
        for index, value in enumerate(encoded):
            left = decoded[index - channels] if index >= channels else 0
            up = prior[index]
            upper_left = prior[index - channels] if index >= channels else 0
            predictor = {0: 0, 1: left, 2: up, 3: (left + up) // 2, 4: _paeth(left, up, upper_left)}[filter_type]
            decoded[index] = (value + predictor) & 0xFF
        rows.append(decoded)
    pixels = bytearray()
    for row in rows:
        if channels == 3:
            pixels.extend(row)
        elif channels == 4:
            for index in range(0, len(row), 4):
                pixels.extend(row[index : index + 3])
        else:
            for value in row:
                pixels.extend((value, value, value))
    return width, height, bytes(pixels)


def select_medoid(frames: list[tuple[int, Path]]) -> tuple[int, dict[int, float]]:
    require(len(frames) >= 2, "at least two frames are required for medoid selection")
    decoded: dict[int, tuple[int, int, bytes]] = {index: decode_png_rgb(path) for index, path in frames}
    dimensions = {(width, height) for width, height, _ in decoded.values()}
    require(len(dimensions) == 1, "passed frames have inconsistent dimensions")
    scores: dict[int, float] = {}
    for index, (_, _, pixels) in decoded.items():
        distances = []
        for other_index, (_, _, other_pixels) in decoded.items():
            if other_index == index:
                continue
            require(len(pixels) == len(other_pixels), "passed frame pixel lengths differ")
            distances.append(sum(abs(left - right) for left, right in zip(pixels, other_pixels)) / len(pixels))
        scores[index] = sum(distances) / len(distances)
    return min(scores, key=lambda index: (scores[index], index)), scores


def validate_source(root: Path) -> dict[str, Any]:
    manifest_path = root / MANIFEST_REL
    visual_path = root / VISUAL_REL
    routing_path = root / ROUTING_REL
    manifest = load_json(manifest_path)
    visual = load_json(visual_path)
    routing = load_json(routing_path)
    frames = manifest.get("frames")
    require(isinstance(frames, list) and len(frames) == 8, "source manifest must contain exactly eight frames")
    frame_by_index = {record.get("frame_index"): record for record in frames if isinstance(record, dict)}
    require(set(frame_by_index) == set(range(8)), "source frame indexes mismatch")
    failed = visual.get("failed_frame_indexes")
    require(failed == [5, 6, 7], "source visual failure indexes mismatch")
    require(routing.get("routing", {}).get("recommended_action") == "rerun_shot", "Row023 rerun-shot route missing")
    require(routing.get("routing", {}).get("executor_output_published") is False, "prior executor unexpectedly published output")
    passed = sorted(set(frame_by_index) - set(failed))
    require(passed == [0, 1, 2, 3, 4], "passed frame set mismatch")
    base = manifest_path.parent
    medoid_inputs: list[tuple[int, Path]] = []
    for index in passed:
        record = frame_by_index[index]
        path = (base / str(record.get("artifact_path", ""))).resolve()
        require(repo_path(path, root).startswith(repo_path(base, root) + "/"), "frame path escaped source packet")
        binding = bind(path, root)
        require(binding["sha256"] == record.get("artifact_sha256"), f"frame {index} SHA-256 mismatch")
        require(binding["bytes"] == record.get("artifact_bytes"), f"frame {index} byte count mismatch")
        medoid_inputs.append((index, path))
    selected, scores = select_medoid(medoid_inputs)
    require(selected == 2, f"passed-frame medoid drifted to frame {selected}")
    source_path = root / SOURCE_REL
    width, height, _ = decode_png_rgb(source_path)
    source_binding = bind(source_path, root)
    require(source_binding == {"path": SOURCE_REL, "sha256": SOURCE_SHA256, "bytes": SOURCE_BYTES}, "selected source binding mismatch")
    require((width, height) == (SOURCE_WIDTH, SOURCE_HEIGHT), "selected source dimensions mismatch")
    return {
        "passed_frame_indexes": passed,
        "failed_frame_indexes": failed,
        "selected_frame_index": selected,
        "selection_method": "minimum_mean_absolute_rgb_distance_medoid_across_passed_frames",
        "mean_absolute_rgb_distance_scores": {str(index): round(score, 6) for index, score in sorted(scores.items())},
        "source": source_binding | {"width": width, "height": height},
    }


def completed_wan_seeds(root: Path) -> set[int]:
    robustness = load_json(root / ROBUSTNESS_REL)
    diversity = load_json(root / DIVERSITY_REL)
    seeds = {record.get("seed") for record in robustness.get("seed_results", []) if isinstance(record, dict)}
    seeds.add(diversity.get("runtime_unit", {}).get("seed"))
    require(all(isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds), "completed Wan seed inventory invalid")
    return seeds


def validate_profile(profile: dict[str, Any], source: dict[str, Any], prior_seeds: set[int]) -> dict[str, Any]:
    require(profile.get("target_lane_id") == LANE_ID, "profile lane mismatch")
    binding = profile.get("source_binding", {})
    require(binding.get("project_path") == source["source"]["path"], "profile source path mismatch")
    require(binding.get("staged_filename") == STAGED_FILENAME, "profile staged filename mismatch")
    require(binding.get("sha256") == source["source"]["sha256"], "profile source hash mismatch")
    require(binding.get("size_bytes") == source["source"]["bytes"], "profile source size mismatch")
    require((binding.get("source_width"), binding.get("source_height")) == (SOURCE_WIDTH, SOURCE_HEIGHT), "profile source dimensions mismatch")
    require(binding.get("selected_frame_index") == source["selected_frame_index"], "profile selected frame mismatch")
    patches = profile.get("request_patch_values", {})
    require(patches.get("seed") == SEED and SEED not in prior_seeds, "profile seed is invalid or already completed")
    require(patches.get("source_image") == STAGED_FILENAME, "profile request source filename mismatch")
    require(patches.get("video_latent") == {"width": 480, "height": 640, "length": 49, "batch_size": 1}, "profile video latent mismatch")
    require(patches.get("sampler_settings") == {"steps": 20, "cfg": 5, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1}, "profile sampler contract mismatch")
    require(patches.get("output_video") == {"filename_prefix": OUTPUT_PREFIX, "format": "mp4", "codec": "h264"}, "profile output contract mismatch")
    positive = str(patches.get("positive_prompt", "")).lower()
    negative = str(patches.get("negative_prompt", "")).lower()
    for token in ("exact face identity", "white collared blouse", "black studio background", "locked camera", "head-and-shoulders"):
        require(token in positive, f"profile positive prompt missing: {token}")
    for token in ("identity drift", "scene change", "background change", "terminal frame corruption"):
        require(token in negative, f"profile negative prompt missing: {token}")
    boundaries = profile.get("runtime_boundaries", {})
    required_true = {
        "local_readiness_only",
        "targeted_rerun_shot",
        "material_route_change_from_failed_animatediff",
        "requires_direct_before_after_temporal_review_after_execution",
    }
    required_false = {
        "retry_allowed",
        "ec2_start_allowed",
        "generation_allowed",
        "gold_masks_consumed",
        "body_mask_or_geometry_authority_claimed",
        "mask_promotion_allowed",
        "content_based_suppression",
        "adult_or_nsfw_asset_visibility_restricted",
        "production_video_lane_certification_claimed",
        "wave71_activation_claimed",
        "jira_mutated",
    }
    require(all(boundaries.get(name) is True for name in required_true), "profile required true boundary missing")
    require(all(boundaries.get(name) is False for name in required_false), "profile fail-closed boundary missing")
    require(boundaries.get("authorized_generation_count") == 1, "profile generation count must be one")
    return {"profile_id": profile.get("profile_id"), "seed": SEED, "completed_seed_count": len(prior_seeds), "completed_seeds": sorted(prior_seeds)}


def validate_run_package(root: Path, path: Path, profile: dict[str, Any]) -> dict[str, Any]:
    manifest = load_json(path)
    require(manifest.get("lane_id") == LANE_ID and manifest.get("result") == "pass_local_only", "run package result mismatch")
    require(manifest.get("local_only") is True, "run package must be local-only")
    for name in ("aws_contacted", "comfyui_contacted", "ec2_started", "generation_executed"):
        require(manifest.get(name) is False, f"run package boundary invalid: {name}")
    prompt_profile = manifest.get("prompt_profile", {})
    require(prompt_profile.get("supplied") is True and prompt_profile.get("applied") is True, "run package profile not applied")
    require(prompt_profile.get("profile_id") == profile.get("profile_id"), "run package profile identity mismatch")
    source_binding = prompt_profile.get("source_binding", {})
    require(source_binding.get("valid") is True, "run package source binding invalid")
    require(source_binding.get("staged_filename") == STAGED_FILENAME, "run package source filename mismatch")
    require(source_binding.get("sha256") == SOURCE_SHA256 and source_binding.get("size_bytes") == SOURCE_BYTES, "run package source binding mismatch")
    packaged_source = (root / str(source_binding.get("packaged", ""))).resolve()
    require(bind(packaged_source, root)["sha256"] == SOURCE_SHA256, "packaged source hash mismatch")
    prompt_record = manifest.get("prompt_request", {})
    generated = {record.get("purpose"): record for record in manifest.get("generated_files", []) if isinstance(record, dict)}
    request_record = generated.get("Patched ComfyUI /prompt request body for later runtime execution.")
    require(isinstance(request_record, dict), "run package prompt request record missing")
    request_path = (root / str(request_record.get("path", ""))).resolve()
    require(sha256_file(request_path) == prompt_record.get("sha256") == request_record.get("sha256"), "run package prompt request hash mismatch")
    prompt = load_json(request_path).get("prompt", {})
    patches = profile["request_patch_values"]
    require(prompt.get("7", {}).get("inputs", {}).get("image") == STAGED_FILENAME, "prompt source image mismatch")
    require(prompt.get("9", {}).get("inputs", {}).get("seed") == SEED, "prompt seed mismatch")
    require(prompt.get("4", {}).get("inputs", {}).get("text") == patches["positive_prompt"], "prompt positive text mismatch")
    require(prompt.get("5", {}).get("inputs", {}).get("text") == patches["negative_prompt"], "prompt negative text mismatch")
    require(prompt.get("12", {}).get("inputs", {}).get("filename_prefix") == OUTPUT_PREFIX, "prompt output prefix mismatch")
    boundaries = manifest.get("runtime_boundaries", {})
    require(boundaries.get("ec2_start_allowed_by_package") is False and boundaries.get("generation_allowed_by_package") is False, "run package authorized runtime")
    return bind(path, root) | {"run_id": manifest.get("run_id"), "prompt_request": bind(request_path, root), "packaged_source": bind(packaged_source, root)}


def build_evidence(root: Path, profile_path: Path, run_package_path: Path | None, timestamp: str) -> dict[str, Any]:
    source = validate_source(root)
    prior_seeds = completed_wan_seeds(root)
    profile = load_json(profile_path)
    profile_result = validate_profile(profile, source, prior_seeds)
    workflow = load_json(root / WORKFLOW_REL)
    required_nodes = {"UNETLoader", "CLIPLoader", "VAELoader", "CLIPTextEncode", "ModelSamplingSD3", "LoadImage", "Wan22ImageToVideoLatent", "KSampler", "VAEDecode", "CreateVideo", "SaveVideo"}
    require({record.get("class_type") for record in workflow.values() if isinstance(record, dict)} >= required_nodes, "Wan workflow node contract incomplete")
    run_package = validate_run_package(root, run_package_path, profile) if run_package_path else None
    checks = [
        "row023_rerun_shot_route_exact",
        "failed_frames_5_6_7_excluded",
        "passed_frames_0_through_4_hash_bound",
        "frame_2_is_deterministic_passed_frame_medoid",
        "frame_2_source_hash_size_dimensions_exact",
        "wan_route_is_material_model_change",
        "seed_2272301_not_previously_completed",
        "source_binding_and_prompt_contract_exact",
        "one_generation_zero_retry_boundary_exact",
        "mask_wave71_jira_and_production_claims_false",
        "content_based_suppression_false",
        "wan_native_node_contract_complete",
    ]
    if run_package:
        checks.extend(["run_package_local_only_pass", "run_package_source_and_prompt_hash_bound", "run_package_authorizes_no_ec2_or_generation"])
    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W64-ROW023-WAN-RERUN-LOCAL-READINESS-{timestamp.replace('-', '').replace(':', '')}",
        "timestamp": timestamp,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "classification": "ROW023_WAN_RERUN_RUN_PACKAGE_LOCAL_READINESS_PASS" if run_package else "ROW023_WAN_RERUN_SOURCE_PROFILE_LOCAL_READINESS_PASS",
        "status": "ready_local_only_runtime_not_authorized",
        "source_sequence": source,
        "profile": bind(profile_path, root) | profile_result,
        "prior_wan_runtime": {
            "completed_seeds": sorted(prior_seeds),
            "replacement_reuse_eligible": False,
            "reason": "Existing Wan clips bind different source identities and environments; they cannot prove preservation of the failed AnimateDiff shot.",
        },
        "run_package": run_package,
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "runtime_gate": {
            "local_comfyui_required_nodes_present": True,
            "local_wan_model_payloads_present": False,
            "target_runtime_required": True,
            "ec2_start_authorized_by_this_evidence": False,
            "generation_authorized_by_this_evidence": False,
            "authorized_future_candidate_count_after_all_external_gates": 1,
            "retry_allowed": False,
        },
        "boundaries": {
            "generation_executed": False,
            "aws_contacted_by_validator": False,
            "ec2_started": False,
            "gold_masks_consumed": False,
            "mask_or_geometry_authority_claimed": False,
            "mask_promotion_claimed": False,
            "production_video_lane_certification_claimed": False,
            "content_based_suppression": False,
            "adult_or_nsfw_asset_visibility_restricted": False,
            "wave71_activation_claimed": False,
            "jira_mutated": False,
        },
        "result": "pass_local_readiness_only",
        "next_action": "Checkpoint this exact profile and validator through protected main, rebuild the run package and deploy bundle from the merge head, then require fresh AWS auth, emergency-stop, watchdog, static-model, bundle-hash, and dry-run gates before one target-runtime candidate.",
    }
    return evidence


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--profile", type=Path, default=Path(PROFILE_REL))
    parser.add_argument("--run-package-manifest", type=Path)
    parser.add_argument("--timestamp", default=datetime.now().astimezone().isoformat(timespec="seconds"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracker-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.project_root.resolve()
        profile_path = (args.profile if args.profile.is_absolute() else root / args.profile).resolve()
        run_package = None if args.run_package_manifest is None else (args.run_package_manifest if args.run_package_manifest.is_absolute() else root / args.run_package_manifest).resolve()
        outputs = [(path if path.is_absolute() else root / path).resolve() for path in (args.output, args.tracker_output)]
        for path in [profile_path, *outputs] + ([run_package] if run_package else []):
            path.relative_to(root)
        evidence = build_evidence(root, profile_path, run_package, args.timestamp)
        for path in outputs:
            write_atomic(path, evidence)
        print(json.dumps({"status": evidence["status"], "classification": evidence["classification"], "checks": evidence["check_summary"], "outputs": [repo_path(path, root) for path in outputs]}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, zlib.error) as exc:
        print(json.dumps({"status": "failed_closed", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
