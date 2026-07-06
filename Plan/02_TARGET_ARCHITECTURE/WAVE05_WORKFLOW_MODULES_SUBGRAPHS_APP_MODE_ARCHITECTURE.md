# Wave 05 — Workflow Modules, Subgraphs, and App Mode Architecture

## Executive decision

The best architecture is **not** one giant monolithic ComfyUI graph. The system should use a controlled collection of small reusable workflow modules, packaged as subgraphs where useful, and executed by an external pass planner/orchestrator.

## Why the current giant-flow pattern must change

The current Main Flow is useful because it contains executable lanes, staged lanes, notes, catalog nodes, and promotion boundaries. It is not ideal as the final production runtime for these reasons:

1. It mixes active generation lanes with catalog/reference-only LoRA nodes.
2. It uses notes to represent future systems such as video/audio handoff and deeper pose/depth/OpenPose support.
3. It contains multiple SaveImage terminal outputs that should become separate workflow templates.
4. It has disabled LoRA library nodes that must remain catalog references, not runtime nodes.
5. It is difficult for an AI project manager to patch safely without a formal contract per module.
6. It is difficult to run strict QA because one large canvas hides what actually affected the output.

## Target architecture

```text
Operator / AI PM request
        ↓
App Mode control surface
        ↓
Scene Director Bridge
        ↓
Pass Planner / Orchestrator
        ↓
Engine Router + Asset Compatibility Gate
        ↓
Workflow Template / Subgraph Module
        ↓
Runtime Output
        ↓
QA Evidence Export
        ↓
Promotion Gate
```

## Module types

### 1. Operator modules

These modules collect intent, scene structure, runtime target, QA strictness, camera/framing, characters, and output mode.

Examples:

- App Mode operator surface
- Scene Director bridge
- Camera/framing request parser
- Environment preset selector

### 2. Engine/runtime modules

These modules actually render or transform outputs.

Examples:

- SDXL/RealVisXL base lane
- Z-Image base lane
- SDXL inpaint/detail lane
- Image bridge/refine lane
- Upscale/export lane
- IPAdapter face/reference lane
- ControlNet Canny lane

### 3. Control/mask modules

These modules create structured guidance assets for runtime modules.

Examples:

- Mask Factory
- Pose/depth/control maps
- Camera/framing map planner
- Person-instance separation
- Contact-zone masks

### 4. Specialist hyper-realism modules

These modules should never run globally by default. They must run using masks, crops, or controlled low-denoise passes.

Examples:

- Body shape correction
- Skin/material detail
- Hard anatomy detail
- Soft-body contact/deformation
- Multi-character interaction

### 5. Output continuity modules

These modules turn still-image logic into GIF/video/audio/AV outputs.

Examples:

- GIF/video keyframe planner
- Video engine router
- Temporal QA and frame repair
- Audio scene generation
- Pose-to-audio force planner
- AV sync and spatial audio

### 6. QA/promotion modules

These modules are the authority for whether outputs can be used.

Examples:

- Static workflow validation
- Object-info visibility proof
- Model reference validation
- Runtime evidence manifest
- Crop QA
- Creative QA
- Temporal QA
- Promotion gate

## Subgraph usage rules

Use subgraphs for node groups that are stable, reusable, and not expected to be frequently patched by the orchestrator at dozens of points.

Good subgraph candidates:

- Mask Factory operations
- Upscale/export
- Evidence manifest writing
- Pose/depth preprocessing
- Reference image preparation
- Local inpaint wrapper
- QA crop export

Do not prematurely subgraph:

- Experimental prompt-routing systems
- In-progress engine-router logic
- Anything with unresolved node availability
- Disabled LoRA catalog libraries
- Model paths that are still being reconciled from S3/Civitai/EC2

## Workflow template usage rules

Use API workflow templates when the orchestrator must patch many values at runtime.

Good API-template candidates:

- Base generation lane
- Refine lane
- Inpaint/detail lane
- Video frame generation lane
- Audio generation lane
- Per-character/multi-character passes

## App Mode usage rules

App Mode should expose high-level inputs only:

- output type
- scene/environment
- character count
- shot type
- camera/lens/zoom/depth
- primary engine profile
- enabled pass types
- QA level
- runtime target
- export formats

App Mode should hide:

- raw model paths
- raw LoRA paths
- API tokens
- AWS/EC2 details
- prompt patch internals
- node ID maps
- sampler internals unless explicitly exposed in expert mode

## AI project manager instructions

The AI project manager must:

1. Read the module catalog.
2. Select the smallest module needed.
3. Validate module inputs.
4. Patch a workflow template.
5. Run local static validation.
6. Run local ComfyUI runtime validation if available.
7. Only start EC2 when a GPU proof is required.
8. Collect output evidence.
9. Run QA gates.
10. Promote or block based on evidence, not assumptions.
