# Wave 35 ComfyUI Runtime Structure

Recommended ComfyUI runtime boundary:

```text
ComfyUI/
├── custom_nodes/
├── input/
│   ├── references/
│   ├── masks/
│   ├── control_maps/
│   └── video_references/
├── models/
│   ├── checkpoints/
│   ├── loras/
│   ├── controlnet/
│   ├── vae/
│   ├── upscale_models/
│   ├── ipadapter/
│   └── video/
├── output/
│   ├── Main_Flow/
│   ├── previews/
│   ├── qa_evidence/
│   └── releases/
└── user/
    └── workflows/
```

## Rule
ComfyUI runtime folders are execution folders. Repo folders are source-of-truth folders.
