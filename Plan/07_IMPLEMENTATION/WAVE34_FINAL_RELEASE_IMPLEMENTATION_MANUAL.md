# Wave 34 Final Release Implementation Manual

## Steps
1. Validate this cumulative pack.
2. Export or verify App Mode controls.
3. Compile the orchestrator release plan.
4. Run local proof validation.
5. Generate low-cost preview evidence.
6. Run preview QA.
7. Run state diff and targeted rerun planning.
8. Run final-render preflight.
9. Hydrate EC2 only if preflight unlocks EC2.
10. Collect runtime manifests.
11. Run QA certification.
12. Create release gate decision.
13. Create final handoff packet.

## Command
Use the Wave 34 validation script first:

```powershell
.\07_IMPLEMENTATION\templates\powershell\Run-Wave34-FinalReleaseValidation.ps1 -Root .
```
