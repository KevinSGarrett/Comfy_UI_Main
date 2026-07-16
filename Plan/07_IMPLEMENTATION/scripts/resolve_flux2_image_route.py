from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SUPPORTED_CAPABILITIES = {"text_to_image", "single_reference_edit"}
KLEIN_LANE = "flux2_klein_4b_distilled"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("runtime proof must be a JSON object")
    return value


def select_route(capability: str, proof: dict[str, Any] | None) -> dict[str, Any]:
    if capability not in SUPPORTED_CAPABILITIES:
        return {
            "status": "BLOCKED",
            "classification": "BLOCKED_FLUX2_CAPABILITY_UNSUPPORTED",
            "capability": capability,
            "selected_lane": None,
        }
    if not proof:
        return {
            "status": "BLOCKED",
            "classification": "BLOCKED_FLUX2_RUNTIME_PROOF_MISSING",
            "capability": capability,
            "selected_lane": None,
        }
    capabilities = proof.get("capabilities")
    record = capabilities.get(capability) if isinstance(capabilities, dict) else None
    required = {
        "runtime_pass": True,
        "artifact_hash_bound": True,
        "direct_visual_qa_pass": True,
    }
    failed = [key for key, expected in required.items() if not isinstance(record, dict) or record.get(key) is not expected]
    if proof.get("lane_id") != KLEIN_LANE or proof.get("production_ready") is True or failed:
        return {
            "status": "BLOCKED",
            "classification": "BLOCKED_FLUX2_CAPABILITY_PROOF_INCOMPLETE",
            "capability": capability,
            "selected_lane": None,
            "failed_checks": failed,
        }
    return {
        "status": "PASS",
        "classification": "FLUX2_KLEIN_BOUNDED_ROUTE_SELECTED",
        "capability": capability,
        "selected_lane": KLEIN_LANE,
        "workflow_path": record.get("workflow_path"),
        "production_ready": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed FLUX.2 image capability router")
    parser.add_argument("--capability", required=True)
    parser.add_argument("--runtime-proof")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    proof = load_json(Path(args.runtime_proof)) if args.runtime_proof else None
    result = select_route(args.capability, proof)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
