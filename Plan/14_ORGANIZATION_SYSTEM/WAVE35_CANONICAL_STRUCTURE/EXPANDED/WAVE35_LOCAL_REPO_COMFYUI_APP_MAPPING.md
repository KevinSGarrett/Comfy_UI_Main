# Wave 35 Local ↔ Repo ↔ ComfyUI ↔ App Mode Mapping

## Mapping principle

Every artifact has a lifecycle:

```text
source definition → runtime copy → generated output → QA evidence → release handoff
```

## Examples

| Artifact | Repo | Local | ComfyUI | App Mode |
|---|---|---|---|---|
| Canonical workflow | workflows/comfyui/canonical | 05_WORKFLOWS/00_CANONICAL_MAIN_FLOW | user/workflows/canonical | apps/image_generator |
| Model file | registry only | 03_MODELS/checkpoints | models/checkpoints | profile reference only |
| LoRA file | registry only | 04_LORAS/<engine> | models/loras/<engine> | preset/profile reference |
| Reference image | manifest only | 06_REFERENCE_ASSETS/images | input/references | app input upload |
| Preview output | manifest only | 07_GENERATED_OUTPUTS/previews | output/previews | app preview panel |
| QA evidence | qa schema/report | 08_QA_EVIDENCE | output/qa_evidence | app QA review |
| Release ZIP | releases/manifest | 14_RELEASES | output/releases if needed | release_exports |
