# ComfyUI Object Info and Node Visibility Strategy

## Purpose

ComfyUI workflow JSON can reference node types that are not installed in the runtime. Wave 03 prevents that from slipping through by requiring `/object_info` proof.

## What `/object_info` proves

A captured object info snapshot proves:

- the runtime is reachable,
- ComfyUI is serving API metadata,
- required node class names are registered,
- custom node packages are installed enough to expose node definitions.

## What `/object_info` does not prove

It does not prove:

- model files exist,
- model files load,
- VRAM is sufficient,
- the workflow will render successfully,
- image quality is good,
- the output satisfies hyper-realism QA.

Those are later runtime and creative QA layers.

## Required object info workflow

```text
Start local ComfyUI
→ run collect_comfyui_object_info.py
→ save object_info_snapshot.json
→ run validate_object_info_against_workflows.py
→ fix missing node classes before EC2 render proof
```

## Node visibility statuses

| Status | Meaning |
|---|---|
| `VISIBLE_LOCAL` | Node exists in local `/object_info`. |
| `MISSING_LOCAL` | Node is required by workflow but absent locally. |
| `VISIBLE_EC2` | Node exists in EC2 `/object_info`. |
| `EC2_ONLY` | Node is intentionally not mirrored locally. |
| `DEPRECATED_REPLACE` | Node should be replaced before production. |
| `BLOCKED_UNKNOWN_NODE` | Node is missing and no approved replacement exists. |

## Custom node handling

Every custom node used in production must have:

```text
node type
custom node package name
Git source or install source
local install status
EC2 install status
object_info visibility proof
workflow(s) using it
fallback/replacement plan
```

## Promotion gate

No workflow module may be promoted unless every production node type is visible in at least one approved runtime environment.
