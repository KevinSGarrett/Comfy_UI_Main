#!/usr/bin/env python3
"""Validate the sealed, narrow Wav2Vec2 expanded-alignment acceptance packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class AcceptanceError(RuntimeError):
    """Raised when retained campaign evidence violates its immutable contract."""


EXPECTED_FILES = {
    "calibration_receipt.json": "533cd88a1205468e78087335ede874754bcbbfc14037344d533d5d14206e6361",
    "held_out_receipt.json": "f1797ededd4665829fe9be7d715ff42fa39cf4a0482fa3558a16756593be5292",
    "coordinator_lease_granted.json": "9252dedd6b7b6db4ee07f35721e3f57ebbfb94aa66c70d433c02bd2f9513dfb3",
    "coordinator_lease_released.json": "5eb656eccdb2b7448adbecbed43adffcca81fd8accf7aebf139e508205b3f0f5",
}
EXPECTED_CASES = {
    "calibration": ["align_qwen_english", "align_ambience_refusal", "align_foley_refusal"],
    "held_out": [
        "align_natural_english",
        "align_spanish_diagnostic",
        "align_code_switch_diagnostic",
        "align_transcript_mismatch_refusal",
        "align_overlap_refusal",
    ],
}
EXPECTED_PLAN_SHA256 = "a8bd9b6bdeaf16be3ab1dd83f6cdf73dcec717ba25f03986bc3bf84071be50d4"
EXPECTED_MODEL_REVISION = "ae45363bf3413b374fecd9dc8bc1df0e24c3b7f4"
EXPECTED_WEIGHT_SHA256 = "3173bde9e9ce490fa0f989e413c42f25bc1820c020adc1e6b9b87025b3cfcc5e"
EXPECTED_EVIDENCE_SET_SHA256 = "6f7d8add2df118bbfed3926b472d919765973fbaf472983d37537731aab06c3b"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def reject_secret_keys(value: Any) -> None:
    if isinstance(value, dict):
        if "lease_token" in value:
            raise AcceptanceError("retained evidence contains a lease token")
        for child in value.values():
            reject_secret_keys(child)
    elif isinstance(value, list):
        for child in value:
            reject_secret_keys(child)


def evidence_set_hash(root: Path) -> str:
    rows = []
    for name in sorted(EXPECTED_FILES):
        relative = f"Plan/Tracker/Evidence/{root.name}/{name}"
        rows.append(f"{relative}:{sha256(root / name)}\n")
    return hashlib.sha256("".join(rows).encode()).hexdigest()


def validate_partition(
    receipt: dict[str, Any], partition: str, lease_id: str, cleanup_tolerance: int
) -> None:
    expected_status = f"PASS_{partition.upper()}_PARTITION_AND_PROCESS_EXIT_CLEANUP"
    if receipt.get("status") != expected_status or receipt.get("partition") != partition:
        raise AcceptanceError(f"{partition} terminal status mismatch")
    if receipt.get("plan_sha256") != EXPECTED_PLAN_SHA256:
        raise AcceptanceError(f"{partition} plan identity mismatch")
    package = receipt.get("package", {})
    if (
        package.get("revision") != EXPECTED_MODEL_REVISION
        or package.get("weight_sha256") != EXPECTED_WEIGHT_SHA256
    ):
        raise AcceptanceError(f"{partition} model identity mismatch")
    lease = receipt.get("lease", {})
    if (
        lease.get("valid") is not True
        or lease.get("lease_id") != lease_id
        or lease.get("project") != "comfyui_main"
        or lease.get("profile") != "comfyui_model_qualification"
        or lease.get("lease_mode") != "exclusive"
        or float(lease.get("reserved_peak_gib", 0)) != 4.0
    ):
        raise AcceptanceError(f"{partition} lease binding mismatch")
    results = receipt.get("results", [])
    if [item.get("case_id") for item in results] != EXPECTED_CASES[partition]:
        raise AcceptanceError(f"{partition} case ordering or identity mismatch")
    if any(item.get("passed") is not True for item in results):
        raise AcceptanceError(f"{partition} contains a failed case")
    runtime = receipt.get("runtime", {})
    delta = runtime.get("process_exit_cleanup_delta_mib")
    if runtime.get("process_exit_cleanup_pass") is not True or not isinstance(delta, int) or delta > cleanup_tolerance:
        raise AcceptanceError(f"{partition} process-exit cleanup failed")
    authority = receipt.get("authority", {})
    if authority.get("exact_partition_control_behavior") is not True:
        raise AcceptanceError(f"{partition} exact control authority missing")
    forbidden = {
        "general_forced_alignment",
        "multilingual_alignment",
        "overlap_alignment",
        "audio_event_recognition",
        "operational_activation",
        "product_promotion",
    }
    if any(authority.get(key) is not False for key in forbidden):
        raise AcceptanceError(f"{partition} authority exceeds the admitted scope")


def validate(root: Path, acceptance_path: Path) -> None:
    if root.resolve() != acceptance_path.parent.resolve():
        raise AcceptanceError("acceptance packet escaped its evidence root")
    observed = {path.name for path in root.iterdir() if path.is_file()}
    required = set(EXPECTED_FILES) | {acceptance_path.name}
    if observed != required or any((root / name).is_symlink() for name in observed):
        raise AcceptanceError("evidence file set mismatch or unsafe member")
    for name, expected in EXPECTED_FILES.items():
        if sha256(root / name) != expected:
            raise AcceptanceError(f"retained receipt hash mismatch: {name}")
    documents = {name: load(root / name) for name in EXPECTED_FILES}
    for document in documents.values():
        reject_secret_keys(document)
    grant = documents["coordinator_lease_granted.json"]
    release = documents["coordinator_lease_released.json"]
    lease_id = grant.get("lease_id")
    if (
        grant.get("event") != "LEASE_GRANTED"
        or grant.get("project") != "comfyui_main"
        or grant.get("mode") != "exclusive"
        or float(grant.get("peak_gib", 0)) != 4.0
        or not isinstance(lease_id, str)
        or release.get("event") != "LEASE_RELEASED"
        or release.get("lease_id") != lease_id
        or release.get("project") != "comfyui_main"
        or release.get("result") != "completed_and_evidenced"
        or release.get("occurred_at", "") <= grant.get("occurred_at", "")
    ):
        raise AcceptanceError("coordinator grant/release chain mismatch")
    validate_partition(documents["calibration_receipt.json"], "calibration", lease_id, 1024)
    validate_partition(documents["held_out_receipt.json"], "held_out", lease_id, 1024)
    calibration = documents["calibration_receipt.json"]
    held_out = documents["held_out_receipt.json"]
    matched = next(item for item in calibration["results"] if item["case_id"] == "align_qwen_english")
    mismatch = next(item for item in held_out["results"] if item["case_id"] == "align_transcript_mismatch_refusal")
    if float(matched["greedy_similarity"]) - float(mismatch["greedy_similarity"]) < 0.15:
        raise AcceptanceError("held-out mismatch refusal is not calibration-bound")
    acceptance = load(acceptance_path)
    if acceptance.get("status") != "PARTIALLY_ADOPTED_EXACT_WAV2VEC2_ALIGNMENT_CONTROLS_ONLY":
        raise AcceptanceError("acceptance status mismatch")
    if acceptance.get("evidence_set_sha256") != evidence_set_hash(root) or evidence_set_hash(root) != EXPECTED_EVIDENCE_SET_SHA256:
        raise AcceptanceError("evidence-set content identity mismatch")
    bindings = acceptance.get("bindings", {})
    if any(bindings.get(name, {}).get("sha256") != expected for name, expected in EXPECTED_FILES.items()):
        raise AcceptanceError("acceptance receipt binding mismatch")
    if acceptance.get("authority", {}).get("product_or_role_promotion") is not False:
        raise AcceptanceError("acceptance grants forbidden promotion authority")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_root", type=Path)
    parser.add_argument("--acceptance", type=Path, required=True)
    args = parser.parse_args()
    validate(args.evidence_root, args.acceptance)
    print("W64_AQA_WAV2VEC2_EXPANDED_ALIGNMENT_ACCEPTANCE_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
