# Wave 34 Orchestrator Release Graph

The orchestrator coordinates the entire system.

## Stages
1. intake user request
2. compile structured plan
3. resolve characters/assets
4. compile App Mode settings
5. choose proxy preview tier
6. run local preview/proof
7. run preview QA
8. create state diff / targeted rerun plan
9. pass final-render preflight
10. hydrate EC2 only if needed
11. run EC2 final render only if unlocked
12. collect manifests
13. run QA certification
14. release or block
15. create final handoff

## Rule
The orchestrator cannot skip preview QA, state diff, proof-gate, or release-gate stages.
