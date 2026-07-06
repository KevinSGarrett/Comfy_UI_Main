# Wave 06 Engine Promotion Lifecycle

## Promotion states
| State | Meaning |
|---|---|
| `catalog_only` | Known asset or engine, not installed/proven |
| `path_verified` | File path exists, but model not proven in runtime |
| `object_info_visible` | Required ComfyUI nodes are visible |
| `model_load_verified` | Model loads without runtime error |
| `smoke_output_verified` | Tiny test output generated and hashed |
| `qa_candidate` | Output exists and can be visually compared |
| `production_candidate` | Can be used in controlled production test runs |
| `production_approved` | May be selected by router automatically |
| `blocked` | Must not be selected |
| `rejected_or_superseded` | Kept for traceability only |

## Engine promotion checklist
An engine may move to `production_candidate` only after:

1. Model metadata exists.
2. Required files are in the model registry.
3. Required files are in S3 or local cache as expected.
4. Required ComfyUI nodes are visible in `/object_info`.
5. The workflow template validates.
6. The model loads.
7. A smoke output is created.
8. Output is saved with SHA256.
9. QA manifest is recorded.
10. Visual review does not show unacceptable failure for the pass type.
11. Cost/runtime is acceptable for the intended tier.

## Router enforcement
The router must never select:

- `catalog_only`
- `path_verified` for production
- `blocked`
- `rejected_or_superseded`
- any route without exact engine-family compatibility
- any route whose required files are missing
- any route with stale object_info proof after a ComfyUI/custom-node update

## EC2 cost control
EC2 should only be turned on when:

- local validation passes
- exact engine candidate is identified
- exact asset hydration manifest exists
- exact workflow template exists
- expected output and QA task are defined

EC2 should not be used for broad search, model guessing, or random LoRA stack exploration.
