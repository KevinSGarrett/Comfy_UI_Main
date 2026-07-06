# Wave 10 Main Flow Camera and Framing Review

## Summary

The current Main Flow is a strong image-generation staging canvas, but it does not yet contain a complete production camera solver. It contains fixed latent sizes, prompt-driven camera influence, an active-copy pose/camera LoRA reference, staged IPAdapter/ControlNet branches, and note-only boundaries for additional pose/depth/OpenPose controls.

## Observed Main Flow Evidence

```json
{
  "source_file": "Wave42_Runtime_Bound__UI__WAVE42_MAIN_FLOW_20260702(10).json",
  "source_sha256": "13297484923fa1ca7525fa913792b19999f395e05118e50eb269e48e4d1bc8bb",
  "observed_at_utc": "2026-07-05T23:30:00Z",
  "node_count": 356,
  "link_count": 91,
  "mode_counts": {
    "0": 82,
    "2": 274
  },
  "save_image_lanes": [
    "Main_Flow/SDXL_RealVisXL_LoRA",
    "Main_Flow/Flux_Family_ZImage",
    "Main_Flow/SDXL_RealVisXL_LoRA_Upscaled",
    "Main_Flow/SDXL_Inpaint_Detail",
    "Main_Flow/Flux_to_SDXL_Refine",
    "Main_Flow/True_Flux_Schnell_Reference_Smoke",
    "Main_Flow/ControlNet_Canny_Edge",
    "Main_Flow/IPAdapter_Face_Reference"
  ],
  "latent_image_nodes": [
    {
      "node_id": 16,
      "node_type": "EmptyLatentImage",
      "width": 1024,
      "height": 1280,
      "batch": 1
    },
    {
      "node_id": 35,
      "node_type": "EmptySD3LatentImage",
      "width": 1024,
      "height": 1024,
      "batch": 1
    },
    {
      "node_id": 104,
      "node_type": "EmptySD3LatentImage",
      "width": 512,
      "height": 512,
      "batch": 1
    },
    {
      "node_id": 115,
      "node_type": "EmptyLatentImage",
      "width": 768,
      "height": 768,
      "batch": 1
    },
    {
      "node_id": 125,
      "node_type": "EmptyLatentImage",
      "width": 768,
      "height": 768,
      "batch": 1
    }
  ],
  "ipadapter_nodes": [
    {
      "node_id": 112,
      "type": "IPAdapter",
      "widgets_values": [
        0.45,
        0,
        0.85,
        "standard"
      ]
    },
    {
      "node_id": 110,
      "type": "IPAdapterUnifiedLoader",
      "widgets_values": [
        "PLUS FACE (portraits)"
      ]
    }
  ],
  "controlnet_nodes": [
    {
      "node_id": 120,
      "type": "ControlNetLoader",
      "widgets_values": [
        "controlnet-canny-sdxl-1.0-small.safetensors"
      ]
    },
    {
      "node_id": 124,
      "type": "ControlNetApplyAdvanced",
      "widgets_values": [
        0.65,
        0,
        0.75
      ]
    }
  ],
  "note_boundaries": [
    {
      "node_id": 1,
      "text": "MAIN FLOW - Wave42 image generation canvas\nCanonical superseding workflow for the image-generation section. Built from the planned layout pages and the existing SDXL/RealVisXL + Flux-family runtime templates.\nExecutable lanes: SDXL/RealVisXL with organized Wave42 LoRA stack, Flux-family/Z-Image lane, and Flux-to-SDXL support pass."
    },
    {
      "node_id": 70,
      "text": "Reference / IPAdapter / ControlNet staging\nThe layout source calls for reference identity, pose/depth/edge/mask control, and regional inpaint. The face-reference IPAdapter branch is staged below as ready_to_verify from the prior smoke template. The Canny ControlNet edge-map branch is staged below as ready_to_verify. Additional reference-slot routing and pose/depth/openpose control maps remain notes until direct runtime proof exists."
    },
    {
      "node_id": 71,
      "text": "Image QA / promotion export\nOutputs are saved under Main_Flow/* prefixes so downstream QA, manifest intake, and tracker-promotion scripts can consume concrete image-generation artifacts instead of layout notes."
    },
    {
      "node_id": 72,
      "text": "Video/audio handoff boundary\nThe Main Flow now produces image outputs ready for video lanes. WAN/Hunyuan/LTXV/audio remain separate runtime lanes until their own ComfyUI node graphs are merged and proven."
    },
    {
      "node_id": 73,
      "text": "True Flux image-reference conditioning boundary\nThe true Flux Schnell reference-smoke/base lane is staged as ready_to_verify using the concrete Wave20 Flux smoke template. Actual image-reference conditioning remains note-only because current templates load or name references but do not wire reference pixels into generation."
    },
    {
      "node_id": 74,
      "text": "Inpaint, upscale, QA, release promotion\nFinal image QA, manifest intake, and tracker promotion remain notes until proven. Basic RealESRGAN upscale and SDXL inpaint/detail are staged and wired as ready_to_verify."
    },
    {
      "node_id": 130,
      "text": "IG-09 Image QA and evidence export\nRun export_wave42_main_flow_image_evidence.py after Main_Flow images are generated. It records lane prefix, file path, size, SHA256, dimensions, format, and basic decode QA."
    },
    {
      "node_id": 131,
      "text": "Evidence manifest output\nManifest path: Implementation/manifests/main_flow_image_qa_evidence/*.json. This is evidence intake, not tracker promotion by itself."
    },
    {
      "node_id": 132,
      "text": "QA boundary\nBasic file QA proves files are non-empty, decodable images with dimensions. Creative QA, runtime prompt proof, object_info visibility, and model-loader proof remain separate verification gates."
    },
    {
      "node_id": 133,
      "text": "IG-10 Main Flow promotion after runtime proof\nRun promote_wave42_main_flow_after_runtime_proof.py only after IG-09 finds exact Main_Flow outputs for the required lanes. Promotion is blocked until those runtime files exist."
    },
    {
      "node_id": 134,
      "text": "Promotion decision output\nManifest path: Implementation/manifests/main_flow_promotion/*.json. Verified is allowed only when all required lanes have passing evidence records."
    },
    {
      "node_id": 135,
      "text": "Current promotion boundary\nIf exact Main_Flow runtime outputs are absent, IG-10 must report blocked_missing_runtime_proof. It must not promote from layout notes or unrelated smoke outputs."
    },
    {
      "node_id": 136,
      "text": "WAVE42 DEPLOYED LORA LIBRARY - MANIFEST WIRED, DISABLED BY DEFAULT\nSource CSV: C:\\Comfy_UI_Lora\\Model_Organize\\wave07\\WAVE07_EC2_DEPLOY_MANIFEST.csv\nSource manifest JSON: C:\\Comfy_UI_Lora\\Model_Organize\\wave07\\WAVE07_EC2_DEPLOY_MANIFEST.json\nRegistry: C:\\Comfy_UI\\Implementation\\loras\\wave42_lora_registry.json\nStack profiles: C:\\Comfy_UI\\Implementation\\profiles\\wave42_stack_profiles.json\nThis sect
```

## Interpretation

The current flow can produce camera-influenced images, but Wave 10 adds the missing formal layer:

- camera plan JSON
- shot-size taxonomy
- lens registry
- angle taxonomy
- crop policy
- subject slot rules
- depth/DOF rules
- workflow patch targets
- QA gates

## Current Limitations To Fix Later

1. Camera controls are not yet centralized into App Mode inputs.
2. Latent dimensions are fixed inside nodes rather than patched from a camera plan.
3. Pose/depth/OpenPose remain note-only until runtime proof.
4. Camera terms inside LoRA names or prompts should not be used as the only camera source of truth.
5. Multi-character screen placement and depth order are not yet solved inside the current canvas.
6. Video camera motion requires separate video workflow proof.
