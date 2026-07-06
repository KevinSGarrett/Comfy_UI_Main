# Wave 35 Model, LoRA, and Asset Boundary Policy

## Heavy asset rule

Heavy model assets belong in local/runtime storage, not the git repo.

## Model folders

```text
03_MODELS/
├── checkpoints/
├── unet/
├── clip/
├── vae/
├── controlnet/
├── ipadapter/
├── upscale_models/
└── video_models/
```

## LoRA folders

```text
04_LORAS/
├── sdxl/
├── flux/
├── pony/
├── sd15/
├── rejected_or_superseded/
└── quarantine/
```

## Asset rule

Every large asset must have a registry record before being used by a canonical workflow.
