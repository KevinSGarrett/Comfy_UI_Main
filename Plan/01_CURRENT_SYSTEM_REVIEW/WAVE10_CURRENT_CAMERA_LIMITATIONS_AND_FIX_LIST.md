# Wave 10 Current Camera Limitations and Fix List

## Current Limitation: Prompt-Only Framing

A prompt can ask for “full body,” but the sampler may crop feet/hands or create inconsistent body scale.

### Fix

Use `camera_plan.shot_size`, `framing.must_not_crop`, and `qa_goals` as explicit control data.

## Current Limitation: Fixed Latent Sizes

The current Main Flow includes fixed latent nodes. This is useful for smoke proof, but not enough for adaptive camera framing.

### Fix

Workflow compiler must patch latent width/height from the camera plan.

## Current Limitation: Multi-Character Layout

Multi-character requests need subject slots, screen positions, depth order, and occlusion policy.

### Fix

Use `multi_character_composition.schema.json` and `wave10_multi_character_framing_rules.json`.

## Current Limitation: Lens Is Prompt-Like

A “35mm lens” in text is useful, but not a guaranteed optical model.

### Fix

Treat lens profile as a guidance/control abstraction, then verify output characteristics through QA.

## Current Limitation: Video Motion Is Separate

Still image camera planning is not the same as video camera motion.

### Fix

Video runtime lanes must consume the same camera plan plus camera-motion fields such as pan, tilt, dolly, zoom, orbit, lock-on, and stabilization.
