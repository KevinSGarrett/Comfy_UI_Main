# Wave 05 — Clean Operator UI Design

## Design principle

The App Mode operator UI must make the system easier to use without making it easier to break.

## Primary tabs/sections

### 1. Run Setup

- project ID
- output type
- runtime target
- QA level
- final promotion allowed/not allowed

### 2. Scene

- environment preset
- lighting preset
- prop/surface context
- scene continuity ID

### 3. Character Setup

- character count
- character bible IDs
- identity references
- body references
- outfit references
- per-character region locks

### 4. Camera and Frame

- shot type
- camera angle
- lens
- zoom/distance
- depth of field
- full-body requirement
- all-characters-in-frame requirement

### 5. Engine and Passes

- primary engine profile
- enabled pass types
- LoRA stack profile by registry/profile name
- no raw LoRA file path exposure

### 6. QA and Export

- auto-rerun on fail
- crop QA required
- manifest hashes required
- export formats
- final promotion gate

## User-facing labels should be clean

The UI should use labels like:

- Skin/detail profile
- Body-shape profile
- Camera/pose profile
- Reference identity profile
- Contact-detail profile
- Fabric/material profile

The UI should not show raw filenames, Civitai IDs, S3 paths, or internal model tags unless in developer/debug mode.

## Why this matters

The operator should not need to understand a 300+ node graph to request a result. The AI project manager should receive structured, validated data instead of raw prompt paragraphs and manual node edits.
