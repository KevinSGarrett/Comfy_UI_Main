#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


RUN_STAMP = "20260710T025800-0500"
TIMESTAMP = "2026-07-10T02:58:00-05:00"
MASK_TYPE_ID = "mf70_teeth_mouth_area"
CANDIDATE_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_TEETH_MOUTH_AREA_POSTPROCESS_V2_20260710T025200-0500.json"
)


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve(root: Path, path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else root / p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def append_unique_text(path: Path, text: str, marker: str) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if marker in existing:
        return
    path.write_text(existing.rstrip() + "\n\n" + text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main", type=Path)
    args = parser.parse_args()
    root = args.project_root

    candidate_path = resolve(root, CANDIDATE_EVIDENCE)
    candidate = read_json(candidate_path)
    if candidate.get("result") != "candidate_created_pending_strict_visual_review_not_promoted":
        raise RuntimeError(f"unexpected candidate result: {candidate.get('result')}")

    review_panel = resolve(root, candidate["review_panel"])
    candidate_mask = resolve(root, candidate["candidate_mask"])
    protected_overlay = resolve(root, candidate["protected_overlay"])
    if not review_panel.exists() or not candidate_mask.exists() or not protected_overlay.exists():
        raise FileNotFoundError("candidate review assets missing")

    lip_overlap = candidate["stats"]["candidate_overlap_with_predicted_lips_pixels"]
    nose_overlap = candidate["stats"]["candidate_overlap_with_predicted_nose_pixels"]
    if nose_overlap != 0:
        raise RuntimeError("candidate overlaps nose and must not be accepted")

    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-TEETH-MOUTH-AREA-POSTPROCESS-V2-STRICT-VISUAL-ACCEPTANCE-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "scope": "strict_source_overlay_visual_review_no_generation",
        "mask_type_id": MASK_TYPE_ID,
        "candidate_evidence": rel(candidate_path, root),
        "candidate_evidence_sha256": sha256_file(candidate_path),
        "candidate_mask": candidate["candidate_mask"],
        "candidate_mask_sha256": sha256_file(candidate_mask),
        "review_panel": candidate["review_panel"],
        "review_panel_sha256": sha256_file(review_panel),
        "protected_overlay": candidate["protected_overlay"],
        "protected_overlay_sha256": sha256_file(protected_overlay),
        "visual_findings": [
            "The v2 candidate sits on the visible mouth/teeth opening and does not drift into hair, cheeks, nose, eyes, chin, or background.",
            "The v2 candidate is intentionally broader than the old active teeth-only strip because the gold benchmark row maps to CelebAMask-HQ mouth area, not just visible teeth.",
            f"Protected overlay reports zero nose overlap and {lip_overlap} pixels of lip-boundary overlap; the lip-boundary overlap is expected for the benchmark-passing mouth-area route and must be checked again in generated-output QA.",
            "The old active teeth mask remains useful only for a teeth-only row; it is not sufficient evidence for the broader mf70_teeth_mouth_area benchmark target.",
        ],
        "strict_review": {
            "source_aligned_for_mouth_area": True,
            "not_a_teeth_only_mask": True,
            "nose_overlap_pixels": nose_overlap,
            "lip_boundary_overlap_pixels": lip_overlap,
            "requires_generated_output_proof": True,
            "requires_target_runtime_or_reference_matrix_before_final": True,
        },
        "decision": "candidate_visual_acceptance_pass_generated_output_pending_not_promoted",
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "generation_executed": False,
        "ec2_started": False,
        "result": "candidate_visual_acceptance_pass_generated_output_pending_not_promoted",
        "next_required_action": (
            "Copy the candidate to a v2-specific ComfyUI input filename and run one bounded local generated-output proof with strict whole-image QA. "
            "Do not overwrite ComfyUI/input/wave70_mf70_teeth_mask.png."
        ),
    }

    out = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / (
        f"W70_MF70_TEETH_MOUTH_AREA_POSTPROCESS_V2_STRICT_VISUAL_ACCEPTANCE_{RUN_STAMP}.json"
    )
    tracker = root / "Plan/Tracker/Evidence" / out.name
    write_json(out, evidence)
    write_json(tracker, evidence)

    marker = evidence["evidence_id"]
    section = f"""## Wave70 mf70_teeth_mouth_area Postprocess V2 Strict Visual Acceptance - {TIMESTAMP}

Strictly reviewed the unpromoted `mf70_teeth_mouth_area` v2 postprocess candidate. Evidence `{rel(out, root)}` reports `candidate_visual_acceptance_pass_generated_output_pending_not_promoted`: the mask is aligned to the visible mouth/teeth opening, has zero nose overlap, and is explicitly a broader mouth-area mask rather than the old teeth-only strip. No active input, mask promotion, generation, EC2, AWS, GitHub, S3, Civitai, final certification, or row completion occurred.
"""
    for path in [
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md",
        root / "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md",
        root / "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md",
        root / "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        append_unique_text(path, section, marker)

    print(json.dumps({"result": evidence["result"], "evidence": rel(out, root), "tracker": rel(tracker, root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
