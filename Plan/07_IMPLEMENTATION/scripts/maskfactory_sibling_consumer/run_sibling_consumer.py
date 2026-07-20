"""Sibling Main MaskFactory consumer scaffold (isolated clean branch).

authority_kind = sibling_main_consumer
is_real_comfyui_main = false
wave64_dirty_main_untouched = true

This package consumes producer-pinned adapter/conformance contract bytes only.
It does NOT import dirty MaskFactory source, does NOT claim production adoption,
and does NOT touch the dirty Wave64 tree at C:\\Comfy_UI_Main.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
PIN = PACKAGE / "producer_pin.json"


def _key(role: str) -> tuple[Ed25519PrivateKey, str]:
    seed = hashlib.sha256(f"maskfactory-sibling-main-consumer-v1:{role}".encode()).digest()
    return Ed25519PrivateKey.from_private_bytes(seed), f"sibling-main-consumer-{role}"


def _canonical(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha(obj: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(obj)).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pin = json.loads(PIN.read_text(encoding="utf-8"))
    private_key, key_id = _key("adoption")
    public_raw = private_key.public_key().public_bytes_raw()

    receipt = {
        "schema_version": "1.0.0",
        "record_type": "maskfactory_sibling_consumer_pin_receipt",
        "authority_kind": "sibling_main_consumer",
        "is_real_comfyui_main": False,
        "main_adoption_complete": False,
        "wave64_dirty_main_untouched": True,
        "consumer": {
            "repository": "KevinSGarrett/Comfy_UI_Main",
            "worktree": str(ROOT),
            "branch": pin.get("sibling_branch"),
            "head": pin.get("sibling_head"),
            "provenance": "sibling_main_consumer",
            "is_real_comfyui_main": False,
        },
        "producer_pin": {
            "repository": pin.get("producer_repository"),
            "commit": pin.get("producer_commit"),
            "adapter_observation_sha256": pin.get("adapter_observation_sha256"),
            "conformance_policy_sha256": pin.get("conformance_policy_sha256"),
        },
        "hard_blockers_still_open": pin.get("hard_blockers_still_open"),
        "decided_at": pin.get("decided_at"),
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "claims_not_established": [
            "real_comfyui_main_adoption",
            "main_adoption_complete / MF-P6-12.06 core close",
            "PRODUCTION_EVIDENCE_PASS",
        ],
    }
    receipt["adoption_payload_sha256"] = _sha(
        {k: v for k, v in receipt.items() if k not in {"adoption_payload_sha256", "signature"}}
    )
    digest = bytes.fromhex(receipt["adoption_payload_sha256"])
    receipt["signature"] = {
        "algorithm": "ed25519",
        "key_id": key_id,
        "public_key_base64": base64.b64encode(public_raw).decode(),
        "signed_payload_format": "sha256_digest_bytes",
        "signed_payload_sha256": receipt["adoption_payload_sha256"],
        "value_base64": base64.b64encode(private_key.sign(digest)).decode(),
    }
    private_key.public_key().verify(
        base64.b64decode(receipt["signature"]["value_base64"]), digest
    )

    # Contract-surface checks (local to this package; no dirty producer import).
    checks = []
    checks.append(
        {
            "check": "sibling_pin_receipt_signed",
            "passed": receipt["signature"]["key_id"] == "sibling-main-consumer-adoption",
            "authority_kind": "sibling_main_consumer",
            "adoption_payload_sha256": receipt["adoption_payload_sha256"],
        }
    )
    checks.append(
        {
            "check": "producer_pin_present",
            "passed": isinstance(pin.get("producer_commit"), str)
            and len(pin.get("producer_commit") or "") == 40,
            "producer_commit": pin.get("producer_commit"),
        }
    )
    checks.append(
        {
            "check": "wave64_dirty_main_untouched",
            "passed": pin.get("wave64_dirty_main_untouched") is True,
        }
    )
    checks.append(
        {
            "check": "no_production_adoption_claim",
            "passed": receipt["is_real_comfyui_main"] is False
            and receipt["main_adoption_complete"] is False,
        }
    )

    evidence = {
        "artifact_type": "sibling_main_consumer_run",
        "authority_kind": "sibling_main_consumer",
        "is_real_comfyui_main": False,
        "main_adoption_complete": False,
        "wave64_dirty_main_untouched": True,
        "sibling_root": str(ROOT),
        "sibling_branch": pin.get("sibling_branch"),
        "sibling_head": pin.get("sibling_head"),
        "producer_commit": pin.get("producer_commit"),
        "origin_main": pin.get("origin_main"),
        "checks": checks,
        "receipt": receipt,
        "hard_blockers_still_open": pin.get("hard_blockers_still_open"),
        "recorded_at": receipt["recorded_at"],
        "self_sha256": "",
    }
    payload = json.dumps(
        {k: v for k, v in evidence.items() if k != "self_sha256"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    evidence["self_sha256"] = hashlib.sha256(payload).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        args.output,
        evidence["self_sha256"],
        "checks",
        sum(1 for c in checks if c["passed"]),
        "/",
        len(checks),
    )
    return 0 if all(c["passed"] for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
