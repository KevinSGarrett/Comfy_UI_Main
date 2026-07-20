# MaskFactory sibling consumer scaffold

Isolated clean `Comfy_UI_Main` branch for MaskFactory bridge consumer work.

- Branch: `codex/maskfactory-sibling-consumer-scaffold`
- Base: `origin/main` (NOT the dirty Wave64 tree at `C:\Comfy_UI_Main`)
- Authority: `sibling_main_consumer` (explicitly NOT production Main adoption)

## Run

```
python Plan/07_IMPLEMENTATION/scripts/maskfactory_sibling_consumer/run_sibling_consumer.py \
  --output runtime_artifacts/maskfactory_sibling_consumer/run_evidence.json
```

## Honesty

Does not close HARD MF-P6-11.02 / 11.07 / 12.05 / 12.06. Does not touch Wave64.
