#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


RUN_STAMP = "20260710T033200-0500"
TIMESTAMP = "2026-07-10T03:32:00-05:00"
MASK_TYPE_ID = "mf70_face_skin"
CANDIDATE_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_FACE_SKIN_HULL_V2_20260710T032500-0500.json"
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
    stats = candidate["stats"]
    review_panel = resolve(root, candidate["review_panel"])
    if not review_panel.exists():
        raise FileNotFoundError(candidate["review_panel"])

    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"W70-MF70-FACE-SKIN-HULL-V2-STRICT-VISUAL-REVIEW-{RUN_STAMP}",
        "timestamp": TIMESTAMP,
        "project_root": str(root),
        "scope": "strict_source_overlay_visual_review_no_generation",
        "mask_type_id": MASK_TYPE_ID,
        "candidate_evidence": rel(candidate_path, root),
        "candidate_evidence_sha256": sha256_file(candidate_path),
        "candidate_mask": candidate["candidate_mask"],
        "candidate_mask_sha256": candidate["candidate_mask_sha256"],
        "review_panel": candidate["review_panel"],
        "review_panel_sha256": sha256_file(review_panel),
        "protected_overlay": candidate["protected_overlay"],
        "protected_overlay_sha256": candidate["protected_overlay_sha256"],
        "route_gold_benchmark_summary": candidate["route_gold_benchmark_summary"],
        "overlap_stats": stats,
        "visual_findings": [
            "The hull route is benchmark-valid but fills the face as a broad oval on the target portrait.",
            "The target overlay visibly covers eyes/eyebrows and lips/mouth, and includes the nose region.",
            "The protected overlay also shows nonzero hair/clothing boundary contact.",
            "This may be acceptable as a semantic dataset skin class, but it is unsafe as a direct runtime inpaint mask for the current facial-detail workflow because it risks changing identity-critical eyes, lips, mouth expression, and nose.",
        ],
        "strict_review": {
            "benchmark_route_passed": True,
            "target_runtime_safe": False,
            "candidate_overlap_with_eye_brow_pixels": stats["candidate_overlap_with_eye_brow_pixels"],
            "candidate_overlap_with_lips_mouth_pixels": stats["candidate_overlap_with_lips_mouth_pixels"],
            "candidate_overlap_with_nose_pixels": stats["candidate_overlap_with_nose_pixels"],
            "candidate_overlap_with_hair_cloth_pixels": stats["candidate_overlap_with_hair_cloth_pixels"],
        },
        "decision": "blocked_face_skin_hull_v2_runtime_unsafe_protected_route_required",
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "generation_executed": False,
        "ec2_started": False,
        "result": "blocked_face_skin_hull_v2_runtime_unsafe_protected_route_required",
        "next_required_action": (
            "Do not run generated-output proof for this hull mask. Build a protected face-skin route that excludes eyes, eyebrows, lips/mouth, hair, and clothing while documenting any tradeoff against the current benchmark definition."
        ),
    }

    out = root / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70" / (
        f"W70_MF70_FACE_SKIN_HULL_V2_STRICT_VISUAL_REVIEW_{RUN_STAMP}.json"
    )
    tracker = root / "Plan/Tracker/Evidence" / out.name
    write_json(out, evidence)
    write_json(tracker, evidence)

    marker = evidence["evidence_id"]
    section = f"""## Wave70 mf70_face_skin Hull V2 Strict Visual Review - {TIMESTAMP}

Strict visual review blocked the benchmark-passing `mf70_face_skin` hull v2 candidate for runtime use. Evidence `{rel(out, root)}` reports `blocked_face_skin_hull_v2_runtime_unsafe_protected_route_required`: the target overlay fills eyes/eyebrows, lips/mouth, nose, and touches hair/clothing boundaries. Do not run generated-output proof for this hull mask; create a protected route instead. No active input, mask promotion, generation, EC2, AWS, GitHub, S3, Civitai, final certification, or row completion occurred.
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
