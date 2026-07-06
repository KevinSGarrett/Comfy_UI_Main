# Wave 03 Runtime Inventory and Validation Harness Architecture

## Architecture decision

Wave 03 establishes a **three-layer validation model**:

```text
Layer 1 — Offline static validation
Layer 2 — Local runtime visibility validation
Layer 3 — EC2 GPU runtime proof
```

The AI project manager must always use the cheapest valid layer first.

## Layer 1 — Offline static validation

Runs with EC2 off and ComfyUI not running.

Checks:

- JSON parse
- required top-level workflow fields
- node IDs
- link IDs
- source/target node existence
- source/target slot ranges
- declared link type consistency
- terminal outputs
- upstream dependency graph
- disabled/catalog nodes
- model reference extraction
- JSON registry parsing
- `.env` key presence without printing secrets

Layer 1 catches broken workflow structure before any GPU cost.

## Layer 2 — Local runtime visibility validation

Runs with local ComfyUI running on the workstation.

Checks:

- `/object_info` reachable
- every workflow node type exists in the local runtime
- custom nodes are installed
- ComfyUI can see expected node classes
- API base URL is correct
- local runtime is close enough to validate API JSON compilation

Layer 2 still avoids EC2 cost.

## Layer 3 — EC2 GPU runtime proof

Runs only after Layer 1 and Layer 2 pass or after local GPU limits are reached.

Checks:

- required model files hydrate from S3 to EC2
- ComfyUI model folders resolve
- selected checkpoint/LoRA/VAE/control/upscale files load
- required workflow modules generate concrete output files
- output manifests prove dimensions, hash, path, and decoder validity
- later waves add visual/creative QA

Layer 3 is expensive and should not be used for basic syntax, graph, registry, or metadata checks.

## Required local manifest outputs

Every local validation run must write to:

```text
Implementation/manifests/wave03_local_validation/
```

Required outputs:

```text
workflow_graph_validation_report.json
terminal_outputs.csv
node_type_counts.csv
model_references.csv
json_registry_parse_report.json
env_validation_report.json
object_info_validation_report.json
wave03_validation_manifest.json
```

Some outputs are conditional. For example, `object_info_validation_report.json` only exists after a local or EC2 ComfyUI `/object_info` snapshot has been captured.

## Object info proof

A workflow node type is not production-valid until it is visible in the actual runtime:

```text
workflow node type
→ must exist in /object_info
→ must match expected input/output fields enough to compile the API workflow
```

This prevents the AI project manager from assuming a custom node exists just because a workflow JSON references it.

## Model reference proof

A model reference is not production-valid until it is one of:

```text
PASS_LOCAL_FILE_FOUND
WARN_REGISTRY_HIT_LOCAL_HYDRATION_REQUIRED
PASS_EC2_FILE_FOUND
PASS_S3_CANONICAL_OBJECT_FOUND
```

A raw filename in a workflow is not enough.

## Registry proof

All JSON registries must parse before runtime:

```text
engine registry
model registry
asset compatibility registry
pass planner schema
mask taxonomy
camera/frame schema
Civitai metadata registry
release manifests
QA manifests
```

Invalid registry JSON blocks promotion.

## Tracker and Plans ZIP boundary

The tracker CSV and Plans ZIP are ongoing upstream sources. Wave 03 inventories them but does not freeze them.

Future waves must re-ingest them when they are updated.
