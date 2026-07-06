# Wave 17 Delivery Report

## Delivered
Wave 17 adds a complete body-shape and proportion correction layer.

## Major additions
- Body region taxonomy for stomach, waist, hips, thighs, silhouette, clothing boundary, and protected regions.
- Body proportion target profiles.
- Large-mask correction rules.
- Same-engine LoRA selection constraints.
- Body correction pass profiles.
- QA scoring rules.
- Drift/failure taxonomy.
- Rerun policy.
- App Mode body controls.
- Main Flow body-shape inventory.
- JSON schemas, examples, and validation scripts.

## Non-goals
Wave 17 does not claim that the body-correction runtime is already promoted. It creates the control layer and proof gates. Actual runtime proof still requires ComfyUI output artifacts.

## Promotion requirement
No body-shape correction result may promote unless it passes body target improvement, identity preservation, pose preservation, character count, mask edge, crop boundary, clothing/fabric continuity, and skin texture continuity QA.

## Validation summary

```text
Files before ZIP: 971
JSON files checked: 434
Python scripts present: 87
Main Flow nodes observed: 356
Mask input slots observed: 2
Low-denoise anchors observed: 2
Body-shape LoRA signals: 37
Tracker body-shape related rows: 243
Validation: PASS
```
