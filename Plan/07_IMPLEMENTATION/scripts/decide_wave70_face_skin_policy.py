from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_FACE_SKIN_POLICY_DECISION_{RUN_STAMP}"

SOURCES = {
    "combined_gold_gate_decision": "W70_FACIAL_COMBINED_GOLD_GATE_DECISION_*.json",
    "lapa_gold_benchmark_gate": "W70_FACIAL_LAPA_GOLD_BENCHMARK_GATE_*.json",
    "combined_gold_postprocess_route_eval": "W70_COMBINED_GOLD_POSTPROCESS_ROUTE_EVAL_*.json",
    "face_skin_hull_v2_strict_visual_review": "W70_MF70_FACE_SKIN_HULL_V2_STRICT_VISUAL_REVIEW_*.json",
    "face_skin_protected_v3": "W70_MF70_FACE_SKIN_PROTECTED_V3_*.json",
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest(pattern: str) -> Path:
    matches = sorted(QA_DIR.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No evidence found for {pattern}")
    return matches[0]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_record(name: str, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "path": rel(path),
        "sha256": sha256(path),
        "result": payload.get("result"),
    }


def combined_region_record(payload: dict[str, Any], region: str) -> dict[str, Any] | None:
    for record in payload.get("region_decisions", []):
        if record.get("region") == region:
            return record
    return None


def lapa_region_record(payload: dict[str, Any], region: str) -> dict[str, Any] | None:
    for record in payload.get("region_gate_records", []):
        if record.get("region") == region or record.get("mask_type_id") == region:
            return record
    return None


def postprocess_region_record(payload: dict[str, Any], region: str) -> dict[str, Any] | None:
    for record in payload.get("region_route_records", []):
        if record.get("region") == region:
            return record
    return None


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)

    source_paths = {name: latest(pattern) for name, pattern in SOURCES.items()}
    sources = {name: load_json(path) for name, path in source_paths.items()}

    combined = combined_region_record(sources["combined_gold_gate_decision"], "mf70_face_skin")
    lapa = lapa_region_record(sources["lapa_gold_benchmark_gate"], "mf70_face_skin")
    postprocess = postprocess_region_record(sources["combined_gold_postprocess_route_eval"], "mf70_face_skin")
    hull_review = sources["face_skin_hull_v2_strict_visual_review"]
    protected = sources["face_skin_protected_v3"]
    if combined is None:
        raise RuntimeError("Combined gold gate has no mf70_face_skin record")
    if lapa is None:
        raise RuntimeError("LaPa gate has no mf70_face_skin record")
    if postprocess is None:
        raise RuntimeError("Postprocess eval has no mf70_face_skin record")

    combined_all_gold_pass = not combined.get("blocked_by")
    lapa_pass = bool(lapa.get("lapa_gold_benchmark_gate_pass"))
    postprocess_pass = bool(postprocess.get("best_pass_gate"))
    hull_benchmark_pass = bool(hull_review.get("strict_review", {}).get("benchmark_route_passed"))
    hull_runtime_safe = bool(hull_review.get("strict_review", {}).get("target_runtime_safe"))
    protected_gold_pass = bool(protected.get("protected_route_gold_benchmark_tradeoff", {}).get("passes_current_gold_gate"))
    promotion_ready = combined_all_gold_pass and hull_runtime_safe and protected_gold_pass

    policy_options = [
        {
            "policy": "promote_current_combined_gold_face_skin_route",
            "decision": "rejected",
            "reason": "Combined gold gate blocks mf70_face_skin because CelebAMask-HQ fails even though LaPa passes.",
        },
        {
            "policy": "promote_benchmark_valid_hull_v2_runtime_mask",
            "decision": "rejected",
            "reason": "Hull v2 is benchmark-valid but strict visual review marks it runtime-unsafe over identity-critical facial features.",
        },
        {
            "policy": "promote_protected_v3_runtime_mask",
            "decision": "rejected",
            "reason": "Protected v3 is safer for runtime but fails the current gold benchmark tradeoff.",
        },
        {
            "policy": "fail_closed_until_dataset_vs_runtime_face_skin_policy_or_safer_gold_supported_route",
            "decision": "selected",
            "reason": (
                "Face skin has a dataset/runtime policy conflict: semantic skin benchmarks and runtime-safe protected masks optimize different surfaces. "
                "Promotion requires an explicit policy split or a safer route that passes gold and protected-feature review."
            ),
        },
    ]

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "Wave70 mf70_face_skin dataset-vs-runtime policy decision from current combined gold and target-source safety evidence",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "region": "mf70_face_skin",
        "gold_mask_authority": {
            "masked_warehouse": str(PROJECT_ROOT / "MaskedWarehouse"),
            "primary_datasets": ["CelebAMask-HQ", "LaPa"],
            "single_generated_portrait_is_pass_authority": False,
        },
        "source_evidence": [
            source_record(name, path, sources[name])
            for name, path in source_paths.items()
        ],
        "combined_gold_face_skin_record": combined,
        "lapa_face_skin_gate_record": lapa,
        "combined_gold_postprocess_record": postprocess,
        "hull_v2_strict_visual_review": {
            "decision": hull_review.get("decision"),
            "result": hull_review.get("result"),
            "route_gold_benchmark_summary": hull_review.get("route_gold_benchmark_summary"),
            "strict_review": hull_review.get("strict_review"),
            "visual_findings": hull_review.get("visual_findings"),
        },
        "protected_v3_tradeoff": protected.get("protected_route_gold_benchmark_tradeoff"),
        "combined_all_gold_policy_pass": combined_all_gold_pass,
        "lapa_face_skin_policy_pass": lapa_pass,
        "combined_gold_postprocess_policy_pass": postprocess_pass,
        "hull_v2_benchmark_policy_pass": hull_benchmark_pass,
        "hull_v2_runtime_safe": hull_runtime_safe,
        "protected_v3_gold_policy_pass": protected_gold_pass,
        "current_face_skin_promotion_ready": promotion_ready,
        "policy_options": policy_options,
        "selected_policy": "fail_closed_until_dataset_vs_runtime_face_skin_policy_or_safer_gold_supported_route",
        "result": "mf70_face_skin_policy_fail_closed_no_promotion",
        "decision": (
            "Do not promote or target-proof mf70_face_skin from the current combined-gold route, hull v2, or protected v3 candidate. "
            "Resume only after an explicit dataset-vs-runtime face-skin policy is selected, or after a safer route passes both gold support and protected-feature runtime review."
        ),
        "next_required_action": (
            "Switch to another local gold-backed row or define a face-skin dataset-vs-runtime policy / safer gold-supported protected route before any new face-skin proof."
        ),
    }

    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / evidence_path.name
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(
        json.dumps(
            {
                "evidence": rel(evidence_path),
                "tracker": rel(tracker_path),
                "result": evidence["result"],
                "selected_policy": evidence["selected_policy"],
                "combined_all_gold_policy_pass": combined_all_gold_pass,
                "lapa_face_skin_policy_pass": lapa_pass,
                "hull_v2_runtime_safe": hull_runtime_safe,
                "protected_v3_gold_policy_pass": protected_gold_pass,
                "current_face_skin_promotion_ready": promotion_ready,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
