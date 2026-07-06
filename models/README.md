# models

Place local ComfyUI model files here when they are intentionally downloaded or copied for local use.

Recommended layout:

```text
models\
  checkpoints\
  loras\
  vae\
  controlnet\
  embeddings\
```

Model binaries are intentionally ignored by Git (`*.safetensors`, `*.ckpt`, `*.pt`, `*.pth`, `*.onnx`, `*.bin`, `*.gguf`). Any model added here still needs registry metadata, hash/path validation, and runtime QA evidence before it is considered usable.
