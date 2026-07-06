# Wave 03 Strict QA Gates

## QA purpose

Wave 03 validates structure and runtime readiness. It does not validate final artistic quality.

## Gate 03.1 — Workflow JSON parse

**Pass condition**

- Workflow JSON loads with Python standard `json`.
- Top-level `nodes` and `links` fields exist.
- Node count and link count are reported.

**Fail condition**

- JSON cannot parse.
- Workflow is missing required core fields.

## Gate 03.2 — Graph integrity

**Pass condition**

- Every link source node exists.
- Every link target node exists.
- Every source slot is in range.
- Every target slot is in range.
- Every node input link reference exists.
- Every node output link reference exists.

**Warning condition**

- Declared link type differs from source/target type but ComfyUI may tolerate it.

**Fail condition**

- Missing node/link/slot reference.

## Gate 03.3 — Terminal output inventory

**Pass condition**

- Every SaveImage/PreviewImage node is inventoried.
- Upstream sampler IDs are identified.
- Terminal nodes are marked enabled/disabled.

**Fail condition**

- No enabled terminal output exists for a production workflow module.

## Gate 03.4 — Active vs staged boundary

**Pass condition**

- Nodes not upstream of enabled outputs are not mistaken for production-active nodes.
- Disabled/catalog LoRA nodes remain disabled unless explicitly selected by a future pass router.

**Fail condition**

- AI project manager claims a staged/catalog node is production-active without reachability proof.

## Gate 03.5 — Model reference inventory

**Pass condition**

- All workflow asset references are extracted.
- References include node ID, node type, asset filename/path, and known engine/category metadata.

**Fail condition**

- Workflow contains untracked model references.
- Referenced model cannot be found locally, in registry, in S3 manifest, or in a hydrate-required manifest.

## Gate 03.6 — Registry parse

**Pass condition**

- Every JSON registry/manifest/schema file parses.
- Invalid JSON blocks promotion.

## Gate 03.7 — `.env` readiness

**Pass condition**

- Required keys are present.
- Secrets are never printed in logs.
- `.env.example` exists.
- real `.env` is excluded from Git.

## Gate 03.8 — Object info node visibility

**Pass condition**

- Runtime `/object_info` snapshot is captured.
- Every production workflow node type is visible.

**Blocked condition**

- No local or EC2 runtime was queried yet.

**Fail condition**

- Required production node type is missing from the runtime.

## Gate 03.9 — EC2 cost gate

**Pass condition**

- EC2 remains off until local validation is complete.
- EC2 starts only with a minimal required model hydration list and a stop-after-run plan.

## Gate 03.10 — Release manifest

**Pass condition**

- Wave 03 creates `WAVE03_VALIDATION_REPORT.json`.
- Report clearly separates static PASS from runtime proof still required.
