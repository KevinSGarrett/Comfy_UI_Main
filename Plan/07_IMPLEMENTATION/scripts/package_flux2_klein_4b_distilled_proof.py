from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageStat


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LANE_ID = "flux2_klein_4b_distilled"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def history_entry(history: dict[str, Any], prompt_id: str) -> dict[str, Any]:
    entry = history.get(prompt_id)
    if not isinstance(entry, dict):
        raise ValueError(f"History is missing prompt {prompt_id}")
    prompt = entry.get("prompt")
    if not isinstance(prompt, list) or len(prompt) < 4 or str(prompt[1]) != prompt_id:
        raise ValueError(f"History prompt binding is invalid for {prompt_id}")
    return entry


def timing(entry: dict[str, Any]) -> dict[str, Any]:
    stamps: dict[str, int] = {}
    cached: list[str] | None = None
    for message in entry.get("status", {}).get("messages", []):
        if not isinstance(message, list) or len(message) != 2 or not isinstance(message[1], dict):
            continue
        name, payload = message
        if name in {"execution_start", "execution_success"} and isinstance(payload.get("timestamp"), int):
            stamps[name] = payload["timestamp"]
        if name == "execution_cached":
            cached = [str(item) for item in payload.get("nodes", [])]
    start, end = stamps.get("execution_start"), stamps.get("execution_success")
    return {
        "execution_start_epoch_ms": start,
        "execution_success_epoch_ms": end,
        "elapsed_seconds": round((end - start) / 1000.0, 3) if start is not None and end is not None else None,
        "cached_nodes": cached,
    }


