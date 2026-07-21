#!/usr/bin/env python3
"""Transfer Wave64 climb helper scripts to RunPod via SSH stdin base64."""
from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
REMOTE_DIR = "/workspace/wave64_repo_scripts"
FILES = [
    ROOT / "Plan/07_IMPLEMENTATION/scripts/_tmp_w64_019_wait_extract_strict_motion_stronger.sh",
    ROOT / "Plan/07_IMPLEMENTATION/scripts/wave64_pod_strict_visual_qa.py",
    ROOT / "Plan/07_IMPLEMENTATION/scripts/wave64_wan_ti2v_climb_visual.py",
    ROOT / "Plan/07_IMPLEMENTATION/scripts/wave64_climb_strict_visual_gate.py",
]


def main() -> int:
    for path in FILES:
        data = path.read_bytes()
        b64 = base64.b64encode(data)
        remote = f"{REMOTE_DIR}/{path.name}"
        remote_py = (
            "import sys,base64;"
            f"open({remote!r},'wb').write(base64.b64decode(sys.stdin.buffer.read()))"
        )
        proc = subprocess.run(
            [
                "ssh",
                "-o",
                "ConnectTimeout=30",
                "-p",
                "52077",
                "root@195.26.233.100",
                f"python3 -c {remote_py!r}",
            ],
            input=b64,
            capture_output=True,
        )
        print(path.name, "rc", proc.returncode, "bytes", len(data))
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr.decode("utf-8", errors="replace")[:800])
            return proc.returncode
        # chmod shell scripts
        if path.suffix == ".sh":
            subprocess.run(
                [
                    "ssh",
                    "-o",
                    "ConnectTimeout=30",
                    "-p",
                    "52077",
                    "root@195.26.233.100",
                    f"chmod +x {remote}",
                ],
                check=False,
            )
    print("ALL_SYNCED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
