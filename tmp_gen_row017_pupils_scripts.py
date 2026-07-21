#!/usr/bin/env python3
"""Generate Row017 mf70_pupils_iris_sclera producer/VLM/launcher from eyebrows templates on the pod."""
from __future__ import annotations

import os
import py_compile
import re
from pathlib import Path

ROOT = Path("/workspace")


def main() -> None:
    text = (ROOT / "tmp_row017_runpod_mf70_eyebrows_producer.py").read_text(encoding="utf-8")
    text = text.replace("mf70_eyebrows", "mf70_pupils_iris_sclera")
    text = text.replace("MF70_EYEBROWS", "MF70_PUPILS_IRIS_SCLERA")
    text = text.replace("SEED = 210824", "SEED = 210811")
    text = text.replace("DENOISE = 0.03", "DENOISE = 0.035")
    text = text.replace("CFG = 3.2", "CFG = 3.4")
    text = text.replace(
        "cursor-row017-mf70-eyebrows-runpod",
        "cursor-row017-mf70-pupils-runpod",
    )
    text = text.replace(
        "wave70_mf70_pupils_iris_sclera_visible_brow_v4_20260710T001900-0500",
        "wave70_mf70_pupils_iris_sclera_v3_20260708T005000-0500",
    )
    text = text.replace(
        'MASK = ASSET_DIR / "wave70_mf70_pupils_iris_sclera_visible_brow_v4_mask.png"',
        'MASK = ASSET_DIR / "wave70_mf70_pupils_iris_sclera_v3_mask.png"',
    )
    text = text.replace(
        '"filename": "wave70_mf70_pupils_iris_sclera_visible_brow_v4_mask.png"',
        '"filename": "wave70_mf70_pupils_iris_sclera_v3_mask.png"',
    )
    text = text.replace(
        "wave64_row017_mf70_pupils_iris_sclera_src_",
        "wave64_row017_mf70_pupils_src_",
    )
    text = text.replace(
        "wave64_row017_mf70_pupils_iris_sclera_mask_",
        "wave64_row017_mf70_pupils_mask_",
    )
    text = text.replace(
        "ROW017-RUNPOD-MF70-EYEBROWS-VISUAL-QA-",
        "ROW017-RUNPOD-MF70-PUPILS-IRIS-SCLERA-VISUAL-QA-",
    )
    text = text.replace(
        "W64-RUNPOD-COMFYUI-ROW017-MF70-EYEBROWS-EXECUTE-",
        "W64-RUNPOD-COMFYUI-ROW017-MF70-PUPILS-IRIS-SCLERA-EXECUTE-",
    )

    pos = (
        "extremely subtle photoreal pupil iris sclera preservation pass, preserve exact person "
        "identity, gaze direction, eye symmetry, iris color, pupil size, sclera tone, catchlights, "
        "eyelids, eyelashes, eyebrow position, nearby hair occlusion, surrounding skin texture, "
        "face lighting, white blazer, background, and portrait composition unchanged"
    )
    neg = (
        "identity change, different person, gaze change, mismatched eyes, crossed eyes, "
        "asymmetrical pupils, enlarged pupils, blown catchlights, missing catchlights, "
        "iris color change, glassy eyes, doll eyes, anime eyes, red eyes, sclera discoloration, "
        "eyelid deformation, eyelash mutation, eyebrow change, hair mutation, visible seam, "
        "skin tone change, clothing change, background change, watermark, text"
    )
    text = re.sub(
        r"POS = \(\n    \".*?\"\n\)",
        f'POS = (\n    "{pos}"\n)',
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"NEG = \(\n    \".*?\"\n\)",
        f'NEG = (\n    "{neg}"\n)',
        text,
        count=1,
        flags=re.S,
    )
    text = text.replace(
        """            "regions_scanned": [
                "eyebrows",
""",
        """            "regions_scanned": [
                "pupils_iris_sclera",
""",
    )
    if '"pupils_iris_sclera"' not in text:
        text = text.replace('"eyebrows"', '"pupils_iris_sclera"', 1)

    outp = ROOT / "tmp_row017_runpod_mf70_pupils_iris_sclera_producer.py"
    outp.write_text(text, encoding="utf-8")
    py_compile.compile(str(outp), doraise=True)
    assert "SEED = 210811" in text
    assert "DENOISE = 0.035" in text
    assert "wave70_mf70_pupils_iris_sclera_v3_mask.png" in text
    assert "visible_brow" not in text
    print("producer_ok", outp.stat().st_size)

    vtext = (ROOT / "tmp_row017_runpod_mf70_eyebrows_vlm_deepen.py").read_text(encoding="utf-8")
    vtext = vtext.replace("mf70_eyebrows", "mf70_pupils_iris_sclera")
    vtext = vtext.replace("MF70_EYEBROWS", "MF70_PUPILS_IRIS_SCLERA")
    prompt = (
        "You are a bounded Wave64 Row017 VLM critic for a localized SDXL mf70_pupils_iris_sclera "
        "inpaint. Image 1 is the producer output; image 2 (if present) is source|output side-by-side. "
        "The mask covers pupil/iris/sclera cores of both eyes; planned change is a very subtle "
        "pupil/iris/sclera preservation pass while preserving identity, gaze symmetry, iris color, "
        "pupil size, sclera tone, catchlights, eyelids, eyelashes, eyebrows, nearby hair occlusion, "
        "mouth, nose bridge, neck, clothing, background, lighting, and framing. Assess whole-frame "
        "identity preservation, gaze/iris/catchlight stability, sclera naturalness, mouth stability, "
        "hard mask edges, and whether any refinement stayed inside the pupils/iris/sclera mask. "
        "Return ONLY compact JSON with keys: frame_ok (bool), identity_preserved (bool), "
        "eyes_ok (bool), mouth_ok (bool), background_ok (bool), hard_mask_edge (bool), "
        "target_region_refined (bool), global_defects (array of strings), summary (string <= 280 chars), "
        "promotion_allowed (always false), row_complete_allowed (always false), uncertainty (0..1). "
        "Do not invent media. Do not claim COMPLETE."
    )
    vtext = re.sub(
        r'prompt = \(\n        ".*?"\n    \)',
        f'prompt = (\n        "{prompt}"\n    )',
        vtext,
        count=1,
        flags=re.S,
    )
    vout = ROOT / "tmp_row017_runpod_mf70_pupils_iris_sclera_vlm_deepen.py"
    vout.write_text(vtext, encoding="utf-8")
    py_compile.compile(str(vout), doraise=True)
    print("vlm_ok", vout.stat().st_size)

    launcher = """#!/usr/bin/env bash
# Wait for Comfy :8188 idle (do not kill foreign/tournament), then run pupils producer+VLM.
set -euo pipefail
source /workspace/paths.env
export WAVE64_ROOT="${WAVE64_ROOT:-/workspace/wave64}"
export COMFY_URL="${COMFY_URL:-http://127.0.0.1:8188}"
export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
export ROW017_VLM_MODEL="${ROW017_VLM_MODEL:-qwen2.5vl:7b}"

LOG=/workspace/tmp_row017_pupils_run.log
exec > >(tee -a "$LOG") 2>&1

echo "=== pupils wait/run $(date -Is) ==="
echo "WAVE64_ROOT=$WAVE64_ROOT COMFY_URL=$COMFY_URL"

python3 - <<'PY'
import json, time, urllib.request, os, sys
api = os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")

def get(path, timeout=10):
    with urllib.request.urlopen(api + path, timeout=timeout) as r:
        return json.loads(r.read().decode())

for i in range(60):
    try:
        st = get("/system_stats", timeout=5)
        print("comfy_up", st.get("system", {}).get("comfyui_version"))
        break
    except Exception as e:
        print("comfy_down_wait", type(e).__name__, e)
        lock = "/tmp/mf_gpu_tournament.lockdir"
        if not os.path.exists(lock) and i > 0 and i % 6 == 0:
            print("attempt_start_comfy_no_tournament_lock")
            os.system("bash /workspace/04_start_comfy.sh >/workspace/tmp_start_comfy_pupils.log 2>&1 &")
        time.sleep(10)
else:
    print("FATAL comfy never came up")
    sys.exit(2)

deadline = time.time() + 7200
while time.time() < deadline:
    try:
        q = get("/queue", timeout=10)
    except Exception as e:
        print("queue_poll_err", e)
        time.sleep(10)
        continue
    running = len(q.get("queue_running") or [])
    pending = len(q.get("queue_pending") or [])
    rid = q["queue_running"][0][1] if q.get("queue_running") else None
    print(f"queue running={running} pending={pending} rid={rid}")
    if running == 0 and pending == 0:
        print("queue_idle")
        break
    time.sleep(20)
else:
    print("FATAL queue busy beyond 7200s")
    sys.exit(3)
print("idle_ok")
PY

cd "$WAVE64_ROOT"
test -f /workspace/tmp_row017_runpod_mf70_pupils_iris_sclera_producer.py
test -f /workspace/tmp_row017_runpod_mf70_pupils_iris_sclera_vlm_deepen.py

python3 /workspace/tmp_row017_runpod_mf70_pupils_iris_sclera_producer.py
PROD_RC=$?
echo "producer_rc=$PROD_RC"
if [[ $PROD_RC -ne 0 ]]; then
  exit $PROD_RC
fi

STAMP=$(python3 - <<'PY'
from pathlib import Path
base = Path("/workspace/wave64/Plan/Instructions/Operations/Pulled_Back_Artifacts")
cands = sorted(
    base.glob("runpod_comfyui_row017_mf70_pupils_iris_sclera_*"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)
print(cands[0].name.split("runpod_comfyui_row017_mf70_pupils_iris_sclera_", 1)[1])
PY
)
export ROW017_PRODUCER_STAMP="$STAMP"
echo "ROW017_PRODUCER_STAMP=$STAMP"
python3 /workspace/tmp_row017_runpod_mf70_pupils_iris_sclera_vlm_deepen.py
echo "vlm_rc=$?"
echo "=== done $(date -Is) ==="
"""
    lpath = ROOT / "tmp_row017_pod_wait_idle_run_pupils.sh"
    lpath.write_text(launcher, encoding="utf-8")
    os.chmod(lpath, 0o755)
    print("launcher_ok", lpath)


if __name__ == "__main__":
    main()
