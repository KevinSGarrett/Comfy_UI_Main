#!/usr/bin/env python3
from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
FILES = [
    ROOT / "Plan/07_IMPLEMENTATION/scripts/wave64_autonomous_vlm_client.py",
    ROOT / "Plan/07_IMPLEMENTATION/scripts/wave64_pod_strict_visual_qa.py",
    ROOT / "Plan/07_IMPLEMENTATION/scripts/wave64_climb_strict_visual_gate.py",
    ROOT / "Plan/07_IMPLEMENTATION/scripts/wave64_wan_ti2v_climb_visual.py",
    ROOT / "Plan/07_IMPLEMENTATION/scripts/_tmp_w64_019_rerun_strict_motion_stronger.sh",
    ROOT / "Plan/07_IMPLEMENTATION/scripts/_tmp_w64_019_wait_extract_strict_motion_stronger.sh",
    ROOT / "Plan/07_IMPLEMENTATION/scripts/_tmp_w64_019_oneshot_strict_motion_stronger.sh",
]
REMOTE = "/workspace/wave64_repo_scripts"


def main() -> int:
    for path in FILES:
        data = path.read_bytes()
        b64 = base64.b64encode(data)
        remote = f"{REMOTE}/{path.name}"
        remote_py = (
            "import sys,base64;"
            f"open({remote!r},'wb').write(base64.b64decode(sys.stdin.buffer.read()));"
            f"print('wrote',{remote!r},{len(data)})"
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
        out = proc.stdout.decode("utf-8", errors="replace")
        err = proc.stderr.decode("utf-8", errors="replace")
        print(path.name, "rc", proc.returncode, out.strip(), err[:300])
        if proc.returncode != 0:
            return proc.returncode
    verify = subprocess.run(
        [
            "ssh",
            "-o",
            "ConnectTimeout=30",
            "-p",
            "52077",
            "root@195.26.233.100",
            "cd /workspace/wave64_repo_scripts && python3 -c \"from wave64_autonomous_vlm_client import chat_with_images; import inspect; print(inspect.signature(chat_with_images))\"",
        ],
        capture_output=True,
        text=True,
    )
    print("VERIFY", verify.stdout.strip(), verify.stderr[:200])
    return verify.returncode


if __name__ == "__main__":
    raise SystemExit(main())
