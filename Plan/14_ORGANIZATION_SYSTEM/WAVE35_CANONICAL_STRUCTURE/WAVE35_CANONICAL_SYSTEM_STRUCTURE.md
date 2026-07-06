# Wave 35 Canonical System Structure

The system is split into four major physical contexts:

1. **Local workspace** — where the user works and stores heavy local assets.
2. **Git repository** — where source-controlled code, schemas, docs, templates, and registries live.
3. **ComfyUI runtime** — where ComfyUI workflows, model references, output folders, and runtime extensions live.
4. **App Mode / UI package** — where simplified user-facing controls and app configuration live.

## Rule
Heavy runtime assets and generated outputs should not be mixed with source-controlled implementation files.
