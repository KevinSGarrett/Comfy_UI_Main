# ADR-W64-HVAA-001: Hybrid Controller Console and ComfyUI App Mode Surfaces

**Status:** Proposed for main-task adoption
**Date:** 2026-07-16

## Context

The system must coordinate characters, scenes, shots, masks, image/video/audio
passes, exact models, workers, QA, repairs, and releases across many workflows.
ComfyUI App Mode is optimized for selected inputs/outputs of one workflow.

## Decision

Use a standalone local controller console as the primary application, small App
Mode workflow launchers for focused execution, and an optional frontend
extension for diagnostic/deep-link integration.

## Options considered

| Option | Multi-workflow state | ComfyUI integration | Complexity | Decision |
|---|---:|---:|---:|---|
| One giant App Mode graph | poor | native | deceptively high | reject |
| Frontend extension only | medium | deepest | high coupling | reject as sole UI |
| Standalone controller only | excellent | indirect | medium | incomplete alone |
| Hybrid console + App Mode + optional extension | excellent | strong | highest initial scope | accept |

## Consequences

- Durable state and promotion remain outside ComfyUI.
- Workflow authors retain focused App Mode experiences.
- The project must version a controller API and projection model.
- Some UI concepts exist in two surfaces, so a generated binding registry and
  contract tests are mandatory.
- Frontend-extension changes cannot break core controller operation.
