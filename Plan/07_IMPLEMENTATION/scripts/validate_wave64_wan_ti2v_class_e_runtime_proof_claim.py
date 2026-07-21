#!/usr/bin/env python3
"""Fail closed: Wan TI2V Class E 'runtime proof success' is not smoke emission.

Smoke/canary generation receipts (Comfy completed + tiny mp4 exists) are allowed
only when claimed as smoke_emission. Success-sounding Class E proof language
requires non-degenerate media plus an explicit visual/VLM review gate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Comfy_UI_Main")

# Absolute floor for a non-empty H.264 decode of ~2s 480x640. Below this is junk/empty.
ABSOLUTE_MIN_BYTES = 16_384
# Class E "proof success" must not be claimed for the project smoke-size band (~90KB).
CLASS_E_PROOF_MIN_BYTES = 250_000

PROOF_SUCCESS_STATUS_RE = re.compile(
    r"(Runtime_Proof_Landed|CLASS_E_RUNTIME_PROOF|RUNTIME_PROOF_LANDED|"
    r"WAN_TI2V_BOUNDED_RUNTIME_GENERATION_PROOF)",
    re.IGNORECASE,
)
SMOKE_OK_STATUS_RE = re.compile(
    r"(Runtime_Smoke_Emitted|smoke_emission|SMOKE_EMISSION)",
    re.IGNORECASE,
)
# Honest Class E attempt FAIL/REJECT (bytes/VLM gate miss) — not proof success, not smoke.
FAIL_OK_STATUS_RE = re.compile(
    r"(Proof_Attempt_FAIL|PROOF_ATTEMPT_FAIL|class_e_attempt_fail|"
    r"Class_E_Proof_Attempt_FAIL|FAIL_REJECT)",
    re.IGNORECASE,
)
FAIL_CLAIM_TIERS = frozenset({"class_e_attempt_fail", "proof_attempt_fail"})


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _as_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an int")
    return value


def _claim_language_blob(packet: dict[str, Any]) -> str:
    """Only authoritative claim fields — not narrative that may mention retracted language."""
    parts = [
        str(packet.get("status", "")),
        str(packet.get("verdict", "")),
        str(packet.get("proof_tier", "")),
        str(packet.get("highest_proof_tier_achieved", "")),
        str(packet.get("claim_tier", "")),
        str(packet.get("status_decision", "")),
    ]
    return " | ".join(parts)


def evaluate_claim(packet: dict[str, Any], *, artifact_bytes: int | None = None) -> dict[str, Any]:
    generation = packet.get("generation") or {}
    artifact = generation.get("artifact") if isinstance(generation, dict) else None
    if not isinstance(artifact, dict):
        artifact = packet.get("artifact") if isinstance(packet.get("artifact"), dict) else {}

    bytes_value = artifact_bytes
    if bytes_value is None:
        raw = artifact.get("bytes") if isinstance(artifact, dict) else None
        if raw is None and isinstance(packet.get("artifact_bytes"), int):
            raw = packet["artifact_bytes"]
        bytes_value = _as_int(raw, "artifact.bytes") if raw is not None else None

    vlm = packet.get("vlm_review") if isinstance(packet.get("vlm_review"), dict) else {}
    visual = packet.get("visual_qa") if isinstance(packet.get("visual_qa"), dict) else {}
    visual_performed = bool(vlm.get("performed")) or bool(visual.get("performed"))
    visual_pass = bool(vlm.get("pass")) or bool(visual.get("pass")) or (
        str(visual.get("result", "")).lower() in {"pass", "passed", "ok"}
    )

    claim_tier = str(packet.get("claim_tier") or "").strip().lower()
    blob = _claim_language_blob(packet)
    uses_proof_success_language = bool(PROOF_SUCCESS_STATUS_RE.search(blob))
    uses_smoke_language = bool(SMOKE_OK_STATUS_RE.search(blob)) or claim_tier == "smoke_emission"
    uses_fail_language = (
        bool(FAIL_OK_STATUS_RE.search(blob)) or claim_tier in FAIL_CLAIM_TIERS
    )

    checks: dict[str, bool] = {}
    failed: list[str] = []

    def mark(name: str, ok: bool) -> None:
        checks[name] = ok
        if not ok:
            failed.append(name)

    mark("artifact_bytes_present", bytes_value is not None)
    if bytes_value is None:
        bytes_value = -1

    mark("artifact_above_absolute_min_bytes", bytes_value >= ABSOLUTE_MIN_BYTES)
    mark("row_complete_false", packet.get("row_complete") is False)
    mark("no_complete_claim", packet.get("production_completion_allowed") is not True)
    mark("production_video_complete_not_claimed", packet.get("production_video_complete_claimed") is not True)
    mark("row074_untouched", packet.get("row074_touched") is not True)
    mark("ec2_untouched", packet.get("ec2_touched") is not True)

    # Smoke may be tiny; Class E proof-success language may not.
    # Explicit FAIL/REJECT attempt claims are allowed when proof-success language is absent.
    if uses_proof_success_language and not uses_smoke_language and not uses_fail_language:
        mark("class_e_proof_min_bytes", bytes_value >= CLASS_E_PROOF_MIN_BYTES)
        mark("visual_review_performed_for_proof_success", visual_performed)
        mark("claim_tier_not_smoke_when_proof_success", claim_tier not in {"", "smoke_emission"})
        # claim_tier must explicitly be class_e_runtime_proof for success language
        mark(
            "claim_tier_is_class_e_runtime_proof",
            claim_tier == "class_e_runtime_proof",
        )
        if visual_performed:
            mark("visual_review_pass_for_proof_success", visual_pass)
    elif uses_fail_language:
        mark("fail_claim_forbids_proof_success_language", not uses_proof_success_language)
        mark(
            "fail_claim_tier_or_status",
            claim_tier in FAIL_CLAIM_TIERS or bool(FAIL_OK_STATUS_RE.search(blob)),
        )
        # A Class E attempt FAIL should still show the climb ran a visual/VLM gate.
        mark("fail_attempt_visual_review_performed", visual_performed)
        # Bytes below Class E proof floor is an acceptable FAIL reason; do not require ≥250KB.
        mark(
            "fail_attempt_not_claiming_proof_landed",
            "proof_landed" not in blob.lower() or "fail" in blob.lower(),
        )
    else:
        # Smoke path: forbid leftover proof-success language.
        mark("smoke_claim_forbids_proof_success_language", not uses_proof_success_language)
        mark(
            "smoke_claim_tier_or_status",
            claim_tier == "smoke_emission" or uses_smoke_language,
        )

    technical = packet.get("technical_qa") if isinstance(packet.get("technical_qa"), dict) else {}
    if technical:
        mark("technical_qa_not_black", technical.get("checks", {}).get("no_black_frames", True) is True)
        if technical.get("technical_pass") is False and uses_proof_success_language:
            mark("technical_pass_required_for_proof_success", False)

    ok = not failed
    result = "pass_wan_ti2v_class_e_claim_policy" if ok else "fail_wan_ti2v_class_e_claim_policy"
    return {
        "schema_version": "1.0",
        "validator": "validate_wave64_wan_ti2v_class_e_runtime_proof_claim",
        "claim_tier_observed": claim_tier or None,
        "uses_proof_success_language": uses_proof_success_language,
        "uses_smoke_language": uses_smoke_language,
        "uses_fail_language": uses_fail_language,
        "artifact_bytes": bytes_value if bytes_value >= 0 else None,
        "thresholds": {
            "absolute_min_bytes": ABSOLUTE_MIN_BYTES,
            "class_e_proof_min_bytes": CLASS_E_PROOF_MIN_BYTES,
        },
        "visual_review": {
            "performed": visual_performed,
            "pass": visual_pass,
        },
        "checks": checks,
        "failed_checks": failed,
        "policy_pass": ok,
        "result": result,
        "boundaries": {
            "smoke_emission_is_not_class_e_proof_success": True,
            "product_visual_qa_required_before_proof_landed_status": True,
            "technical_decode_pass_is_not_identity_or_product_pass": True,
        },
        "next_action": (
            "Keep Status as Runtime_Smoke_Emitted / product visual QA open until a non-degenerate "
            "clip clears visual/VLM review; never promote Comfy success alone to Class E proof."
            if not ok
            else "Claim language matches smoke-vs-proof policy."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path, help="Evidence packet JSON")
    parser.add_argument("--out", type=Path, help="Optional policy result JSON")
    parser.add_argument(
        "--artifact-bytes",
        type=int,
        help="Override artifact byte count (e.g. from local pullback stat)",
    )
    args = parser.parse_args(argv)

    packet_path = args.packet if args.packet.is_absolute() else ROOT / args.packet
    packet = load_json(packet_path)
    result = evaluate_claim(packet, artifact_bytes=args.artifact_bytes)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        out = args.out if args.out.is_absolute() else ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
    sys.stdout.write(text)
    return 0 if result["policy_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
