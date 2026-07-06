# Wave 40 Domain Contracts and Dependencies

## Required domain contracts

- planning domain
- implementation domain
- workflow domain
- runtime domain
- QA domain
- catalog/search domain
- release/handoff domain

## Dependency rule

A downstream domain cannot promote unless upstream domains have valid status.

Example:

```text
workflow bridge → requires source intake + crosswalk + architecture owner
runtime proof → requires workflow bridge + preview/preflight gates
release handoff → requires QA evidence + traceability + validation
```
