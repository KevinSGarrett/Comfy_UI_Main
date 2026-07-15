# Wave64 Hyperreal Audio Model and Asset Discovery Protocol

## Purpose

This protocol converts platform search results into a bounded acquisition queue for Rows067-148. It complements the unified acquisition controller; it does not replace acquisition requests, exact hash verification, runtime wiring, or modality QA.

## Required provider pass

For every new speech, Foley, audio-intelligence, synchronization, or lip-sync capability:

1. Check the authoritative local registry, `C:\Comfy_UI_Main`, `C:\Comfy_UI`, and validated caches for exact hashes.
2. Query the official or creator-published Hugging Face organization and resolve an immutable repository commit plus required LFS file SHA-256 values.
3. Pin the official source repository commit and record code license separately from model terms.
4. Query Civitai through `manage_model_asset_acquisition.py discover-civitai` across relevant `Workflows`, `Other`, and `LORA` types.
5. Record exact Civitai model, version, file, filename, scan state, and SHA-256 for any integration candidate.
6. Classify every result as official model authority, official code authority, community integration candidate, compatible optional optimization, duplicate, unrelated, license-blocked, access-blocked, or rejected.
7. Bind selected candidates to exact Item/Tracker rows and a concrete runtime lane.
8. Acquire only when that row is active, using the unified controller and exact pinned identity.

## Selection hierarchy

Official model weights are preferred over mirrors. Official code is preferred over copied wrappers. Civitai workflows may accelerate ComfyUI wiring, but their embedded links, node requirements, scripts, and settings must be inspected offline and rebound to official weights. A workflow archive is never evidence that its dependencies are present or licensed.

Popularity, likes, downloads, recency, filename, adult/NSFW metadata, or a successful provider scan cannot independently select or promote an asset. Adult/NSFW naming remains metadata only and `content_based_suppression=false` is mandatory.

## Exactness requirements

Hugging Face assets require repository ID, immutable 40-character commit, exact filename, bytes, and SHA-256 for each runtime-critical LFS object. Civitai assets require model ID, model-version ID, file ID, exact filename, and SHA-256. GitHub source requires repository, immutable commit, and recorded license state.

Unknown or custom licenses block acquisition until the exact terms and intended use are recorded. Gated models block until authorized access is accepted. Paid/private restrictions are never bypassed.

## Runtime completion boundary

Discovery is not acquisition. Acquisition is not integration. Integration is not production readiness. A selected asset must still pass exact-hash reuse/download, environment isolation, loader visibility, bounded runtime generation, technical QA, perceptual QA, benchmark comparison, and an explicit promotion decision.

## Refresh policy

Do not repeat broad provider searches during every audit. Refresh a candidate only when its implementation row activates, an exact source disappears, a model revision is intentionally reconsidered, a license changes, a benchmark exposes a capability gap, or the user explicitly requests a new market scan. Preserve previous snapshots and candidate decisions.
