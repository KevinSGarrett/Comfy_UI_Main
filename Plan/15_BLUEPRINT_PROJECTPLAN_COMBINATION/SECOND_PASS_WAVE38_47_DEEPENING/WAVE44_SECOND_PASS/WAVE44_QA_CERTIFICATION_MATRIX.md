# Wave 44 QA Certification Matrix

## QA certification layers

| Layer | Purpose | Release impact |
|---|---|---|
| structure_QA | validates folders/docs/schemas | required |
| catalog_QA | validates catalogs/search/stale-index | required |
| workflow_QA | validates workflow mapping | required before runtime |
| preview_QA | validates low-cost preview | required before final render |
| runtime_QA | validates output artifacts | required for runtime proof |
| state_diff_QA | compares planned vs generated state | required for promotion |
| release_QA | final certification | required for handoff |

## Rule

QA certificates must link to evidence, not just written claims.
