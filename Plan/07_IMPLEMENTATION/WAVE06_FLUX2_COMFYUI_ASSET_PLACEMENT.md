# Wave 06 Flux2 ComfyUI Asset Placement

## Principle
Do not guess model locations at runtime. Put every Flux2 asset in the model manifest with exact path, source, hash, and promotion status.

## Local layout proposal
```text
C:\Comfy_UI_Main\models\flux2\
  dev\
    diffusion_models\
    text_encoders\
    vae\
    workflows\
    manifests\
  klein\
    diffusion_models\
    text_encoders\
    vae\
    workflows\
    manifests\
```

## ComfyUI native model layout bridge
If ComfyUI requires standard folders, use either direct placement or symlinks/junctions:

```text
ComfyUI\models\diffusion_models\
ComfyUI\models\text_encoders\
ComfyUI\models\vae\
```

## S3 layout proposal
```text
s3://<MODEL_BUCKET>/models/flux2/dev/
s3://<MODEL_BUCKET>/models/flux2/klein/
s3://<MODEL_BUCKET>/manifests/flux2/
s3://<MODEL_BUCKET>/proofs/flux2/
```

## EC2 layout proposal
```text
/opt/ComfyUI/models/flux2/dev/
/opt/ComfyUI/models/flux2/klein/
/opt/ComfyUI/Implementation/manifests/flux2/
```

## Hydration policy
Hydrate only the exact required Flux2 files for a route:

```text
flux2_dev_local route
→ hydrate dev diffusion model
→ hydrate dev text encoder
→ hydrate dev VAE
→ hydrate workflow template
→ run proof
```

Do not sync the entire model bucket to EC2.

## Required proof files
```text
Implementation/manifests/flux2/
  object_info_snapshot.json
  model_path_proof.json
  model_load_proof.json
  smoke_output_manifest.json
  visual_qa_report.json
  promotion_decision.json
```

## Promotion
Flux2 stays disabled in the router until `promotion_decision.json` explicitly marks the specific variant as allowed for the specific pass type.
