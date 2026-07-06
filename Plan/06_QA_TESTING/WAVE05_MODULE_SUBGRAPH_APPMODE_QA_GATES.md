# Wave 05 — Module, Subgraph, and App Mode QA Gates

## Gate 1 — Module catalog parse

The module catalog must parse and contain:

- current-flow modules
- future target modules
- owner waves
- purpose statements
- input/output expectations
- QA requirements

Failure condition: module catalog missing or invalid JSON.

## Gate 2 — Current-flow lane extraction map

The extraction map must identify all current SaveImage terminal lanes and map each lane to a module.

Failure condition: SaveImage lane missing from extraction map.

## Gate 3 — App Mode control surface

The App Mode control surface must expose high-level controls and hide advanced/private controls.

Required exposed groups:

- project/runtime
- output mode
- scene/environment
- characters
- camera/framing
- engine/modules
- QA/promotion

Failure condition: raw model paths, API keys, AWS keys, GitHub token, or raw node patch maps are exposed as normal operator controls.

## Gate 4 — Orchestrator boundary

The docs must state that App Mode is not the brain. The orchestrator/pass planner is responsible for module sequence, reruns, and promotion.

Failure condition: docs imply App Mode alone can autonomously perform full multi-pass planning.

## Gate 5 — Subgraph strategy

The subgraph plan must separate good subgraph candidates from modules that should remain API workflow templates.

Failure condition: the entire Main Flow is proposed as one production subgraph.

## Gate 6 — Template contract

Every module in the module catalog must have a matching workflow template contract entry.

Failure condition: module without a template contract.

## Gate 7 — Runtime proof boundary

Wave 05 must not claim runtime proof for modules not executed in local/EC2 ComfyUI.

Failure condition: validation report says production runtime proof is complete without actual generated outputs/evidence.

## Gate 8 — Source-canvas boundary

The current Main Flow must remain classified as a source/staging canvas.

Failure condition: docs treat it as final production architecture.
