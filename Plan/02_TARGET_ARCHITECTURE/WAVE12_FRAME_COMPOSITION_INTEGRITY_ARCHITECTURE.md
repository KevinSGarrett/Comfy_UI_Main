# Wave 12 Architecture — Frame Composition Integrity

Wave 12 is the composition integrity layer. It prevents the system from promoting images or video frames that visually violate the requested shot.

## Problem this solves

Prompt text like “two people, full body, not cropped” is not enough. Image models can still create:

- The wrong number of characters.
- Extra background people.
- Merged or fused bodies.
- Cropped heads, hands, or feet.
- Full-body prompts that output half-body shots.
- Multi-character scenes where skeletons or limbs overlap incorrectly.
- Close-up shots where the wrong region is visible.

Wave 12 turns these requirements into measurable contracts.

## Architectural position

```text
User request
→ Wave07 LLM Scene Director
→ Wave08 Character Bible
→ Wave09 Environment/World Plan
→ Wave10 Camera/Framing Plan
→ Wave11 Pose/Control Map Plan
→ Wave12 Frame Composition Contract
→ Workflow compiler / engine router
→ ComfyUI output
→ Frame Composition Evidence
→ QA / promotion / repair
```

## Key rule

Frame integrity is not proven at prompt time. It is proven only after output evidence exists.