def outputs(entry: dict[str, Any]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for node_id, node_output in (entry.get("outputs") or {}).items():
        if not isinstance(node_output, dict):
            continue
        for image in node_output.get("images", []) or []:
            if isinstance(image, dict):
                result.append({"node_id": str(node_id), "filename": str(image.get("filename") or ""), "subfolder": str(image.get("subfolder") or ""), "type": str(image.get("type") or "")})
    return result


def output_matches(records: list[dict[str, str]], artifact: Path, node_id: str) -> bool:
    return (
        len(records) == 1
        and records[0]["node_id"] == node_id
        and records[0]["filename"] == artifact.name
        and records[0]["subfolder"] == LANE_ID
        and records[0]["type"] == "output"
    )


def image_qa(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        extrema = rgb.getextrema()
        stat = ImageStat.Stat(rgb)
        return {
            "opened": True,
            "format": image.format,
            "mode": image.mode,
            "width": image.width,
            "height": image.height,
            "channel_mean": [round(value, 6) for value in stat.mean],
            "channel_stddev": [round(value, 6) for value in stat.stddev],
            "nonblank_variance_pass": any(high > low for low, high in extrema),
        }


def mean_abs_delta(first: Image.Image, second: Image.Image) -> float:
    stat = ImageStat.Stat(ImageChops.difference(first.convert("RGB"), second.convert("RGB")))
    return round(sum(stat.mean) / 3.0, 6)


def edit_metrics(source: Path, edited: Path) -> dict[str, Any]:
    with Image.open(source) as a, Image.open(edited) as b:
        left, top, right, bottom = 40, 120, 475, 370
        inside = mean_abs_delta(a.crop((left, top, right, bottom)), b.crop((left, top, right, bottom)))
        outside_regions = [(0, 0, 512, top), (0, bottom, 512, 512), (0, top, left, bottom), (right, top, 512, bottom)]
        weighted_total = 0.0
        pixel_total = 0
        for box in outside_regions:
            pixels = (box[2] - box[0]) * (box[3] - box[1])
            weighted_total += mean_abs_delta(a.crop(box), b.crop(box)) * pixels
            pixel_total += pixels
        return {
            "bag_roi": [left, top, right, bottom],
            "inside_bag_roi_mean_abs_rgb_delta": inside,
            "outside_bag_roi_mean_abs_rgb_delta": round(weighted_total / pixel_total, 6),
            "targeted_change_concentration_pass": inside > (weighted_total / pixel_total) * 3.0,
        }


def validate_review(review: dict[str, Any], artifact_sha: str, source_sha: str | None = None) -> list[str]:
    failures: list[str] = []
    if review.get("artifact_sha256") != artifact_sha:
        failures.append("artifact_hash_mismatch")
    if source_sha is not None and review.get("source_artifact_sha256") != source_sha:
        failures.append("source_hash_mismatch")
    checks = review.get("checks")
    if not isinstance(checks, dict) or not checks or not all(value is True for value in checks.values()):
        failures.append("review_checks_not_all_true")
    if review.get("visual_pass") is not True:
        failures.append("visual_pass_false")
    return failures


def make_panel(paths: list[tuple[str, Path]], output: Path) -> None:
    tile = 512
    label_height = 32
    columns = 3
    rows = (len(paths) + columns - 1) // columns
    panel = Image.new("RGB", (columns * tile, rows * (tile + label_height)), "white")
    draw = ImageDraw.Draw(panel)
    for index, (label, path) in enumerate(paths):
        x = (index % columns) * tile
        y = (index // columns) * (tile + label_height)
        with Image.open(path) as image:
            panel.paste(image.convert("RGB").resize((tile, tile), Image.Resampling.LANCZOS), (x, y))
        draw.rectangle((x, y + tile, x + tile, y + tile + label_height), fill=(24, 24, 24))
        draw.text((x + 10, y + tile + 9), label, fill="white")
    output.parent.mkdir(parents=True, exist_ok=True)
    panel.save(output)


def http_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=60) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object from {url}")
    return value


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package bounded FLUX.2 Klein 4B T2I/edit runtime proof")
    parser.add_argument("--api-url", default="http://127.0.0.1:8188")
    parser.add_argument("--requirements", required=True)
    parser.add_argument("--t2i-workflow", required=True)
    parser.add_argument("--edit-workflow", required=True)
    parser.add_argument("--t2i-history", required=True)
    parser.add_argument("--t2i-prompt-id", required=True)
    parser.add_argument("--edit-history", required=True)
    parser.add_argument("--edit-prompt-id", required=True)
    parser.add_argument("--matched-klein-history", required=True)
    parser.add_argument("--matched-klein-prompt-id", required=True)
    parser.add_argument("--matched-klein-workflow", required=True)
    parser.add_argument("--realvis-history", required=True)
    parser.add_argument("--realvis-prompt-id", required=True)
    parser.add_argument("--realvis-workflow", required=True)
    parser.add_argument("--t2i-artifact", required=True)
    parser.add_argument("--matched-klein-artifact", required=True)
    parser.add_argument("--realvis-artifact", required=True)
    parser.add_argument("--edit-source", required=True)
    parser.add_argument("--edit-artifact", required=True)
    parser.add_argument("--schnell-evidence", required=True)
    parser.add_argument("--t2i-review", required=True)
    parser.add_argument("--edit-review", required=True)
    parser.add_argument("--comparison-review", required=True)
    parser.add_argument("--model-root", required=True)
    parser.add_argument("--output-evidence", required=True)
    parser.add_argument("--mirror-evidence", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    requirements_path = Path(args.requirements).resolve()
    requirements = load_json(requirements_path)
    workflow_paths = {"text_to_image": Path(args.t2i_workflow).resolve(), "single_reference_edit": Path(args.edit_workflow).resolve()}
    workflows = {name: load_json(path) for name, path in workflow_paths.items()}
    histories = {
        "text_to_image": (load_json(Path(args.t2i_history)), args.t2i_prompt_id, workflows["text_to_image"]),
        "single_reference_edit": (load_json(Path(args.edit_history)), args.edit_prompt_id, workflows["single_reference_edit"]),
        "matched_klein": (load_json(Path(args.matched_klein_history)), args.matched_klein_prompt_id, load_json(Path(args.matched_klein_workflow))),
        "realvisxl": (load_json(Path(args.realvis_history)), args.realvis_prompt_id, load_json(Path(args.realvis_workflow))),
    }
    entries = {name: history_entry(history, prompt_id) for name, (history, prompt_id, _workflow) in histories.items()}
    timings = {name: timing(entry) for name, entry in entries.items()}
    output_records = {name: outputs(entry) for name, entry in entries.items()}
    artifacts = {
        "text_to_image": Path(args.t2i_artifact).resolve(),
        "matched_klein": Path(args.matched_klein_artifact).resolve(),
        "realvisxl": Path(args.realvis_artifact).resolve(),
        "edit_source": Path(args.edit_source).resolve(),
        "single_reference_edit": Path(args.edit_artifact).resolve(),
    }
    artifact_hashes = {name: sha256_file(path) for name, path in artifacts.items()}
    object_info = http_json(f"{args.api_url.rstrip('/')}/object_info")
    model_root = Path(args.model_root).resolve()
    model_reports: list[dict[str, Any]] = []
    for model in requirements["required_models"]:
        path = model_root / model["comfyui_model_subdir"] / model["filename"]
        model_reports.append({**model, "path": str(path), "observed_bytes": path.stat().st_size if path.is_file() else None, "observed_sha256": sha256_file(path) if path.is_file() else None})

    t2i_review = load_json(Path(args.t2i_review))
    edit_review = load_json(Path(args.edit_review))
    comparison_review = load_json(Path(args.comparison_review))
    source_sha = artifact_hashes["edit_source"]
    comparison_hashes = comparison_review.get("artifacts") or {}
    metrics = edit_metrics(artifacts["edit_source"], artifacts["single_reference_edit"])
    required_nodes = [str(item) for item in requirements["required_nodes"]]
    required_models_by_role = {str(model["role"]): str(model["filename"]) for model in requirements["required_models"]}
    all_model_names = json.dumps(object_info, separators=(",", ":"))
    dynamic_edit_nodes = {"4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "16", "17", "18", "19"}
    checks = {
        "lane_id_matches": requirements.get("lane_id") == LANE_ID,
        "separate_workflow_files": workflow_paths["text_to_image"] != workflow_paths["single_reference_edit"] and sha256_file(workflow_paths["text_to_image"]) != sha256_file(workflow_paths["single_reference_edit"]),
        "required_nodes_visible": all(node in object_info for node in required_nodes),
        "all_models_present": all(report["observed_bytes"] is not None for report in model_reports),
        "all_model_bytes_match": all(report["observed_bytes"] == report["bytes"] for report in model_reports),
        "all_model_hashes_match": all(report["observed_sha256"] == report["sha256"] for report in model_reports),
        "all_models_visible": all(report["filename"] in all_model_names for report in model_reports),
        "all_histories_success": all(entry.get("status", {}).get("status_str") == "success" and entry.get("status", {}).get("completed") is True for entry in entries.values()),
        "canonical_t2i_history_binding": entries["text_to_image"]["prompt"][2] == workflows["text_to_image"],
        "canonical_edit_history_binding": entries["single_reference_edit"]["prompt"][2] == workflows["single_reference_edit"],
        "matched_klein_history_binding": entries["matched_klein"]["prompt"][2] == histories["matched_klein"][2],
        "realvis_history_binding": entries["realvisxl"]["prompt"][2] == histories["realvisxl"][2],
        "uncached_first_klein_run": timings["text_to_image"]["cached_nodes"] == [],
        "edit_dynamic_path_executed": not dynamic_edit_nodes.intersection(set(timings["single_reference_edit"]["cached_nodes"] or [])),
        "realvis_comparison_uncached": timings["realvisxl"]["cached_nodes"] == [],
        "all_timings_complete": all(value["elapsed_seconds"] is not None and value["elapsed_seconds"] > 0 for value in timings.values()),
        "single_output_per_run": all(len(value) == 1 for value in output_records.values()),
        "t2i_history_output_bound_to_artifact": output_matches(output_records["text_to_image"], artifacts["text_to_image"], "13"),
        "edit_history_output_bound_to_artifact": output_matches(output_records["single_reference_edit"], artifacts["single_reference_edit"], "19"),
        "matched_klein_history_output_bound_to_artifact": output_matches(output_records["matched_klein"], artifacts["matched_klein"], "13"),
        "realvis_history_output_bound_to_artifact": output_matches(output_records["realvisxl"], artifacts["realvisxl"], "9"),
        "all_artifacts_512_square": all(image_qa(path)["width"] == 512 and image_qa(path)["height"] == 512 for path in artifacts.values()),
        "all_artifacts_nonblank": all(image_qa(path)["nonblank_variance_pass"] is True for path in artifacts.values()),
        "t2i_visual_review_pass": not validate_review(t2i_review, artifact_hashes["text_to_image"]),
        "edit_visual_review_pass": not validate_review(edit_review, artifact_hashes["single_reference_edit"], source_sha),
        "comparison_visual_review_pass": comparison_review.get("visual_pass") is True and all(value is True for value in (comparison_review.get("checks") or {}).values()),
        "comparison_hashes_match": comparison_hashes.get("flux1_schnell", {}).get("sha256") == source_sha and comparison_hashes.get("flux2_klein_4b_distilled", {}).get("sha256") == artifact_hashes["matched_klein"] and comparison_hashes.get("realvisxl_v5", {}).get("sha256") == artifact_hashes["realvisxl"],
        "matched_comparison_seed": histories["matched_klein"][2]["7"]["inputs"]["noise_seed"] == 7162601 and histories["realvisxl"][2]["3"]["inputs"]["seed"] == 7162601,
        "matched_comparison_prompt": histories["matched_klein"][2]["4"]["inputs"]["text"] == histories["realvisxl"][2]["6"]["inputs"]["text"] == workflows["text_to_image"]["4"]["inputs"]["text"],
        "edit_source_workflow_binding": workflows["single_reference_edit"]["4"]["inputs"]["image"] == artifacts["edit_source"].name,
        "canonical_flux2_model_bindings": workflows["text_to_image"]["1"]["inputs"]["unet_name"] == required_models_by_role["diffusion_model"] and workflows["single_reference_edit"]["1"]["inputs"]["unet_name"] == required_models_by_role["diffusion_model"] and workflows["text_to_image"]["2"]["inputs"]["clip_name"] == required_models_by_role["text_encoder"] and workflows["single_reference_edit"]["2"]["inputs"]["clip_name"] == required_models_by_role["text_encoder"] and workflows["text_to_image"]["3"]["inputs"]["vae_name"] == required_models_by_role["vae"] and workflows["single_reference_edit"]["3"]["inputs"]["vae_name"] == required_models_by_role["vae"],
        "canonical_workflows_do_not_load_cross_family_checkpoint": "CheckpointLoaderSimple" not in json.dumps(workflows, separators=(",", ":")),
        "edit_targeted_change_concentrated": metrics["targeted_change_concentration_pass"] is True,
        "schnell_lineage_hash_bound": load_json(Path(args.schnell_evidence)).get("artifact", {}).get("sha256") == source_sha,
        "production_not_promoted": comparison_review.get("production_default_promoted") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"FLUX.2 Klein proof checks failed: {failed}")

    output_path = Path(args.output_evidence).resolve()
    mirror_path = Path(args.mirror_evidence).resolve()
    artifact_dir = output_path.parent / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, dict[str, Any]] = {}
    for name, source in artifacts.items():
        target = artifact_dir / source.name
        if not target.exists():
            shutil.copy2(source, target)
        if sha256_file(target) != artifact_hashes[name]:
            raise RuntimeError(f"Copied artifact hash mismatch: {target}")
        copied[name] = {"path": rel(target), "bytes": target.stat().st_size, "sha256": artifact_hashes[name], "technical_qa": image_qa(target)}
    panel_path = output_path.parent / "flux2_klein_comparison_panel.png"
    make_panel([
        ("FLUX.1 Schnell seed 7162601", artifacts["edit_source"]),
        ("FLUX.2 Klein seed 7162601", artifacts["matched_klein"]),
        ("RealVisXL seed 7162601", artifacts["realvisxl"]),
        ("FLUX.2 Klein uncached seed 7162602", artifacts["text_to_image"]),
        ("Edit source: crimson", artifacts["edit_source"]),
        ("FLUX.2 edit: cobalt", artifacts["single_reference_edit"]),
    ], panel_path)

    payload = {
        "schema_version": "1.0",
        "evidence_id": "W64-FLUX2-KLEIN-4B-DISTILLED-LOCAL-RUNTIME-20260716T133738-0500",
        "created_at": "2026-07-16T13:37:38-05:00",
        "lane_id": LANE_ID,
        "classification": "bounded_local_flux2_klein_t2i_and_reference_edit_pass",
        "model_assets": model_reports,
        "workflows": {name: {"path": rel(path), "sha256": sha256_file(path)} for name, path in workflow_paths.items()},
        "runtime": {
            "api_url": args.api_url,
            "prompt_ids": {name: histories[name][1] for name in histories},
            "timings": timings,
            "outputs": output_records,
            "required_node_presence": {node: node in object_info for node in required_nodes},
        },
        "capabilities": {
            "text_to_image": {"workflow_path": rel(workflow_paths["text_to_image"]), "runtime_pass": True, "artifact_hash_bound": True, "direct_visual_qa_pass": True},
            "single_reference_edit": {"workflow_path": rel(workflow_paths["single_reference_edit"]), "runtime_pass": True, "artifact_hash_bound": True, "direct_visual_qa_pass": True},
        },
        "artifacts": copied,
        "edit_metrics": metrics,
        "comparison": {
            "panel": {"path": rel(panel_path), "sha256": sha256_file(panel_path)},
            "matched_seed": 7162601,
            "review": comparison_review,
            "decision": comparison_review["bounded_decision"],
        },
        "visual_reviews": {"text_to_image": t2i_review, "single_reference_edit": edit_review},
        "checks": checks,
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "boundaries": {
            "local_8gb_runtime_proven": True,
            "klein_local_first_flux2_lane_supported": True,
            "flux2_dev_disqualified_by_license": False,
            "flux2_dev_remains_eligible": True,
            "flux2_dev_runtime_proven": False,
            "broad_prompt_seed_or_resolution_robustness_claimed": False,
            "production_ready": False,
            "ec2_started": False,
            "aws_or_s3_mutated": False,
            "mask_or_wave71_authority_claimed": False,
            "jira_mutated": False
        },
        "production_ready": False,
        "result": "pass_bounded_local_flux2_klein_t2i_and_single_reference_edit",
    }
    write_json(output_path, payload)
    write_json(mirror_path, payload)
    print(json.dumps({"status": "PASS", "evidence": rel(output_path), "mirror": rel(mirror_path), "checks": payload["check_summary"], "panel": rel(panel_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
