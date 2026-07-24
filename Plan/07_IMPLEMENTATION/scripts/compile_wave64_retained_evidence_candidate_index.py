#!/usr/bin/env python3
"""Index retained direct-review evidence as curator candidates without qualification claims.

The index is deliberately not a qualification corpus.  It creates a compact,
hash-bound inventory of retained PASS/REJECT evidence so a curator can build a
new, versioned calibration board without reopening held-out material or
mistaking duplicated evidence mirrors for independent examples.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_ROOTS = (
    Path("Plan/Tracker/Evidence/Wave64"),
    Path("Plan/Instructions/QA/Evidence/Wave64"),
)
DEFAULT_OUTPUT = Path(
    "Plan/Tracker/Evidence/W64_AQA_RETAINED_EVIDENCE_CANDIDATE_INDEX_20260724.json"
)
MAX_EVIDENCE_BYTES = 10 * 1024 * 1024
REVIEW_DISPOSITION_KEYS = {
    "strict_pod_llm_review",
    "semantic_review_disposition",
    "visual_review_disposition",
    "quality_review_disposition",
}
IMAGE_ARTIFACT_QA_ROOT = "Plan/Instructions/QA/Evidence/Image_Artifact_QA/"
NON_RELEASE_IMAGE_QA_NAME_TOKENS = (
    "TECHNICAL_QA",
    "CONTROL_MAP",
    "PREPROCESSOR_MAP",
)


class CandidateIndexError(ValueError):
    """Raised when the candidate index cannot remain deterministic and safe."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CandidateIndexError(f"JSON root must be an object: {path}")
    return value


