# Wave 15 — Base Generation QA Gates

## Blocker gates

1. Output file exists and decodes.
2. Engine family, checkpoint family, and LoRA family match.
3. Scene Director plan was used.
4. Character count and body/crop constraints are not obviously violated.
5. Required reference/mask/control inputs were either supplied or explicitly not required.
6. Fallback reason is recorded if fallback was used.
7. Promotion manifest exists.

## Major gates

1. Image is not obviously blurry or corrupted.
2. Identity/environment drift is within tolerance.
3. No visible workflow artifacts, text, watermark, or UI residue.
4. Base image is viable for downstream detail/refine/video handoff.

## Gate outputs

- `pass`
- `rerun`
- `fallback`
- `block`
