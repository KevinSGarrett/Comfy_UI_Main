# Wave 06 Engine Router QA Gates

## Gate 1 — Registry validity
Pass only if:
- every engine has an `engine_id`
- every engine has a `family`
- every engine has a promotion state
- every engine lists compatible LoRA families
- every engine lists required assets or asset placeholders
- every engine has a route role

## Gate 2 — Compatibility validation
Pass only if:
- selected checkpoint family matches engine family
- selected LoRA family matches engine family
- no blocked/rejected assets are selected
- no untagged Civitai model is selected
- no cross-engine latent/model bridge exists

## Gate 3 — Local static validation
Pass only if:
- workflow JSON validates
- registry JSON validates
- paths resolve to placeholders or real files
- `.env` variables required for the engine are present
- route request produces deterministic route decision

## Gate 4 — object_info validation
Pass only if:
- ComfyUI `/object_info` contains required node classes
- object_info snapshot hash is recorded
- custom node versions are recorded

## Gate 5 — model load proof
Pass only if:
- checkpoint loads
- text encoder loads
- VAE loads
- ControlNet/IPAdapter/video/audio nodes load where applicable

## Gate 6 — output proof
Pass only if:
- workflow submits
- output file is created
- output file is non-empty
- output file is decodable
- output file hash is recorded

## Gate 7 — visual/audio/temporal QA
Pass only if:
- output satisfies the pass-specific visual target
- no identity drift beyond threshold
- no engine bridge corruption
- no invalid anatomy/contact artifacts for the target pass
- no video flicker/drift for video lanes
- no clipping/sync failure for audio lanes

## Gate 8 — promotion
Pass only if:
- all evidence records exist
- route decision is reproducible
- manifest promotion script marks route as allowed
- no upstream mutable source contradicts the registry
