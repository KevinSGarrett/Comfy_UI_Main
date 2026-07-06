# Wave 04 — Note-Only and Staged Boundary Review

## Purpose

The current Main Flow contains several areas that are easy to mistake for completed features. Wave 04 explicitly separates them.

## Boundary categories

### Reference / IPAdapter / ControlNet staging

Current meaning:

- The graph contains staged reference/control lanes.
- Some image-reference/control functionality exists as smoke wiring.
- Additional reference-slot routing, pose/depth/OpenPose, and regional control remain not fully proven.

Required future action:

- Convert into named modules.
- Add runtime input contracts.
- Add control map generation.
- Add per-character masks.
- Add QA and evidence output.

### Video/audio handoff boundary

Current meaning:

- The image flow saves outputs that can feed future video/audio flows.
- Video and audio are not merged/proven inside this Main Flow.

Required future action:

- Keep video/GIF as separate workflow/API modules.
- Keep audio as separate workflow/API modules.
- Add AV timeline manifests in later waves.

### True image-reference conditioning boundary

Current meaning:

- Current templates may load/name reference files.
- Actual reference pixels are not fully proven as driving generation in every lane.

Required future action:

- Require explicit reference image input.
- Require reference image hash.
- Require influence/proof metadata.
- Require before/after identity QA.

### QA/promotion boundary

Current meaning:

- The flow contains notes for file evidence and promotion.
- File decode QA exists conceptually, but creative QA is not proven.

Required future action:

- Build QA evidence exporters.
- Build creative QA gates.
- Require exact runtime outputs before promotion.
- Do not promote from notes or unrelated smoke outputs.

### LoRA library boundary

Current meaning:

- The LoRA library is embedded as disabled/disconnected graph nodes.
- It is a manifest-wired catalog, not active runtime logic.

Required future action:

- Migrate into registries.
- Select LoRAs by pass plan.
- Validate engine compatibility before use.
- Keep rejected/superseded assets disabled.