def descendants(value: Any) -> Iterator[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from descendants(child)
    elif isinstance(value, list):
        for child in value:
            yield from descendants(child)


def collect_defect_codes(value: Any) -> list[str]:
    codes: set[str] = set()
    for item in descendants(value):
        if not isinstance(item, dict):
            continue
        for key in ("blocking_defects", "blocking_defect_codes", "defect_codes"):
            raw_codes = item.get(key)
            if isinstance(raw_codes, list) and all(isinstance(code, str) for code in raw_codes):
                codes.update(code.upper().replace(" ", "_") for code in raw_codes)
    return sorted(codes)


def is_image_artifact_qa_source(source: str) -> bool:
    return source.startswith(IMAGE_ARTIFACT_QA_ROOT)


def is_direct_image_artifact_review_source(source: str) -> bool:
    """Exclude technical and control-map diagnostics from release-image curation intake."""
    if not is_image_artifact_qa_source(source):
        return False
    name = Path(source).name.upper()
    return not any(token in name for token in NON_RELEASE_IMAGE_QA_NAME_TOKENS)


def infer_modality(value: Any, source: str) -> str:
    if is_image_artifact_qa_source(source):
        return "image"
    text = " ".join(item.lower() for item in descendants(value) if isinstance(item, str))
    if any(token in text for token in ("wan", "video", "motion", "frame", "temporal")):
        return "video"
    if any(token in text for token in ("audio", "speech", "voice", "wav", "phoneme")):
        return "audio"
    if any(token in text for token in ("workflow", "node", "comfyui graph")):
        return "workflow"
    if any(token in text for token in ("mask", "alpha", "segmentation")):
        return "mask"
    return "image_or_unspecified"


def image_artifact_qa_disposition(value: dict[str, Any]) -> str | None:
    """Read only document-level visual-QA decisions from the image QA evidence family."""
    values: list[str] = []
    for key in ("decision", "qa_result"):
        item = value.get(key)
        if isinstance(item, str):
            values.append(item.upper())
    portfolio = value.get("portfolio_certification_record")
    if isinstance(portfolio, dict) and isinstance(portfolio.get("decision"), str):
        values.append(portfolio["decision"].upper())
    if any(any(token in item for token in ("REJECT", "FAIL", "BLOCK")) for item in values):
        return "REJECT_EVIDENCE_CANDIDATE"
    if any(any(token in item for token in ("PASS", "CERTIFIED")) for item in values):
        return "PASS_EVIDENCE_CANDIDATE"
    return None


def direct_review_disposition(
    value: dict[str, Any], defect_codes: list[str], source: str
) -> str | None:
    """Return only an explicit review outcome; generic status prose is not evidence."""
    values: set[str] = set()
    for item in descendants(value):
        if not isinstance(item, dict):
            continue
        for key in REVIEW_DISPOSITION_KEYS:
            review = item.get(key)
            if isinstance(review, str):
                values.add(review.upper())
    if "REJECT" in values:
        return "REJECT_EVIDENCE_CANDIDATE"
    if "PASS" in values:
        return "PASS_EVIDENCE_CANDIDATE"
    if defect_codes:
        return "REJECT_EVIDENCE_CANDIDATE"
    if is_direct_image_artifact_review_source(source):
        return image_artifact_qa_disposition(value)
    return None


def safe_relative(root: Path, candidate: Path) -> str:
    resolved = candidate.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise CandidateIndexError(f"path escapes project root: {candidate}") from exc


def candidate_record(root: Path, path: Path) -> dict[str, Any] | None:
    if path.stat().st_size > MAX_EVIDENCE_BYTES:
        return None
    try:
        value = load_json(path)
    except (CandidateIndexError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    source = safe_relative(root, path)
    defect_codes = collect_defect_codes(value)
    disposition = direct_review_disposition(value, defect_codes, source)
    if disposition is None:
        return None
    digest = sha256_file(path)
    evidence_id = value.get("evidence_id") or value.get("receipt_id") or value.get("campaign_id")
    tracker_ids = []
    for key in ("tracker_id", "item_id"):
        if isinstance(value.get(key), str):
            tracker_ids.append(value[key])
    if isinstance(value.get("related_tracker_ids"), list):
        tracker_ids.extend(item for item in value["related_tracker_ids"] if isinstance(item, str))
    return {
        "candidate_id": f"W64-AQA-CANDIDATE-{digest[:16].upper()}",
        "evidence_sha256": digest,
        "source_paths": [source],
        "evidence_id": evidence_id if isinstance(evidence_id, str) else None,
        "tracker_ids": sorted(set(tracker_ids)),
        "provisional_disposition": disposition,
        "modality": infer_modality(value, source),
        "defect_codes": defect_codes,
        "requires_human_curation": True,
        "eligible_for_calibration_or_held_out_assignment": False,
        "qualification_truth_claimed": False,
        "product_acceptance_claimed": False,
    }


def compile_index(root: Path, source_roots: tuple[Path, ...]) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    scanned = 0
    for source_root in source_roots:
        absolute_root = (root / source_root).resolve()
        if not absolute_root.is_dir():
            raise CandidateIndexError(f"evidence source root is absent: {source_root}")
        for path in sorted(absolute_root.rglob("*.json")):
            scanned += 1
            record = candidate_record(root, path)
            if record is None:
                continue
            existing = grouped.get(record["evidence_sha256"])
            if existing is None:
                grouped[record["evidence_sha256"]] = record
            else:
                existing["source_paths"].extend(record["source_paths"])
                existing["source_paths"].sort()
                existing["tracker_ids"] = sorted(set(existing["tracker_ids"] + record["tracker_ids"]))
    candidates = sorted(grouped.values(), key=lambda item: (item["evidence_sha256"], item["source_paths"][0]))
    dispositions = {
        "reject_candidates": sum(item["provisional_disposition"] == "REJECT_EVIDENCE_CANDIDATE" for item in candidates),
        "pass_candidates": sum(item["provisional_disposition"] == "PASS_EVIDENCE_CANDIDATE" for item in candidates),
    }
    index = {
        "schema_version": "wave64.aqa.retained_evidence_candidate_index.v1",
        "program_id": "W64-AQA",
        "status": "RETAINED_EVIDENCE_CANDIDATES_READY_FOR_HUMAN_CURATOR_REVIEW",
        "source_roots": [path.as_posix() for path in source_roots],
        "max_evidence_bytes": MAX_EVIDENCE_BYTES,
        "scanned_json_count": scanned,
        "candidates": candidates,
        "coverage": {
            "candidate_count": len(candidates),
            **dispositions,
            "modalities": sorted({item["modality"] for item in candidates}),
            "defect_codes": sorted({code for item in candidates for code in item["defect_codes"]}),
        },
        "curation_rules": [
            "A curator must assign every selected candidate to exactly one frozen calibration or held-out partition.",
            "Duplicate evidence hashes are one candidate regardless of mirrored paths.",
            "No candidate is qualification truth, a role certificate, or product acceptance without a separate governed decision.",
        ],
        "authority": {
            "retained_evidence_inventory": True,
            "runtime_qualification": False,
            "quality_qualification": False,
            "role_certification": False,
            "product_acceptance": False,
            "promotion": False,
        },
        "index_sha256": "0" * 64,
    }
    index["index_sha256"] = hashlib.sha256(canonical_bytes(index)).hexdigest()
    return index


def validate_index(root: Path, path: Path, source_roots: tuple[Path, ...]) -> None:
    actual = load_json(path)
    expected = compile_index(root, source_roots)
    if actual != expected:
        raise CandidateIndexError("candidate index does not replay from current retained evidence")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--source-root", type=Path, action="append")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    source_roots = tuple(args.source_root) if args.source_root else DEFAULT_SOURCE_ROOTS
    if args.validate:
        validate_index(root, args.validate, source_roots)
        print(json.dumps({"status": "PASS", "index": str(args.validate)}))
        return 0
    index = compile_index(root, source_roots)
    output = args.output or root / DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "index": str(output), "candidate_count": len(index["candidates"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
