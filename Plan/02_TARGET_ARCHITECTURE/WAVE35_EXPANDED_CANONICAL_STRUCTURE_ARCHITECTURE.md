# Wave 35 Expanded Canonical Structure Architecture

This document mirrors the detailed organization package into the target architecture section.

## Domains
- local_workspace
- git_repo
- comfyui_runtime
- app_mode
- heavy_assets
- generated_outputs
- qa_evidence
- manifests
- ec2_sync
- releases

## Architecture rule
Every artifact must belong to exactly one owner domain, with runtime/export copies explicitly marked.
