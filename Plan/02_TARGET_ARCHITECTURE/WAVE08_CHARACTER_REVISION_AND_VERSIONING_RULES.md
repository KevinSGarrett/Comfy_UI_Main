# Wave 08 — Character Revision and Versioning Rules

## Why Versioning Matters

Hyperreal character work fails when identity changes are hidden inside prompts. A smaller waist, changed hairline, different face, new skin marks, or altered voice can either be a temporary scene state or a permanent character revision. The system must know the difference.

## Version Naming

Use sequential versions:

```text
v001, v002, v003
```

Use variants inside a version only when identity is unchanged:

```text
v001_outfit_casual
v001_outfit_formal
v001_makeup_evening
v001_hair_tied_back
```

## Revision Types

| Revision Type | New Version? | Example |
|---|---:|---|
| pose change | No | standing, sitting, walking |
| expression change | No | smile, serious, tired |
| temporary makeup | No | smoky makeup, wet mascara |
| temporary outfit | No | different clothing set |
| haircut/color change | Maybe | depends whether intended permanent |
| body silhouette change | Usually yes | waist/hips/height/core body shape |
| facial structure change | Yes | nose, jawline, eyes, face shape |
| skin permanent marks | Yes | tattoos/scars/moles if persistent |
| voice identity change | Yes | different voice/timbre/persona |

## Revision Request Workflow

1. User asks for a change.
2. Scene Director checks whether the field is locked.
3. If unlocked, apply scene variant.
4. If locked, create `proposed_revision` object.
5. Validation checks conflict and QA requirements.
6. Approved revision creates a new Character Bible version.
7. Old version is preserved for reproducibility.

## Required Revision Record

Every revision must record:

- old character version
- new character version
- changed fields
- unchanged locked fields
- reason for change
- source request
- reference updates
- QA acceptance evidence
- rollback path
