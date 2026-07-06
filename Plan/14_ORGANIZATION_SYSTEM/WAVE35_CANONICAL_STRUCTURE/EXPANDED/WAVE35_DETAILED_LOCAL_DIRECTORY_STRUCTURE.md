# Wave 35 Detailed Local Directory Structure

Recommended local root:

```text
C:\Comfy_UI_Hyperrealism_System
├── 00_ADMIN
│   ├── decisions
│   ├── owner_maps
│   ├── migration_notes
│   └── change_logs
├── 01_REPO
│   └── hyperrealism-system-repo
├── 02_COMFYUI_RUNTIME
│   ├── ComfyUI
│   ├── custom_nodes
│   ├── user
│   └── runtime_config
├── 03_MODELS
│   ├── checkpoints
│   ├── unet
│   ├── clip
│   ├── vae
│   ├── controlnet
│   ├── ipadapter
│   ├── upscale_models
│   └── video_models
├── 04_LORAS
│   ├── sdxl
│   ├── flux
│   ├── pony
│   ├── sd15
│   ├── rejected_or_superseded
│   └── quarantine
├── 05_WORKFLOWS
│   ├── 00_CANONICAL_MAIN_FLOW
│   ├── 01_IMAGE_BASE
│   ├── 02_IMAGE_REFINE
│   ├── 03_MASK_INPAINT
│   ├── 04_CONTROL_POSE_DEPTH
│   ├── 05_VIDEO_GIF
│   ├── 06_AUDIO
│   ├── 07_APP_MODE_TOOLS
│   ├── 08_QA_VALIDATION
│   ├── 09_EXPERIMENTS
│   └── 10_ARCHIVED
├── 06_REFERENCE_ASSETS
│   ├── images
│   ├── videos
│   ├── masks
│   ├── control_maps
│   ├── depth
│   ├── openpose
│   ├── ipadapter_refs
│   └── audio_refs
├── 07_GENERATED_OUTPUTS
│   ├── previews
│   ├── final_images
│   ├── video
│   ├── audio
│   ├── contact_sheets
│   └── rejected
├── 08_QA_EVIDENCE
│   ├── image
│   ├── video
│   ├── audio
│   ├── app_mode
│   ├── ec2
│   └── release
├── 09_MANIFESTS
│   ├── file_catalogs
│   ├── workflow_manifests
│   ├── model_manifests
│   ├── lora_manifests
│   ├── qa_manifests
│   └── release_manifests
├── 10_LOGS
│   ├── local
│   ├── comfyui
│   ├── validation
│   ├── ec2
│   └── release
├── 11_BACKUPS
│   ├── repo_snapshots
│   ├── workflow_snapshots
│   ├── registry_snapshots
│   └── pre_migration_snapshots
├── 12_EC2_SYNC_STAGING
│   ├── upload_manifest
│   ├── required_models
│   ├── required_loras
│   ├── required_workflows
│   ├── required_inputs
│   ├── runtime_scripts
│   ├── expected_outputs
│   └── pullback_artifacts
├── 13_APP_MODE
│   ├── apps
│   ├── controls
│   ├── presets
│   ├── profiles
│   ├── examples
│   ├── screenshots
│   └── release_exports
└── 14_RELEASES
    ├── candidate_releases
    ├── certified_releases
    ├── handoff_packets
    └── archived_releases
```
