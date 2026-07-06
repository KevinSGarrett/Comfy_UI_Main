# Wave 06 Delivery Report

## Delivered
Wave 06 adds the engine registry and router blueprint for the cumulative 35-wave hyperrealism system.

## What changed
- Flux2 added as a planned first-class image/editing engine family.
- Flux2 dev and Flux2 klein variants defined separately.
- Optional Flux2 API variants isolated behind API/cost gates.
- Current Flux1, SDXL/RealVisXL, Pony, SD1.5, and Z-Image roles clarified.
- Video engines separated from image engines.
- Audio/AV engines separated from silent video engines.
- Qwen-Image, SD3.5, and HunyuanImage-style candidates placed into review rather than blindly added.
- Strict cross-engine compatibility rules added.
- Model/LoRA routing now requires engine family, checkpoint family, asset metadata, promotion state, and runtime proof.

## Why this matters
Without an engine router, the system can easily load the wrong LoRA into the wrong model family, bridge incompatible latents, promote note-only lanes, or waste EC2 time on runs that could have failed locally. Wave 06 prevents that by making routing a registry decision instead of a prompt guess.

## Result
Wave 06 is ready for Wave 07, where the LLM Scene Director will use this registry to turn user requests into structured engine/pass plans.
