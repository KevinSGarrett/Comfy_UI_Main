# Wave 46 Combined Migration and Implementation Execution Playbook

## Execution order
1. Freeze source packages.
2. Generate inventories.
3. Build source crosswalk.
4. Merge requirements into backlog.
5. Map backlog to canonical structure.
6. Create missing registries/schemas.
7. Validate catalog/search refresh.
8. Run local proof where possible.
9. Use EC2 only after preview/preflight gates.
10. Generate final handoff.

## Rule
Do not work from two separate plans. Work from the combined backlog and traceability graph.
