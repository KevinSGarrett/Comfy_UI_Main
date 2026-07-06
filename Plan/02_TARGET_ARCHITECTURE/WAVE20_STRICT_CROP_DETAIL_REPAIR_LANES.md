# Wave 20 Strict Crop/Detail Repair Lanes

## Why crop lanes are required
Hard anatomy often fails because the generator has insufficient local resolution or too many competing constraints. Crop/detail lanes increase local focus while preserving the approved global image.

## Lane types
- face crop repair lane
- eye crop repair lane
- mouth / teeth crop repair lane
- hand / finger crop repair lane
- foot / toe crop repair lane
- nail detail lane
- final seam-blend lane

## Crop rules
- Crop must include enough context for lighting and edge blending.
- Crop must not remove the region from its body/contact context.
- Repair must round-trip back into the approved full image.
- If crop repair improves the local area but damages global context, block promotion.
