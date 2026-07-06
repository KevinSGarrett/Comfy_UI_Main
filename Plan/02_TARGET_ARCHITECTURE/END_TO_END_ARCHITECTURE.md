# End-to-End Target Architecture

## Recommended strategy

Build multiple connected workflows/modules, not one giant flow.

```text
User / App Mode controls
  ↓
Scene request schema
  ↓
AI pass planner
  ↓
Engine router
  ↓
Character bible + scene graph
  ↓
Mask factory + control-map factory
  ↓
ComfyUI workflow module execution
  ↓
QA evaluator
  ↓
Rerun/repair/promotion decision
  ↓
Still image, GIF/video, audio, AV sync package
```

## Major layers

### 1. App / input layer

Collect high-level intent:
- output type: still, GIF, video, audio, full AV scene
- character count
- character references
- body/skin/fabric/detail targets
- pose and camera references
- interaction/contact targets
- video duration and motion style
- audio/dialogue/SFX needs
- engine preference or auto routing

### 2. Planner layer

Converts request into structured plan:
- scene graph
- characters
- references
- required passes
- engine choices
- masks needed
- control maps needed
- QA gates
- rerun rules

### 3. Execution layer

Runs modular ComfyUI workflows:
- base image generation
- refine
- inpaint/detail
- body-shape correction
- hands/face detail
- contact deformation
- video/GIF keyframes
- frame repair
- audio requests
- sync/mix timeline

### 4. Evidence layer

Stores:
- input request
- workflow hash
- model/LoRA selection
- masks/control maps
- output images/frames/audio
- crops/contact sheets
- QA manifest
- promotion decision

### 5. QA layer

Blocks failures:
- wrong character count
- wrong pose/camera
- merged characters
- identity drift
- hand/finger failures
- body-shape mismatch
- mask bleed
- contact/collision failure
- temporal flicker
- audio sync/clipping/lip-sync failure

## Core rule

Every specific visual target must have a matching evidence artifact. If the request asks for cellulite on thighs, there must be a thigh mask, an output, a thigh crop, and a QA result proving the detail stayed on the thighs.
