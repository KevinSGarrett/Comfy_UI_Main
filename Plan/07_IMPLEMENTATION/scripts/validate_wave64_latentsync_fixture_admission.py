#!/usr/bin/env python3
"""Validate the exact rights-scoped LatentSync video/audio fixture admission."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPECTED_FIXTURE_ID = "latentsync-row137-fictional-adult-pd-speech-v1"
ALLOWED_TRUE = {
    "local_fixture_binding",
    "rights_provenance_validation",
    "technical_decode_validation",
    "remote_storage_stage",
    "atomic_no_overwrite_publish",
    "storage_receipt",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(admission: dict, *, verify_local_files: bool = True) -> list[str]:
    errors: list[str] = []
    if admission.get("fixture_id") != EXPECTED_FIXTURE_ID:
        errors.append("fixture id mismatch")
    if admission.get("status") != "RIGHTS_AND_TECHNICAL_FIXTURE_ADMITTED_STORAGE_PUBLISH_PENDING":
        errors.append("fixture admission status mismatch")
    remote = admission.get("remote", {})
    if remote.get("target_root") != (
        "/workspace/w64_aqa/fixtures/W64-AQA-017/"
        "latentsync-row137-fictional-adult-pd-speech-v1"
    ):
        errors.append("fixture target root mismatch")
    if remote.get("atomic_publish") is not True or remote.get("overwrite_forbidden") is not True:
        errors.append("fixture publish policy must be atomic and no-overwrite")

    video = admission.get("video", {})
    audio = admission.get("audio", {})
    if video.get("origin") != "project_generated_comfyui_wan_2_2_ti2v_5b":
        errors.append("video is not bound to the admitted project-generated origin")
    if video.get("rights_basis") != (
        "project_generated_unnamed_fictional_adult_no_named_likeness_in_prompt"
    ):
        errors.append("video rights basis mismatch")
    review = video.get("visual_review", {})
    if review.get("all_frames_reviewed") is not True:
        errors.append("all video frames were not reviewed")
    if review.get("single_face_functional_fixture") is not True:
        errors.append("single-face fixture finding missing")
    if review.get("golden_identity_authority") is not False:
        errors.append("fixture cannot grant golden identity authority")
    if review.get("product_quality_authority") is not False:
        errors.append("fixture cannot grant product quality authority")
    if audio.get("voice_rights") != "Public Domain Mark 1.0 LibriVox excerpt":
        errors.append("audio voice rights mismatch")
    if "CC-BY-4.0" not in audio.get("foley_rights", ""):
        errors.append("audio foley attribution policy missing")
    if audio.get("expected_transcript") != "Once upon a midnight":
        errors.append("fixture transcript mismatch")

    authority = admission.get("authority", {})
    if any(authority.get(name) is not True for name in ALLOWED_TRUE):
        errors.append("required fixture-staging authority missing")
    if any(value is not False for name, value in authority.items() if name not in ALLOWED_TRUE):
        errors.append("fixture admission exceeds storage-only authority")
    limits = admission.get("limits", {})
    required_forbidden = {
        "golden_identity_truth",
        "general_identity_preservation",
        "general_av_sync_quality",
        "general_visual_quality",
        "human_review_substitution",
        "product_approval",
    }
    if set(limits.get("forbidden_inferences", [])) != required_forbidden:
        errors.append("fixture forbidden-inference set mismatch")

    if verify_local_files:
        for label, item in (("video", video), ("audio", audio)):
            path = ROOT / item.get("local_path", "")
            if not path.is_file():
                errors.append(f"{label} fixture file missing")
                continue
            if path.stat().st_size != item.get("bytes"):
                errors.append(f"{label} fixture size mismatch")
            if sha256(path) != item.get("sha256"):
                errors.append(f"{label} fixture sha256 mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("admission", type=Path)
    parser.add_argument("--skip-local-files", action="store_true")
    args = parser.parse_args()
    admission = json.loads(args.admission.read_text(encoding="utf-8"))
    errors = validate(admission, verify_local_files=not args.skip_local_files)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_LATENTSYNC_FIXTURE_ADMISSION_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
