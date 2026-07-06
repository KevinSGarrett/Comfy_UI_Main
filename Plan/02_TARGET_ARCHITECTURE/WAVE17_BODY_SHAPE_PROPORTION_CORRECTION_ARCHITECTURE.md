# Wave 17 — Body Shape and Proportion Correction Architecture

## Purpose
This architecture turns body-shape requests into controlled correction passes. The goal is to fix stomach, waist, hips, thighs, silhouette, and overall body proportion while preserving identity, pose, camera framing, clothing, skin texture, and scene continuity.

## Position in the system

```text
User request
→ Scene Director
→ Character Bible / character_id
→ Frame Composition contract
→ Mask Factory
→ Body Shape Correction Contract
→ Orchestrator / pass planner
→ Engine Router / Refine Bridge
→ ComfyUI inpaint/refine execution
→ QA evidence
→ rerun/fallback/promote decision
```

## Body correction is not prompt-only
A prompt such as "make the waist smaller" is not enough. The system must compile it into structured data:

- target character,
- target body region,
- target profile,
- large mask,
- protected exclusions,
- denoise range,
- engine family,
- pass type,
- QA goals,
- fallback behavior.

## Main correction modes

### 1. Preserve existing body
Used when base image is already correct. This blocks accidental shape drift.

### 2. Subtle stomach/waist refine
Uses abdomen and waist masks with low denoise. This is the safest correction mode.

### 3. Hourglass proportion correction
Uses waist, hip, abdomen, and silhouette masks. It requires stronger QA because it changes the body outline.

### 4. Hip/thigh balance correction
Uses left/right thigh and hip masks. It must preserve stance and left/right proportion consistency.

### 5. Full silhouette repair
Repairs obviously broken, cropped, or merged silhouettes. This is high-risk and must be QA-gated.

## Hard boundaries
- Full-image redraw is blocked for body correction.
- Large body masks cannot include face identity regions.
- Body correction must be character-instance owned.
- Corrections cannot promote if the character count changes.
- Corrections cannot promote if the body merges with another person or prop.
- Corrections cannot promote if clothing/fabric no longer follows the corrected body.
