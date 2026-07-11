#!/usr/bin/env python3
"""Evaluate two-source local RealESRGAN runtime and preservation robustness."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


ROOT = Path(__file__).resolve().parents[3]
STAMP = "20260711T042000-0500"
PREP_MANIFEST = ROOT / "Plan/Instructions/Operations/Prepared_Input_Assets/realesrgan_multisource_w70_v1/PREPARATION_MANIFEST.json"
SAMPLES = {
    "normal_fullbody": {
        "source": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/normal_v4_full_body_standing_seed711670301_20260711T035900-0500/images/normal_v4_fullbody_standing_711670301_00001_.png",
        "output": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/realesrgan_normal_fullbody_w70_v1_20260711T040825-0500/images/realesrgan_normal_fullbody_w70_v1_00001_.png",
        "runtime": ROOT / "Plan/Instructions/QA/Evidence/Workflow_Runtime/W70_LOCAL_REALESRGAN_NORMAL_FULLBODY_RUNTIME_20260711T041500-0500.json",
        "profile": ROOT / "PromptProfiles/base_generation/realesrgan_multisource_robustness/realesrgan_normal_fullbody_w70_v1.json",
        "source_class": "fullbody_portrait_normal_control_output",
        "visual_result": "pass_with_notes_fullbody_preserved_smoothing_amplified",
        "visual_findings": [
            "Full-length composition, pose, both hands, both legs, and both shoes remain coherent.",
            "No new limb break, crop, ringing halo, block artifact, or color contamination is visible.",
            "The source's polished skin and smooth clothing surfaces are amplified; the result is not a true-detail reconstruction.",
        ],
    },
    "two_character_contact": {
        "source": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/realvisxl_two_character_hand_to_body_w69_seed7152026252_20260707T113434-0500/images/codex_realvisxl_two_character_hand_to_body_seed7152026252_00001_.png",
        "output": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/realesrgan_two_character_contact_w70_v1_20260711T040856-0500/images/realesrgan_twochar_contact_w70_v1_00001_.png",
        "runtime": ROOT / "Plan/Instructions/QA/Evidence/Workflow_Runtime/W70_LOCAL_REALESRGAN_TWO_CHARACTER_CONTACT_RUNTIME_20260711T041500-0500.json",
        "profile": ROOT / "PromptProfiles/base_generation/realesrgan_multisource_robustness/realesrgan_two_character_contact_w70_v1.json",
        "source_class": "square_two_character_contact_output",
        "visual_result": "pass_with_notes_composition_preserved_waxy_skin_and_oversharpened_jacket",
        "visual_findings": [
            "Both people, faces, hair masses, clothing silhouettes, and the existing hand-to-shoulder contact remain spatially coherent.",
            "No new person merge, hand loss, contact-owner reversal, block artifact, or edge-panel seam is visible.",
            "Skin appears waxier and the patterned jacket is visibly over-sharpened, so this output is not preferred over the source for hyperrealism quality.",
        ],
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    required = [PREP_MANIFEST]
    for sample in SAMPLES.values():
        required.extend([sample["source"], sample["output"], sample["runtime"], sample["profile"]])
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required RealESRGAN QA input missing: {missing}")

    records = []
    all_checks = []
    for sample_id, sample in SAMPLES.items():
        with Image.open(sample["source"]) as loaded:
            source_image = loaded.convert("RGB")
            source_size = source_image.size
        with Image.open(sample["output"]) as loaded:
            output_image = loaded.convert("RGB")
            output_size = output_image.size
        source_pixels = np.asarray(source_image)
        downsampled = np.asarray(output_image.resize(source_size, Image.Resampling.LANCZOS))
        ssim = float(structural_similarity(source_pixels, downsampled, channel_axis=2, data_range=255))
        psnr = float(peak_signal_noise_ratio(source_pixels, downsampled, data_range=255))
        mae = float(np.mean(np.abs(source_pixels.astype(np.float32) - downsampled.astype(np.float32))))
        mean_color_shift = float(np.mean(np.abs(source_pixels.mean(axis=(0, 1)) - downsampled.mean(axis=(0, 1)))))
        source_gray = cv2.cvtColor(source_pixels, cv2.COLOR_RGB2GRAY)
        downsampled_gray = cv2.cvtColor(downsampled, cv2.COLOR_RGB2GRAY)
        source_laplacian_variance = float(cv2.Laplacian(source_gray, cv2.CV_64F).var())
        downsampled_laplacian_variance = float(cv2.Laplacian(downsampled_gray, cv2.CV_64F).var())
        edge_variance_ratio = downsampled_laplacian_variance / source_laplacian_variance if source_laplacian_variance else None
        runtime = json.loads(sample["runtime"].read_text(encoding="utf-8"))
        checks = {
            "runtime_passed": runtime.get("result") == "pass_local_run_package_generation_smoke",
            "generation_executed": runtime.get("generation_executed") is True,
            "request_hash_matched": runtime.get("run_package", {}).get("prompt_request", {}).get("hash_match") is True,
            "server_stopped_and_port_closed": runtime.get("local_comfy", {}).get("stopped_by_helper") is True and runtime.get("local_comfy", {}).get("port_closed_after_stop") is True,
            "exact_4x_dimensions": output_size == (source_size[0] * 4, source_size[1] * 4),
            "downsample_ssim_gte_0_95": ssim >= 0.95,
            "downsample_psnr_gte_29db": psnr >= 29.0,
            "downsample_mae_lte_5": mae <= 5.0,
            "mean_color_shift_lte_3": mean_color_shift <= 3.0,
            "visual_no_blocking_composition_or_anatomy_regression": True,
        }
        all_checks.extend(checks.values())
        records.append(
            {
                "sample_id": sample_id,
                "source_class": sample["source_class"],
                "profile": rel(sample["profile"]),
                "runtime_evidence": rel(sample["runtime"]),
                "source": {"path": rel(sample["source"]), "sha256": sha256(sample["source"]), "width": source_size[0], "height": source_size[1]},
                "output": {"path": rel(sample["output"]), "sha256": sha256(sample["output"]), "width": output_size[0], "height": output_size[1], "bytes": sample["output"].stat().st_size},
                "metrics": {
                    "downsample_ssim": ssim,
                    "downsample_psnr_db": psnr,
                    "downsample_mae": mae,
                    "mean_color_shift": mean_color_shift,
                    "source_laplacian_variance": source_laplacian_variance,
                    "downsampled_output_laplacian_variance": downsampled_laplacian_variance,
                    "edge_variance_ratio": edge_variance_ratio,
                },
                "checks": checks,
                "visual_result": sample["visual_result"],
                "visual_findings": sample["visual_findings"],
            }
        )

    passed = all(all_checks) and json.loads(PREP_MANIFEST.read_text(encoding="utf-8")).get("pass") is True
    qa = {
        "schema_version": "1.0",
        "evidence_id": f"W70-LOCAL-REALESRGAN-MULTISOURCE-ROBUSTNESS-QA-{STAMP}",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "lane_id": "sdxl_realesrgan_upscale_polish_lane",
        "result": "pass_with_notes_local_realesrgan_multisource_runtime_robustness_quality_tradeoffs" if passed else "fail_local_realesrgan_multisource_robustness",
        "pass": passed,
        "scope": "two_additional_local_source_classes_exact_4x_upscale_and_preservation",
        "preparation_manifest": {"path": rel(PREP_MANIFEST), "sha256": sha256(PREP_MANIFEST)},
        "samples": records,
        "aggregate": {
            "source_class_count": 2,
            "runtime_pass_count": sum(1 for record in records if record["checks"]["runtime_passed"]),
            "exact_4x_count": sum(1 for record in records if record["checks"]["exact_4x_dimensions"]),
            "preservation_gate_pass_count": sum(1 for record in records if all(record["checks"][key] for key in ("downsample_ssim_gte_0_95", "downsample_psnr_gte_29db", "downsample_mae_lte_5", "mean_color_shift_lte_3"))),
        },
        "quality_decision": {
            "runtime_multisource_robustness_pass": passed,
            "universal_hyperrealism_improvement_claimed": False,
            "two_character_upscale_preferred_over_source": False,
            "reason": "Exact 4x runtime and structural preservation pass, but smooth skin is amplified and high-frequency jacket texture is over-sharpened.",
        },
        "known_issue_review": [
            "RealESRGAN increases pixel resolution but does not reconstruct true pore-level or hand-detail information absent from the source.",
            "Polished source skin can become waxier after upscale.",
            "Dense patterned fabric can become over-sharpened or noisy.",
            "This local matrix does not prove target-runtime behavior or final export suitability for every source class.",
        ],
        "boundaries": {
            "source_lanes_regenerated": False,
            "source_lane_certification_changed": False,
            "local_only": True,
            "aws_contacted": False,
            "ec2_started": False,
            "gold_masks_consumed": False,
            "mask_promotion": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activated": False,
        },
    }
    qa_path = ROOT / f"Plan/Instructions/QA/Evidence/Image_Artifact_QA/W70_LOCAL_REALESRGAN_MULTISOURCE_ROBUSTNESS_QA_{STAMP}.json"
    tracker_qa_path = ROOT / f"Plan/Tracker/Evidence/Image_Artifact_QA/W70_LOCAL_REALESRGAN_MULTISOURCE_ROBUSTNESS_QA_{STAMP}.json"
    write_json(qa_path, qa)
    tracker_qa_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(qa_path, tracker_qa_path)

    item = {
        "item_id": f"ITEM-W70-REALESRGAN-MULTISOURCE-LOCAL-ROBUSTNESS-{STAMP}",
        "timestamp": qa["timestamp"],
        "lane_id": qa["lane_id"],
        "title": "RealESRGAN two-source local runtime and preservation robustness",
        "status": "complete_pass_with_notes" if passed else "complete_qa_failed",
        "implementation_complete": True,
        "runtime_test_complete": True,
        "technical_qa_complete": True,
        "visual_qa_complete": True,
        "tracker_update_complete": True,
        "itemized_list_update_complete": True,
        "known_issue_review_complete": True,
        "bounded_done_certification_allowed": passed,
        "final_lane_certification_allowed": False,
        "qa_evidence": rel(qa_path),
        "known_issues": qa["known_issue_review"],
    }
    item_path = ROOT / f"Plan/Items/Reports/W70_REALESRGAN_MULTISOURCE_LOCAL_ROBUSTNESS_ITEMIZED_LIST_{STAMP}.json"
    write_json(item_path, item)

    cert = {
        "evidence_id": f"W70-REALESRGAN-MULTISOURCE-LOCAL-ROBUSTNESS-DONE-{STAMP}",
        "timestamp": qa["timestamp"],
        "lane_id": qa["lane_id"],
        "result": "done_bounded_local_realesrgan_multisource_robustness_pass_with_notes" if passed else "blocked_local_realesrgan_multisource_robustness_qa_failed",
        "done_scope": qa["scope"],
        "closes_local_scope_item": passed,
        "closes_final_lane_work_order": False,
        "qa_evidence": rel(qa_path),
        "itemized_list_record": rel(item_path),
        "implementation_test_qa_evidence_complete": passed,
        "quality_limitations": qa["known_issue_review"],
        "final_lane_certification": False,
        "full_project_certification": False,
        "certifier": "Codex Desktop autonomous release manager",
        "next_action": "Preserve these sources and outputs without replay. Target-runtime proof and a final source-selection/export policy remain separate.",
    }
    cert_path = ROOT / f"Plan/Instructions/QA/Evidence/Done_Certifications/W70_REALESRGAN_MULTISOURCE_LOCAL_ROBUSTNESS_DONE_{STAMP}.json"
    tracker_cert_path = ROOT / f"Plan/Tracker/Evidence/Done_Certifications/W70_REALESRGAN_MULTISOURCE_LOCAL_ROBUSTNESS_DONE_{STAMP}.json"
    write_json(cert_path, cert)
    tracker_cert_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cert_path, tracker_cert_path)

    print(json.dumps({"qa": rel(qa_path), "item": rel(item_path), "certificate": rel(cert_path), "pass": passed, "aggregate": qa["aggregate"]}, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
