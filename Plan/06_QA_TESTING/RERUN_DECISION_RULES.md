# Rerun and Repair Decision Rules

## Base failures

- Wrong character count → rerun base/layout.
- Wrong pose/camera → rerun base with stronger pose/depth/control.
- Wrong body orientation → rerun base.
- Major identity failure → rerun base or identity reference pass.

## Shape failures

- Stomach/waist/hips wrong but pose is good → large-mask body-shape pass.
- Body edit creates chopped seam → larger mask, more feathering, lower/adjusted denoise, depth/edge guidance.

## Detail failures

- Detail absent → rerun small/medium masked detail pass.
- Detail bleeds → reduce mask, lower LoRA strength, lower denoise.
- Detail over-sharp/plastic → lower denoise/strength, adjust prompt/model.

## Hands

- Rough hand but attached/readable → hand detail pass.
- Hand merged with body or contact impossible → contact pass or base rerun depending severity.
- Extra/missing fingers after repair → rerun hand pass with stricter crop/control.

## Multi-character

- Wrong count/merged bodies → rerun layout/base.
- One character identity wrong → per-character mask identity correction.
- Cross-character bleed → fix masks/reference isolation and rerun affected pass.

## Video/GIF

- One bad frame → local frame repair.
- Many drifting frames → regenerate clip/keyframe sequence.
- Contact inconsistent across frames → rebuild contact masks and keyframes.

## Audio

- Wrong speaker/timing → rebuild audio timing manifest.
- Foley not aligned → adjust cue timeline.
- Lip-sync wrong mouth → fix character/mouth binding.
