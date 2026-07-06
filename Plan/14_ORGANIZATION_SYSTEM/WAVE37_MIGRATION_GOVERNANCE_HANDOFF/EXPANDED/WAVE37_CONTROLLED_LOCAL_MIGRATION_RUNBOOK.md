# Wave 37 Controlled Local Migration Runbook

## Goal

Move from scattered folders into the canonical local structure without losing files or breaking runtime paths.

## Phases

### Phase 0 — Freeze
- Pause large edits.
- Record current folder locations.
- Save a pre-migration snapshot.
- Export current workflow and registry files.

### Phase 1 — Inventory
- List every known folder.
- Count files by folder.
- Identify heavy assets.
- Identify generated outputs.
- Identify repo/source files.
- Identify ComfyUI runtime files.

### Phase 2 — Map
- Assign every folder to a canonical target.
- Mark source-of-truth owner.
- Mark runtime copy status.
- Mark generated-output status.
- Mark archive/deprecation status.

### Phase 3 — Move
- Move one domain at a time.
- Start with docs/scripts/registries.
- Move workflows next.
- Move reference assets next.
- Move generated outputs after cataloging.
- Move heavy assets only with count/hash validation.

### Phase 4 — Validate
- Verify file counts.
- Verify key paths.
- Verify JSON validity.
- Verify workflow catalog.
- Verify asset catalog.
- Verify QA evidence catalog.
- Verify App Mode control mappings.

### Phase 5 — Refresh catalogs
- Regenerate file catalog.
- Regenerate workflow catalog.
- Regenerate asset catalog.
- Regenerate QA evidence catalog.
- Regenerate stale-index report.

### Phase 6 — Release migration
- Write migration report.
- Keep rollback copy until validation passes.
- Mark old paths legacy.
