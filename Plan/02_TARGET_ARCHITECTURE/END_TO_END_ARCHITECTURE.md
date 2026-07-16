# End-to-End Target Architecture

## Recommended strategy

Build multiple connected workflows/modules, not one giant flow.

The complete character-to-image-to-video-to-audio composition contract is defined in:

`Plan/02_TARGET_ARCHITECTURE/MODULAR_CHARACTER_TO_MULTIMODAL_MEDIA_ORCHESTRATION_ARCHITECTURE.md`

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

## Authority and deployment boundaries

The machine-readable boundary contract is:

`Plan/10_REGISTRIES/end_to_end_architecture_boundary_registry.json`

| Domain | Authority | Interface contract |
|---|---|---|
| Local project | `C:\Comfy_UI_Main` | Owns the execution ledger, orchestration source, tracker/items, hydration, and final decisions. |
| GitHub | `origin/main` | Stores code, workflows, schemas, registries, tests, and lightweight evidence only; mutation and push remain a guarded Codex action. |
| S3 | Hash-bound object manifests | Stores selected model/runtime binaries and deploy artifacts; it does not own planning state. |
| EC2 | Approved on-demand GPU worker | Hydrates only selected assets, runs an explicitly gated proof, returns hashes/logs/outputs, and stops. Its workspace is not planning authority. |
| Model registry | `Plan/Registries/Models/model_registry.jsonl` | Resolves exact model identity, license, source, SHA256, cache targets, compatibility, and validation state before hydration. |
| Workflow lanes | Runtime queue plus `Workflows/base_generation/ACTIVE_LANES.json` | Selects one bounded lane with exact workflow, inputs, models, gates, and promotion rule. |
| QA evidence | `Plan/Instructions/QA/Evidence` with Tracker mirrors | Records static, runtime, artifact, visual/audio, blocker, and rerun decisions without treating existence as a pass. |
| Release gate | Release decision plus current release manifest | Fails closed when required runtime, QA, manifest, or unresolved-failure proof is missing. |
| Done certification | Done-certification protocol and record | Requires implementation, tests, QA, inspection, ledger updates, known-issue review, and a final scoped decision. |

## Cross-boundary execution contract

1. A local request compiles to a pass plan and one selected workflow lane.
2. The lane resolves exact registry assets and hashes before any transfer or runtime action.
3. GitHub supplies versioned lightweight source; S3 supplies only selected hash-bound binaries or bundles.
4. EC2 may start only after local, Git, authentication, budget, TTL, emergency-stop, input, model, workflow, and pullback gates pass.
5. Runtime outputs return to local evidence with request, commit, workflow, model, input, output, and log hashes.
6. QA evaluates the complete scoped artifact and records pass, conditional pass, repair, or blocker.
7. Release promotion requires the current manifest and all required proof for the same scope.
8. Done certification is scoped and cannot imply lane, route, wave, or project completion beyond its evidence.

## Fail-closed rules

- Local state wins when local, EC2, S3, or legacy copies disagree.
- No model binary is committed to Git and no full model library is hydrated by default.
- No stale EC2 workspace, candidate mask, historical release pack, or existence-only evidence may authorize promotion.
- Missing authentication, hash, transform, runtime, visual/audio QA, pullback, stopped-state, release, or certification proof blocks only the dependent action and leaves unrelated safe local work available.
