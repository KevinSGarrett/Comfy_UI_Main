#!/usr/bin/env python3
"""Submit one Wan 2.2 TI2V climb from the sharp-hand start still (RunPod only)."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

COMFY = "http://127.0.0.1:8188"
WF = Path(
    "/workspace/wave64/Workflows/video_generation/"
    "wan_2_2_ti2v_5b_primary_lane/workflow.api.json"
)
SRC = "c1_sharp_hand_start_still_20260721T092218Z_a1.png"
EXPECT_SHA = "ac43980940f3ae3187249f485bdd94ec69550a9cb96d4df3ebf163c8712cbcc4"


def main() -> None:
    q = json.load(urllib.request.urlopen(f"{COMFY}/queue", timeout=10))
    if q.get("queue_running") or q.get("queue_pending"):
        raise SystemExit(
            f"NOT_IDLE running={len(q.get('queue_running', []))} "
            f"pending={len(q.get('queue_pending', []))}"
        )

    src_path = Path("/workspace/comfy_input") / SRC
    sha = hashlib.sha256(src_path.read_bytes()).hexdigest()
    if sha != EXPECT_SHA:
        raise SystemExit(f"SHA_MISMATCH {sha}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = f"video/w64_019_023_runpod_wan_ti2v_sharp_hand_climb_{stamp}"
    seed = 2272611
    steps = 38
    cfg = 6.0
    width, height, length = 704, 1280, 81
    wf = json.loads(WF.read_text(encoding="utf-8"))
    if any("lora" in v.get("class_type", "").lower() for v in wf.values()):
        raise SystemExit("FLUX_LORA_FORBIDDEN_ON_WAN")

    pos = (
        "photoreal cinematic medium waist-up studio video of one fully clothed adult woman, "
        "preserve exact face identity hairstyle clothing proportions and neutral gray studio background, "
        "preserve sharp anatomically correct hands with clearly separated fingers knuckles and nails toward camera, "
        "natural human skin with visible pores freckles microtexture not plastic, "
        "CLEAR simple natural motion: gentle chest breathing rise and fall, "
        "one full blink eyelids close then open, small relaxed weight shift with subtle hip settle, "
        "soft fabric micro-movement, hands stay sharp and coherent no mush no fuse, "
        "locked static camera, stable framing, physically coherent continuous motion"
    )
    neg = (
        "camera movement, zoom, pan, cut, scene change, identity drift, face morphing, age change, "
        "hairstyle change, clothing change, background change, body warping, limb deformation, "
        "extra limbs, deformed hands, fused fingers, mushy hands, melted fingers, blob hands, "
        "poorly separated fingers, missing fingers, extra fingers, foot sliding, jitter, flicker, "
        "temporal inconsistency, near-static freeze, frozen pose, no motion, athletic crouch, deep squat, "
        "oversmoothed skin, plastic skin, waxy skin, wax figure, doll skin, airbrushed skin, "
        "blur, low quality, watermark, text, nude, nsfw, explicit"
    )
    wf["4"]["inputs"]["text"] = pos
    wf["5"]["inputs"]["text"] = neg
    wf["7"]["inputs"]["image"] = SRC
    wf["8"]["inputs"].update(
        {"width": width, "height": height, "length": length, "batch_size": 1}
    )
    wf["9"]["inputs"].update(
        {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": "uni_pc",
            "scheduler": "simple",
            "denoise": 1.0,
        }
    )
    wf["11"]["inputs"]["fps"] = 24
    wf["12"]["inputs"].update(
        {"filename_prefix": prefix, "format": "mp4", "codec": "h264"}
    )
    payload = {"prompt": wf, "client_id": f"w64_019_023_sharp_hand_climb_{stamp}"}
    req = urllib.request.Request(
        f"{COMFY}/prompt",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = json.load(urllib.request.urlopen(req, timeout=60))
    meta = {
        "prompt_id": resp["prompt_id"],
        "prefix": prefix,
        "stamp": stamp,
        "seed": seed,
        "steps": steps,
        "cfg": cfg,
        "width": width,
        "height": height,
        "length": length,
        "source_image": SRC,
        "source_sha256": sha,
        "positive": pos,
        "negative": neg,
        "intent": "sharp_hand_start_still_wan_ti2v_climb_breathing_blink_weightshift",
        "flux_loras_attached": False,
        "wan_refetch": False,
        "row017_redo": False,
        "node_errors": resp.get("node_errors") or {},
    }
    out = Path(f"/workspace/comfy_output/video/w64_019_023_sharp_hand_climb_submit_{stamp}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    Path("/workspace/comfy_output/video/w64_019_023_sharp_hand_climb_latest_prompt_id.txt").write_text(
        resp["prompt_id"] + "\n", encoding="utf-8"
    )
    Path("/workspace/comfy_output/video/w64_019_023_sharp_hand_climb_latest_prefix.txt").write_text(
        prefix + "\n", encoding="utf-8"
    )
    print(resp["prompt_id"])
    print(prefix)
    print(str(out))


if __name__ == "__main__":
    main()
