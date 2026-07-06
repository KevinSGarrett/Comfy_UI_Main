#!/usr/bin/env python3
"""
Validate that all JSON registry/schema/manifest files can be parsed.
This uses only Python's standard library so it can run on a fresh local repo.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = Path(args.root)
    checked = []
    failures = []
    for path in root.rglob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                json.load(f)
            checked.append(str(path))
        except Exception as exc:
            failures.append({"path": str(path), "error": str(exc)})

    report = {
        "schema_version": "wave03.json_registry_parse_report.v1",
        "root": str(root),
        "checked_count": len(checked),
        "failure_count": len(failures),
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(json.dumps({"result": report["result"], "checked_count": len(checked), "failure_count": len(failures)}, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
