#!/usr/bin/env python3
"""Fail-closed Wave64 Row104 generated-asset promotion and revocation slice."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/generated_asset_promotion_decision.schema.json")
POLICY_PATH = Path("Plan/10_REGISTRIES/wave64_row104_generated_asset_promotion_policy_registry.json")
DEFAULT_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-104_generated_asset_promotion.json")
EVALUATOR_REVISION = "wave64_row104_generated_asset_promotion_evaluator_v0.1.0"
POLICY_REVISION = "wave64_row104_generated_asset_promotion_policy_v0.1.0"
TRACKER_ID = "TRK-W64-104"
ITEM_ID = "ITEM-W64-104"
SCHEMA_VERSION = "1.0.0"
REQUIRED_GATES = (
    "promotion_authority",
    "registry_ingestion",
    "selector_visibility",
    "origin_preserved",
    "rights",
    "dedup",
    "revocation",
)
DEPENDENCY_DELTAS = {
    "TRK-W64-080": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-080_HYBRID_AUDIO_RETRIEVAL_INDEX_CURRENT_DELTA_20260719.json"),
    "TRK-W64-102": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-102_GENERATED_ASSET_PROVENANCE_CURRENT_DELTA_20260719.json"),
    "TRK-W64-103": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-103_GENERATED_SOUND_QA_CURRENT_DELTA_20260719.json"),
}


class GeneratedAssetPromotionError(ValueError):
    """Raised when Row104 authority or record semantics fail closed."""


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row104_fixture:{label}".encode())


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise GeneratedAssetPromotionError(f"{label}_outside_project_root") from exc
    return path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_policy(root: Path) -> dict[str, Any]:
    policy = load_json(resolve_under(root, POLICY_PATH, "policy"))
    if policy.get("revision") != POLICY_REVISION:
        raise GeneratedAssetPromotionError("policy_revision_mismatch")
    if tuple(policy.get("required_gates") or ()) != REQUIRED_GATES:
        raise GeneratedAssetPromotionError("policy_required_gates_mismatch")
    return policy


def evaluate_dependency_admissions(root: Path) -> dict[str, dict[str, Any]]:
    admissions: dict[str, dict[str, Any]] = {}
    for tracker_id, relative in DEPENDENCY_DELTAS.items():
        path = resolve_under(root, relative, tracker_id.lower())
        if not path.is_file():
            admissions[tracker_id] = {
                "tracker_id": tracker_id,
                "evidence_path": relative.as_posix(),
                "evidence_sha256": "0" * 64,
                "row_complete": False,
                "dependency_satisfied": False,
                "blocker_codes": [f"{tracker_id.replace('-', '_')}_DELTA_ABSENT"],
            }
            continue
        payload = load_json(path)
        complete = payload.get("row_complete") is True
        admissions[tracker_id] = {
            "tracker_id": tracker_id,
            "evidence_path": relative.as_posix(),
            "evidence_sha256": sha256_file(path),
            "row_complete": complete,
            "dependency_satisfied": complete,
            "blocker_codes": [] if complete else [f"{tracker_id.replace('-', '_')}_NOT_ACCEPTED"],
        }
    return admissions


def seal_record(record: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(record)
    sealed["receipt_sha256"] = sha256_bytes(canonical_json_bytes(record))
    return sealed


def validate_semantics(record: dict[str, Any]) -> None:
    decision = record["decision"]
    dependencies_pass = all(item["dependency_satisfied"] for item in record["dependency_admissions"].values())
    gates_pass = (
        dependencies_pass
        and record["provenance"]["accepted"]
        and record["qa"]["accepted"]
        and record["rights"]["output_use"] == "allowed"
        and bool(record["rights"]["license_id"])
        and not record["dedup"]["exact_duplicate"]
        and (not record["dedup"]["near_duplicate"] or bool(record["dedup"]["justified_role"]))
        and record["revocation"]["status"] == "active"
    )
    if record["is_synthetic"] and (record["library"]["selector_visible"] or decision["promotion_authority"]):
        raise GeneratedAssetPromotionError("synthetic_fixture_cannot_gain_library_authority")
    if decision["route"] == "promote" and not gates_pass:
        raise GeneratedAssetPromotionError("failed_gate_cannot_promote")
    if record["library"]["selector_visible"] and not decision["promotion_authority"]:
        raise GeneratedAssetPromotionError("selector_visibility_without_promotion_authority")
    if record["revocation"]["status"] == "revoked":
        if record["library"]["selector_visible"]:
            raise GeneratedAssetPromotionError("revoked_asset_selector_visible")
        if not record["revocation"]["reason"] or not record["revocation"]["receipt_sha256"]:
            raise GeneratedAssetPromotionError("revocation_receipt_required")
    expected = sha256_bytes(canonical_json_bytes({k: v for k, v in record.items() if k != "receipt_sha256"}))
    if record["receipt_sha256"] != expected:
        raise GeneratedAssetPromotionError("receipt_sha256_mismatch")


def validate_record(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    Draft202012Validator(schema).validate(record)
    validate_semantics(record)


def base_packet(name: str, **overrides: Any) -> dict[str, Any]:
    packet = {
        "candidate_id": f"cand_{name}",
        "candidate_pcm_sha256": stable_hash(f"pcm:{name}"),
        "canonical_tags": ["foley", "footstep.wood", "generated"],
        "engine_revision": "fixture_engine_v1",
        "generation_receipt_sha256": stable_hash(f"generation:{name}"),
        "provenance_bundle_sha256": stable_hash(f"provenance:{name}"),
        "provenance_accepted": True,
        "qa_bundle_sha256": stable_hash(f"qa:{name}"),
        "qa_accepted": True,
        "rights_decision_sha256": stable_hash(f"rights:{name}"),
        "output_use": "allowed",
        "license_id": "CC0-1.0",
        "attribution": "fixture generator",
        "exact_duplicate": False,
        "near_duplicate": False,
        "justified_role": None,
    }
    packet.update(overrides)
    return packet


def fixture_packet(name: str) -> dict[str, Any]:
    if name == "synthetic_promotable_fixture":
        return base_packet(name)
    if name == "missing_rights_rejected":
        return base_packet(name, output_use="unknown", license_id="")
    if name == "qa_not_accepted_rejected":
        return base_packet(name, qa_accepted=False)
    if name == "exact_duplicate_rejected":
        return base_packet(name, exact_duplicate=True)
    if name == "near_duplicate_justified_fixture":
        return base_packet(name, near_duplicate=True, justified_role="distinct close-mic material layer")
    raise GeneratedAssetPromotionError(f"unknown_fixture:{name}")


def build_record(
    root: Path,
    *,
    packet: dict[str, Any],
    is_synthetic: bool,
    dependency_admissions: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    policy_path = resolve_under(root, POLICY_PATH, "policy")
    load_policy(root)
    admissions = dependency_admissions or evaluate_dependency_admissions(root)
    blockers: list[str] = []
    dependency_blocked = not all(item["dependency_satisfied"] for item in admissions.values())
    if dependency_blocked:
        blockers.append("ROW104_DEPENDENCIES_NOT_ACCEPTED")
    candidate_blockers: list[str] = []
    if not packet["provenance_accepted"]:
        candidate_blockers.append("PROVENANCE_NOT_ACCEPTED")
    if not packet["qa_accepted"]:
        candidate_blockers.append("QA_NOT_ACCEPTED")
    if packet["output_use"] != "allowed" or not packet["license_id"]:
        candidate_blockers.append("RIGHTS_NOT_ACCEPTED")
    if packet["exact_duplicate"]:
        candidate_blockers.append("EXACT_DUPLICATE")
    if packet["near_duplicate"] and not packet["justified_role"]:
        candidate_blockers.append("NEAR_DUPLICATE_UNJUSTIFIED")
    blockers.extend(candidate_blockers)

    if is_synthetic and not blockers:
        route, status, acceptance = "fixture_promotable", "pass", "fixture_only"
    elif candidate_blockers:
        route, status, acceptance = "reject", "fail", "fixture_only" if is_synthetic else "held"
    elif dependency_blocked:
        route, status, acceptance = "hold", "blocked", "held"
    else:
        route, status, acceptance = "promote", "pass", "accepted"
    promotion_authority = route == "promote" and not is_synthetic
    selector_visible = promotion_authority
    digest = packet["candidate_pcm_sha256"]
    record = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "generated_asset_promotion_decision",
        "evaluator_revision": EVALUATOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": sha256_file(policy_path),
        "candidate_id": packet["candidate_id"],
        "candidate_pcm_sha256": digest,
        "is_synthetic": is_synthetic,
        "dependency_admissions": admissions,
        "required_gates": list(REQUIRED_GATES),
        "canonical_tags": sorted(set(packet["canonical_tags"])),
        "origin": {"type": "generated", "engine_revision": packet["engine_revision"], "generation_receipt_sha256": packet["generation_receipt_sha256"]},
        "provenance": {"bundle_sha256": packet["provenance_bundle_sha256"], "accepted": packet["provenance_accepted"]},
        "qa": {"bundle_sha256": packet["qa_bundle_sha256"], "accepted": packet["qa_accepted"]},
        "rights": {"decision_sha256": packet["rights_decision_sha256"], "output_use": packet["output_use"], "license_id": packet["license_id"], "attribution": packet["attribution"]},
        "dedup": {"exact_duplicate": packet["exact_duplicate"], "near_duplicate": packet["near_duplicate"], "justified_role": packet["justified_role"]},
        "library": {"asset_id": f"generated:{digest}", "version": 1, "object_path": f"generated/{digest}/v1/asset.wav", "selector_visible": selector_visible, "generated_origin_preserved": True, "evidence_retained": True},
        "revocation": {"status": "active", "reason": None, "receipt_sha256": None},
        "decision": {"route": route, "status": status, "blocker_codes": sorted(set(blockers)), "row104_acceptance": acceptance, "product_completion": False, "promotion_authority": promotion_authority},
    }
    sealed = seal_record(record)
    validate_record(root, sealed)
    return sealed


def revoke_record(root: Path, record: dict[str, Any], *, reason: str, receipt_sha256: str) -> dict[str, Any]:
    revoked = deepcopy(record)
    revoked["library"]["selector_visible"] = False
    revoked["revocation"] = {"status": "revoked", "reason": reason, "receipt_sha256": receipt_sha256}
    revoked["decision"] = {"route": "revoke", "status": "pass", "blocker_codes": ["ASSET_REVOKED"], "row104_acceptance": "held", "product_completion": False, "promotion_authority": False}
    revoked.pop("receipt_sha256", None)
    sealed = seal_record(revoked)
    validate_record(root, sealed)
    return sealed


FIXTURES = (
    "synthetic_promotable_fixture",
    "missing_rights_rejected",
    "qa_not_accepted_rejected",
    "exact_duplicate_rejected",
    "near_duplicate_justified_fixture",
)


def fixture_record(root: Path, name: str) -> dict[str, Any]:
    accepted_dependencies = {
        tracker_id: {
            "tracker_id": tracker_id,
            "evidence_path": path.as_posix(),
            "evidence_sha256": stable_hash(f"accepted:{tracker_id}"),
            "row_complete": True,
            "dependency_satisfied": True,
            "blocker_codes": [],
        }
        for tracker_id, path in DEPENDENCY_DELTAS.items()
    }
    return build_record(root, packet=fixture_packet(name), is_synthetic=True, dependency_admissions=accepted_dependencies)


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_dependency_admissions(root)
    records = [fixture_record(root, name) for name in FIXTURES]
    blockers = [code for item in admissions.values() for code in item["blocker_codes"]]
    blockers.extend(["ROW104_DEPENDENCIES_NOT_ACCEPTED", "GENUINE_GENERATED_ASSET_PROMOTION_RUNTIME_ABSENT"])
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-104_generated_asset_promotion",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "evaluator_revision": EVALUATOR_REVISION,
        "policy_revision": POLICY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_DEPENDENCIES_AND_GENERATED_ASSET_PROMOTION_RUNTIME_ABSENT",
        "dependency_admissions": admissions,
        "required_gates": list(REQUIRED_GATES),
        "fixture_calibration": {"authority": "synthetic_non_library", "fixture_count": len(records), "records": records},
        "blocker_codes": sorted(set(blockers)),
        "decision": {"status": "blocked", "row104_acceptance": "held", "product_completion": False, "safe_next_action": "Accept Rows080, 102, and 103; bind a genuine generated candidate with exact rights, provenance, QA, dedup, and no-clobber publication receipts; prove selector discovery and revocation removal while retaining immutable evidence."},
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise GeneratedAssetPromotionError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    payload = build_library_blocker_packet(root)
    if payload["decision"]["status"] != "blocked":
        raise GeneratedAssetPromotionError("library_mode_must_remain_fail_closed")
    write_json(output, payload)
    print(json.dumps({"output": str(output), "status": payload["status"], "row_complete": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
