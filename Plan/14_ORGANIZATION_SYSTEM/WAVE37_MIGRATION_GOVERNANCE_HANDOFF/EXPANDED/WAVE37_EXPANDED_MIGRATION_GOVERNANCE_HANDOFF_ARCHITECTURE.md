# Wave 37 Expanded Migration, Governance, Validation, and Handoff Architecture

Wave 37 converts the system structure into an operating process.

## Main operating loops

1. **Migration loop** — inventory, map, move, validate, catalog refresh, rollback if needed.
2. **Repo cleanup loop** — detect source-control pollution, remove generated/heavy/cache files, validate repo structure.
3. **Runtime handoff loop** — prove ComfyUI runtime folders, required assets, workflows, inputs, outputs, and QA evidence paths are understood.
4. **App Mode handoff loop** — prove each app/control/preset/profile maps to workflow inputs and validation rules.
5. **Local/EC2 sync loop** — create minimal upload payload, run, pull back outputs/evidence, stop EC2, validate evidence.
6. **Governance loop** — ensure future waves follow file index, registry, validation, and release proof rules.
7. **Final handoff loop** — compile handoff packet, release checklist, validation report, and release decision.

## Principle

Migration and handoff must be evidence-based. Moving files or handing off workflows without manifests creates chaos.
