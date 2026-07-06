#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "00_PROJECT_CONTROL/WAVE_00_TO_19_MASTER_SCHEDULE.md",
    "00_PROJECT_CONTROL/AI_PROJECT_MANAGER_OPERATING_MANUAL.md",
    "01_CURRENT_SYSTEM_REVIEW/MAIN_FLOW_REVIEW_FINDINGS.md",
    "02_TARGET_ARCHITECTURE/END_TO_END_ARCHITECTURE.md",
    "03_IMAGE_SYSTEM/PASS_PLANNER_SPEC.md",
    "06_QA_TESTING/STRICT_QA_GATES.md",
    "08_SCHEMAS/pass_plan.schema.json",
    "08_SCHEMAS/scene_request.schema.json",
    "08_SCHEMAS/qa_manifest.schema.json",
    "10_REGISTRIES/current_main_flow_summary.json",
    "11_RELEASES/WAVE00_DELIVERY_REPORT.md",
]

def main():
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    json_errors = []
    for path in ROOT.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            json_errors.append((str(path.relative_to(ROOT)), str(exc)))
    ok = not missing and not json_errors
    report = {
        "status": "PASS" if ok else "FAIL",
        "missing_required_files": missing,
        "json_errors": json_errors,
        "checked_root": str(ROOT)
    }
    out = ROOT / "11_RELEASES" / "WAVE00_VALIDATION_REPORT.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if ok else 1)

if __name__ == "__main__":
    main()
