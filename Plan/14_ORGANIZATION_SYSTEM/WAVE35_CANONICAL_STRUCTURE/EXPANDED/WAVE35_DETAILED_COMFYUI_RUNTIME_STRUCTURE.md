# Wave 35 Detailed ComfyUI Runtime Structure

ComfyUI runtime should be treated as an execution environment.

```text
ComfyUI/
├── custom_nodes/
├── input/
│   ├── references/
│   ├── masks/
│   ├── control_maps/
│   ├── video_references/
│   ├── audio_references/
│   └── app_mode_inputs/
├── models/
│   ├── checkpoints/
│   ├── diffusion_models/
│   ├── unet/
│   ├── clip/
│   ├── vae/
│   ├── loras/
│   │   ├── sdxl/
│   │   ├── flux/
│   │   ├── pony/
│   │   └── sd15/
│   ├── controlnet/
│   ├── ipadapter/
│   ├── upscale_models/
│   └── video/
├── output/
│   ├── Main_Flow/
│   ├── previews/
│   ├── contact_sheets/
│   ├── app_mode/
│   ├── qa_evidence/
│   ├── release_candidates/
│   └── archive/
└── user/
    ├── workflows/
    │   ├── canonical/
    │   ├── experiments/
    │   └── archive/
    └── default/
```

## Runtime rule

Runtime folders are allowed to contain generated outputs and active execution files. Repo folders are not.
