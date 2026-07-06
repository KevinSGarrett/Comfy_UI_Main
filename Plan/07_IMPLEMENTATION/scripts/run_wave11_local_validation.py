#!/usr/bin/env python3
"""Run Wave 11 local static validation."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

def run(cmd, cwd):
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(cwd))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    rc = run([sys.executable, "07_IMPLEMENTATION/scripts/validate_wave11_control_pack.py", "--root", str(root)], root)
    if rc != 0:
        return rc

    print("Wave 11 static validation passed. Runtime control-map proof still required after local ComfyUI object_info capture.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
