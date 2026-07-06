#!/usr/bin/env python3
"""Score Wave15 base image evidence.

The script uses stdlib file checks and optionally PIL if available.
It can run without PIL, but dimension checks are stronger with PIL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_image(path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "byte_size": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else None,
        "format": None,
        "width": None,
        "height": None,
        "decode_status": "not_checked"
    }

    if not path.exists() or path.stat().st_size == 0:
        result["decode_status"] = "missing_or_empty"
        return result

    try:
        from PIL import Image  # type: ignore
        with Image.open(path) as img:
            result["format"] = img.format
            result["width"], result["height"] = img.size
            result["decode_status"] = "pass"
    except Exception as exc:
        result["decode_status"] = f"pil_decode_failed_or_unavailable:{type(exc).__name__}"

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane-id", required=True)
    parser.add_argument("--images", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    files = [inspect_image(Path(p)) for p in args.images]
    hard_fail = any(not f["exists"] or f["byte_size"] <= 0 for f in files)
    decode_pass_or_unknown = all(f["decode_status"] in ("pass",) or f["decode_status"].startswith("pil_decode_failed_or_unavailable") for f in files)

    status = "pass" if files and not hard_fail and decode_pass_or_unknown else "fail"

    report = {
        "report_id": f"{args.lane_id}__base_image_evidence_score",
        "lane_id": args.lane_id,
        "status": status,
        "scores": {
            "file_presence": 1.0 if not hard_fail else 0.0,
            "decode": 1.0 if all(f["decode_status"] == "pass" for f in files) else 0.5 if decode_pass_or_unknown else 0.0
        },
        "files": files,
        "promotion_decision": "base_candidate_passed" if status == "pass" else "rerun_or_fallback"
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
