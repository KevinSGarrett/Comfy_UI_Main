#!/usr/bin/env python3
"""Submit one motion-stronger Wan 2.2 TI2V climb from sharp-hand start still.

Class A temporal follow-up: amplify breath/blink/weight-shift while retaining
sharp separated fingers + pores. CreateVideo bit_depth=10; no Flux LoRAs on Wan.
RunPod only; requires :8188 idle.

POST-CLIMB (required before Class A / Proof_Landed claim):
  python3 wave64_wan_ti2v_climb_visual.py --class-ladder class_a \\
    --images <frames...> --out <strict_receipt.json> --prompt-id <id>
  Fail closed without strict_pod_llm_review=PASS (qwen2.5vl:32b).
  Weak qwen2.5vl:7b vlm_review.json is SMOKE/observation only.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Shared producer gate (import proves wiring; runtime call is post-frame-extract).
STRICT_VISUAL_GATE = "wave64_wan_ti2v_climb_visual.py"
STRICT_CLIMB_KIND = "wan_ti2v_class_a"

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
    prefix = f"video/w64_019_023_runpod_wan_ti2v_motion_stronger_{stamp}"
    # New seed after 2272893 Class A REJECT (MUSHY_HANDS / PLASTIC_SKIN / motion_temporal=40)
    seed = 2273017
    steps = 42
    cfg = 6.0
    width, height, length = 704, 1280, 81
    bit_depth = 10
    wf = json.loads(WF.read_text(encoding="utf-8"))
    if any("lora" in v.get("class_type", "").lower() for v in wf.values()):
        raise SystemExit("FLUX_LORA_FORBIDDEN_ON_WAN")

    pos = (
        "photoreal cinematic medium waist-up studio video of one fully clothed adult woman, "
        "preserve exact face identity hairstyle clothing proportions and neutral gray studio background, "
        "CRITICAL: razor-sharp anatomically correct hands with five distinct fully separated fingers, "
        "visible knuckles nail beds finger gaps and natural tendon lines, palms and fingertips crisp toward camera, "
        "CRITICAL: natural living human skin with visible pores freckles subsurface scatter fine peach fuzz "
        "and uneven microtexture, never plastic never waxy never airbrushed, "
        "VERY STRONG unmistakable continuous living human motion across the whole clip (not subtle): "
        "large rhythmic chest breathing with obvious ribcage and sternum rise-fall at least twice, "
        "one unmistakable slow full blink with eyelids fully closing then fully reopening mid-clip, "
        "clear weight transfer with visible hip sway torso torque and shoulder settle, "
        "soft fabric micro-movement on sleeves and collar responding to breath and weight shift, "
        "subtle chin dip then recover, head micro-turn, hands stay sharp coherent no mush no fuse, "
        "locked static camera, stable framing, physically coherent continuous living motion, not a still photo"
    )
    neg = (
        "camera movement, zoom, pan, cut, scene change, identity drift, face morphing, age change, "
        "hairstyle change, clothing change, background change, body warping, limb deformation, "
        "extra limbs, deformed hands, fused fingers, mushy hands, melted fingers, blob hands, "
        "poorly separated fingers, missing fingers, extra fingers, webbed fingers, sausage fingers, "
        "foot sliding, jitter, flicker, temporal inconsistency, near-static freeze, frozen pose, "
        "statue, mannequin, no motion, almost no movement, locked still frame, posed photograph, "
        "minimal motion, subtle-only motion, athletic crouch, deep squat, "
        "oversmoothed skin, plastic skin, waxy skin, wax figure, doll skin, airbrushed skin, "
        "porcelain skin, blur, low quality, watermark, text, nude, nsfw, explicit"
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
    wf["11"]["inputs"].update({"fps": 24, "bit_depth": bit_depth})
    wf["12"]["inputs"].update(
        {"filename_prefix": prefix, "format": "mp4", "codec": "h264"}
    )
    payload = {"prompt": wf, "client_id": f"w64_019_023_motion_stronger_{stamp}"}
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
        "bit_depth": bit_depth,
        "source_image": SRC,
        "source_sha256": sha,
        "positive": pos,
        "negative": neg,
        "intent": (
            "class_a_motion_stronger_hands_skin_motion_retry_bit_depth10_steps42_"
            "from_6a5e81b8_strict32b_reject_mushy_hands_plastic_skin_weak_motion"
        ),
        "prior_class_a_fail_prompt_id": "6a5e81b8-b751-459e-a3cc-b9cb257a08f1",
        "prior_strict_reject": "MUSHY_HANDS|PLASTIC_SKIN|motion_temporal=40",
        "flux_loras_attached": False,
        "wan_refetch": False,
        "row017_redo": False,
        "reencode_pad": False,
        "generation_receipt_is_not_visual_approval": True,
        "strict_visual_gate_required": True,
        "strict_visual_gate_script": STRICT_VISUAL_GATE,
        "strict_climb_kind": STRICT_CLIMB_KIND,
        "strict_pod_llm_review_required_for_product": True,
        "weak_vlm_7b_is_smoke_only": True,
        "required_next_step": (
            f"After frame extract: python3 {STRICT_VISUAL_GATE} "
            f"--class-ladder class_a --images <frames> "
            f"--out strict_receipt.json --prompt-id {resp['prompt_id']}"
        ),
        "node_errors": resp.get("node_errors") or {},
    }
    out = Path(
        f"/workspace/comfy_output/video/w64_019_023_motion_stronger_submit_{stamp}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    Path(
        "/workspace/comfy_output/video/w64_019_023_motion_stronger_latest_prompt_id.txt"
    ).write_text(resp["prompt_id"] + "\n", encoding="utf-8")
    Path(
        "/workspace/comfy_output/video/w64_019_023_motion_stronger_latest_prefix.txt"
    ).write_text(prefix + "\n", encoding="utf-8")
    Path(
        "/workspace/comfy_output/video/w64_019_023_motion_stronger_latest_stamp.txt"
    ).write_text(stamp + "\n", encoding="utf-8")
    print(resp["prompt_id"])
    print(prefix)
    print(str(out))


if __name__ == "__main__":
    main()
