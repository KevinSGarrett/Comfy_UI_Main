# Wave 01 Delivery Report — GitHub, Local Repo, EC2 Mirror, Cost-Aware Development

## Wave status

Wave 01 is a cumulative update on top of Wave 00. It does not replace Wave 00; it extends it with the first implementation-control layer for the local repository, GitHub repository, EC2-off-by-default development model, S3/model-asset strategy, local validation gates, and source-status handling for ongoing upstream artifacts.

## User direction applied

The user clarified that these sources are ongoing and being built alongside the 35-wave system:

- `wave42_working_tracker_20260704_105253_ltxv_router_metadata_repromotion_20260705_142403_asset_compat_registry_promotion.csv`
- `Plans.zip`

Therefore, Wave 01 treats both as **mutable upstream sources**, not completed/frozen truth.

## Wave 01 primary goal

Move the project toward:

```text
Local repo root: C:\Comfy_UI_Main
GitHub remote:  https://github.com/KevinSGarrett/Comfy_UI_Main
EC2 state:      off by default
Model storage:  external to Git, S3/EC2/local-cache manifest based
Runtime proof:  only after local static QA passes
```

## What this wave adds

- GitHub/local repository architecture.
- Local repo bootstrap instructions.
- Strict `.gitignore` and `.gitattributes` templates.
- Model asset exclusion policy.
- EC2 off-by-default guard policy.
- S3/local/EC2 model-cache manifest strategy.
- Local-first validation and QA matrix.
- Source-status registries for the tracker, Plans ZIP, advanced additions, chat logs, and current main flow.
- Scripts for repo bootstrap, repo validation, model-file exclusion checking, and EC2 proof gating.

## Non-goals

Wave 01 does **not** start EC2, run GPU generation, download model assets, modify the actual GitHub repository, or prove ComfyUI runtime execution.

## Promotion rule

Wave 01 can be considered complete only when the AI project manager can prove:

1. The local repo structure exists.
2. The repo excludes model binaries.
3. Source inventories are recorded.
4. The local validation script passes.
5. EC2 runtime proof is blocked by default unless an explicit confirmation token is used.
6. The tracker and Plans ZIP are recorded as ongoing mutable sources.
