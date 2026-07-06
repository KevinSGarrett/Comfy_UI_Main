# Wave 15 — Implementation Manual

## Main validation command

```powershell
powershell -ExecutionPolicy Bypass -File .\07_IMPLEMENTATION\templates\powershell\Run-Wave15-BaseLaneValidation.ps1 -Root "."
```

## Local implementation sequence

1. Run Wave 15 local validation.
2. Inventory the current Main Flow base lanes.
3. Build clean API-format workflow templates for:
   - Flux2 Dev
   - Flux1 Dev
   - Flux1 Schnell smoke
   - SDXL/RealVisXL
   - Z-Image
   - Pony specialty
   - SDXL fallback
4. Run `/object_info` checks before execution.
5. Patch one lane at a time.
6. Save every patched workflow copy.
7. Run ComfyUI only after dry-run checks pass.
8. Collect history and output evidence.
9. Score QA.
10. Promote only evidence-backed base candidates.

## Do not

- Do not modify the canonical Main Flow in place.
- Do not enable the disabled LoRA library globally.
- Do not use Pony or SD1.5 as default base lanes.
- Do not bridge engines through latent/model objects.
- Do not mark Flux2 as default until runtime proof exists.
