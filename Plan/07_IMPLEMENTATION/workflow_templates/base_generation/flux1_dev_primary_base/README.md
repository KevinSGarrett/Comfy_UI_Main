# Flux1 Dev primary template

This directory contains the API workflow and patch/runtime contracts for the
`flux1_dev_primary_base` lane. The graph is extracted from the native Flux
Schnell branch in the authoritative Main Flow and retargeted to the declared
Flux1 Dev checkpoint with higher-quality static settings.

## Current state

The workflow is statically implemented. The immutable Comfy-Org revision,
licensed source, byte count, and checkpoint SHA256 are recorded. The existing
checkpoint at `C:\Comfy_UI\Runtime_Data` is exposed through ComfyUI's configured
external model path and matches the required SHA256, so no download, copy, or
duplicate installation is needed. The evidence records static presence only.

`runtime_requirements.json` remains fail-closed for use-rights and runtime proof.
The local installer remains available for a future authorized replacement, is
dry-run by default, resumes through a `.partial` file, requires a hash-bound
noncommercial acceptance record before network contact, and installs only after
exact verification. The checked-in acceptance template remains `accepted:
false`; changing it is a legal-use assertion, not an automation approval.

Both checked-in mirrors intentionally use the canonical Plan workflow path in
their metadata. `Workflows/base_generation/ACTIVE_LANES.json` exposes the
runtime mirror, while contract validation requires the four mirrored files to
remain byte-identical.

## Promotion rule

This template is not promoted until use rights are documented and live
object_info/model listing, model loading, output, technical QA, visual QA, and
target-runtime evidence pass.
