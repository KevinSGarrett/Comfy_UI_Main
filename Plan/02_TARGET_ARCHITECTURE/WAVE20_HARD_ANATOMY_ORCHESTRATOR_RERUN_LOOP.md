# Wave 20 Hard Anatomy Orchestrator Rerun Loop

## Loop
1. detect failed hard-anatomy regions
2. compile crop/detail repair contract
3. execute low-denoise repair pass
4. score local anatomy
5. score global preservation
6. promote, rerun, fallback, or block

## Rerun limits
- Default maximum: 2 local reruns per region.
- Never rerun the entire image for a small local defect unless local repair repeatedly fails.
- Escalate to base/regional pass only when the crop lacks enough context.
