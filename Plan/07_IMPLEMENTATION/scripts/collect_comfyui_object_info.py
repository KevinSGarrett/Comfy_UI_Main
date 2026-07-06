#!/usr/bin/env python3
"""
Collect a ComfyUI /object_info snapshot.

Run while local ComfyUI is running:
  python collect_comfyui_object_info.py --api-url http://127.0.0.1:8188 --out object_info_snapshot.json

This does not queue a render. It only records which node classes are visible to
the active ComfyUI runtime. Use it before turning on EC2 or before attempting
expensive GPU validation.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.request import urlopen, Request


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def fetch_json(url: str):
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8188")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    api_url = args.api_url.rstrip("/")
    object_info = fetch_json(f"{api_url}/object_info")

    wrapper = {
        "schema_version": "wave03.object_info_snapshot.v1",
        "comfyui_api_url": api_url,
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "node_type_count": len(object_info),
        "object_info": object_info,
    }
    write_json(Path(args.out), wrapper)
    print(json.dumps({"result": "PASS", "node_type_count": len(object_info), "out": args.out}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
