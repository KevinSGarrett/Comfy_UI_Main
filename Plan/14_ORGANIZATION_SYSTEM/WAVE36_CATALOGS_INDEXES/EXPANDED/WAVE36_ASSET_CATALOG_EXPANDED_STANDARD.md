# Wave 36 Asset Catalog Expanded Standard

The asset catalog tracks heavy and reference assets.

## Asset classes

- checkpoint
- diffusion model / UNet
- CLIP
- VAE
- LoRA
- ControlNet
- IPAdapter
- upscaler
- reference image
- reference video
- mask
- control map
- depth map
- pose map
- audio reference
- prompt/profile

## Required fields

- asset_id
- asset_type
- engine_family
- category
- owner_domain
- canonical_path
- runtime_path
- source_of_truth_role
- size_bytes
- sha256 when available
- compatibility
- required_by_workflows
- proof_status
- archive_status
- tags

## Rule

Heavy asset files can live locally/runtime, but their metadata must be cataloged.
