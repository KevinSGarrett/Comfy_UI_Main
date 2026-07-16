#!/usr/bin/env python3
"""Fail-closed atomic promotion, revocation, and rollback control for Wave64 speech."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


class PromotionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromotionError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise PromotionError(f"JSON root must be an object: {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _value(record: dict[str, Any], dotted: str) -> Any:
    value: Any = record
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdefABCDEF" for character in value)


def validate_promotion_request(request: dict[str, Any], verify_artifact: bool = True) -> list[str]:
    """Return stable blocker labels. An empty list is the only eligible state."""

    blockers: list[str] = []
    for field in ("candidate_id", "character_version"):
        if not str(request.get(field, "")).strip():
            blockers.append(f"missing_{field}")
    artifact = request.get("artifact")
    if not isinstance(artifact, dict):
        blockers.append("missing_artifact_binding")
    else:
        if not str(artifact.get("path", "")).strip():
            blockers.append("missing_artifact_path")
        if not _hash(artifact.get("sha256")):
            blockers.append("missing_artifact_sha256")
        if not isinstance(artifact.get("bytes"), int) or artifact.get("bytes", 0) <= 0:
            blockers.append("missing_artifact_bytes")
        if verify_artifact and not any(item.startswith("missing_artifact_") for item in blockers):
            path = Path(artifact["path"]).resolve()
            if not path.is_file():
                blockers.append("artifact_file_missing")
            else:
                if path.stat().st_size != artifact["bytes"]:
                    blockers.append("artifact_bytes_mismatch")
                if sha256_file(path) != artifact["sha256"].lower():
                    blockers.append("artifact_sha256_mismatch")

    required_text = (
        "authority.identity_policy",
        "authority.reference_id",
        "authority.model_id",
        "authority.approved_use",
        "rollback.action",
    )
    for field in required_text:
        if not str(_value(request, field) or "").strip():
            blockers.append(f"missing_{field.replace('.', '_')}")

    required_hashes = (
        "authority.reference_sha256",
        "evaluation.record_sha256",
        "review.playback_record_sha256",
        "review.production_record_sha256",
        "review.artifact_sha256",
    )
    for field in required_hashes:
        if not _hash(_value(request, field)):
            blockers.append(f"missing_{field.replace('.', '_')}")

    required_true = (
        "authority.rights_valid",
        "authority.production_authorized",
        "evaluation.hard_gates_pass",
        "evaluation.ranking_complete",
        "review.playback_review_pass",
        "review.final_production_authority_pass",
        "review.roles_are_distinct",
    )
    for field in required_true:
        if _value(request, field) is not True:
            blockers.append(f"{field.replace('.', '_')}_not_passed")

    required_false = (
        "authority.reference_revoked",
        "authority.model_revoked",
        "content_based_suppression",
    )
    for field in required_false:
        if _value(request, field) is not False:
            blockers.append(f"{field.replace('.', '_')}_not_false")

    artifact_hash = _value(request, "artifact.sha256")
    review_hash = _value(request, "review.artifact_sha256")
    if _hash(artifact_hash) and _hash(review_hash) and artifact_hash.lower() != review_hash.lower():
        blockers.append("review_artifact_sha256_mismatch")
    return sorted(set(blockers))


def canonical_promotion_id(request: dict[str, Any]) -> str:
    material = {
        "candidate_id": request.get("candidate_id"),
        "character_version": request.get("character_version"),
        "artifact_sha256": _value(request, "artifact.sha256"),
        "reference_sha256": _value(request, "authority.reference_sha256"),
        "evaluation_sha256": _value(request, "evaluation.record_sha256"),
        "playback_sha256": _value(request, "review.playback_record_sha256"),
        "production_sha256": _value(request, "review.production_record_sha256"),
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("ascii")
    return f"W64-SP-{hashlib.sha256(encoded).hexdigest()[:24]}"


class PromotionLedger:
    def __init__(self, state_path: Path):
        self.state_path = state_path.resolve()

    def load(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            return {
                "schema_version": "1.0",
                "active": {},
                "history": [],
                "revoked_reference_ids": [],
                "revoked_model_ids": [],
            }
        value = load_object(self.state_path)
        if not isinstance(value.get("active"), dict) or not isinstance(value.get("history"), list):
            raise PromotionError("promotion ledger shape is invalid")
        value.setdefault("revoked_reference_ids", [])
        value.setdefault("revoked_model_ids", [])
        return value

    def promote(self, request: dict[str, Any]) -> dict[str, Any]:
        blockers = validate_promotion_request(request)
        state = self.load()
        if _value(request, "authority.reference_id") in set(state["revoked_reference_ids"]):
            blockers.append("authority_reference_revoked_by_ledger")
        if _value(request, "authority.model_id") in set(state["revoked_model_ids"]):
            blockers.append("authority_model_revoked_by_ledger")
        blockers = sorted(set(blockers))
        if blockers:
            return {
                "status": "BLOCKED",
                "decision": "refused",
                "candidate_id": request.get("candidate_id"),
                "artifact_sha256": _value(request, "artifact.sha256"),
                "blockers": blockers,
                "ledger_mutated": False,
            }
        candidate_id = str(request["candidate_id"])
        promotion_id = canonical_promotion_id(request)
        existing = state["active"].get(candidate_id)
        if existing:
            if existing.get("promotion_id") == promotion_id and existing.get("status") == "active":
                return {
                    "status": "PASS",
                    "decision": "promoted",
                    "candidate_id": candidate_id,
                    "promotion_id": promotion_id,
                    "idempotent_replay": True,
                    "ledger_mutated": False,
                }
            raise PromotionError(f"active promotion hash conflict for candidate: {candidate_id}")
        record = {
            "schema_version": "1.0",
            "promotion_id": promotion_id,
            "candidate_id": candidate_id,
            "artifact_sha256": request["artifact"]["sha256"].lower(),
            "character_version": request["character_version"],
            "authority_bindings": [request["authority"]],
            "evaluation_bindings": [request["evaluation"]],
            "review_bindings": [request["review"]],
            "rollback": request["rollback"],
            "decision": "promoted",
            "status": "active",
            "source_request": request,
        }
        state["active"][candidate_id] = record
        state["history"].append({"event": "promoted", "promotion_id": promotion_id, "candidate_id": candidate_id})
        write_json_atomic(self.state_path, state)
        return {
            "status": "PASS",
            "decision": "promoted",
            "candidate_id": candidate_id,
            "promotion_id": promotion_id,
            "idempotent_replay": False,
            "ledger_mutated": True,
        }

    def revoke(self, reference_ids: set[str] | None = None, model_ids: set[str] | None = None) -> list[str]:
        reference_ids = reference_ids or set()
        model_ids = model_ids or set()
        state = self.load()
        state["revoked_reference_ids"] = sorted(set(state["revoked_reference_ids"]) | reference_ids)
        state["revoked_model_ids"] = sorted(set(state["revoked_model_ids"]) | model_ids)
        invalidated: list[str] = []
        for candidate_id, record in list(state["active"].items()):
            authority = _value(record, "source_request.authority") or {}
            if authority.get("reference_id") not in reference_ids and authority.get("model_id") not in model_ids:
                continue
            record["status"] = "revoked"
            record["decision"] = "revoked"
            state["history"].append({
                "event": "revoked",
                "promotion_id": record["promotion_id"],
                "candidate_id": candidate_id,
                "record": record,
            })
            del state["active"][candidate_id]
            invalidated.append(candidate_id)
        if reference_ids or model_ids:
            write_json_atomic(self.state_path, state)
        return sorted(invalidated)

    def rollback(self, candidate_id: str) -> dict[str, Any]:
        state = self.load()
        record = state["active"].get(candidate_id)
        if not record:
            if any(item.get("event") == "rolled_back" and item.get("candidate_id") == candidate_id for item in state["history"]):
                return {"candidate_id": candidate_id, "decision": "rolled_back", "idempotent_replay": True}
            raise PromotionError(f"promotion is not active: {candidate_id}")
        record["status"] = "rolled_back"
        record["decision"] = "rolled_back"
        state["history"].append({
            "event": "rolled_back",
            "promotion_id": record["promotion_id"],
            "candidate_id": candidate_id,
            "record": record,
        })
        del state["active"][candidate_id]
        write_json_atomic(self.state_path, state)
        return {"candidate_id": candidate_id, "decision": "rolled_back", "idempotent_replay": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--evaluate-only", action="store_true")
    args = parser.parse_args()
    request = load_object(args.request.resolve())
    if args.evaluate_only:
        blockers = validate_promotion_request(request)
        print(json.dumps({"eligible": not blockers, "blockers": blockers}, indent=2))
        return 0 if not blockers else 3
    if args.state is None:
        parser.error("--state is required unless --evaluate-only is used")
    result = PromotionLedger(args.state).promote(request)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
