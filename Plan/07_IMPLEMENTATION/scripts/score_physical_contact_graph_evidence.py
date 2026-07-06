#!/usr/bin/env python3
"""Score Wave 22 physical contact graph evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    checks = {
        "source_target_ownership_pass": bool(data.get("source_target_ownership_pass")),
        "pressure_intensity_pass": bool(data.get("pressure_intensity_pass")),
        "occlusion_pass": bool(data.get("occlusion_pass")),
        "duration_pass": bool(data.get("duration_pass")),
        "audio_force_pass": bool(data.get("audio_force_pass")),
        "deformation_evidence_pass": bool(data.get("deformation_evidence_pass")),
        "preservation_pass": bool(data.get("preservation_pass")),
    }
    score = sum(1 for value in checks.values() if value) / len(checks)
    report = {
        "evidence_version": "wave22.v1",
        "checks": checks,
        "score": round(score, 4),
        "pass": score >= 0.9 and all(checks.values()),
        "failure_flags": data.get("failure_flags", []),
    }

    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
