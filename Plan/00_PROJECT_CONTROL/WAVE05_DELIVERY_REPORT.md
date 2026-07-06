# Wave 05 Delivery Report

## Delivered wave

**Wave 05 — Workflow modules, subgraphs, App Mode**

## Goal

Convert the giant/source Main Flow into reusable module contracts and define the clean App Mode control surface that operators or an AI project manager can use without editing raw nodes.

## What was added

- Module catalog for current-flow executable/staged lanes and future hyper-realism modules.
- App Mode operator control surface registry.
- Workflow template contract registry.
- Module extraction map.
- Subgraph/module architecture document.
- App Mode/operator boundary document.
- Workflow API JSON template strategy.
- Module extraction implementation manual.
- QA gates for module, subgraph, App Mode, and orchestrator separation.
- Schemas for module contracts, App Mode controls, workflow template contracts, and subgraph blueprints.
- Starter module template examples.
- Validation scripts and PowerShell wrapper.

## Current classification

The current Main Flow remains a **source/staging canvas**. Wave 05 defines how it must be split into smaller modules. It does not yet rewrite the actual ComfyUI workflow into final production subgraphs.

## Critical locked decision

The correct architecture is:

```text
App Mode = operator control panel
External orchestrator/pass planner = brain
ComfyUI workflow templates/subgraphs = execution modules
QA/promotion gate = final authority
```

App Mode should not be expected to decide pass order, reruns, or final promotion by itself.
