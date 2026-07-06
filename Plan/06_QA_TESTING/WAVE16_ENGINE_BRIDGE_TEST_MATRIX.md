# Wave 16 — Engine Bridge Test Matrix

## Required bridge tests

| Test id | Bridge | Expected result |
|---|---|---|
| WB16-BRIDGE-001 | Flux2 base → SDXL low-denoise | Planned only until Flux2 runtime proof exists |
| WB16-BRIDGE-002 | Flux1 base → SDXL low-denoise | Image bridge only; no latent/model object crossing |
| WB16-BRIDGE-003 | Z-Image base → SDXL low-denoise | Anchored to current static template; runtime proof required |
| WB16-BRIDGE-004 | SDXL base → SDXL detail | Preferred same-family refine |
| WB16-BRIDGE-005 | SDXL base → Pony masked specialty | Masked only; global pass blocked |
| WB16-BRIDGE-006 | Pony specialty → SDXL cleanup | Allowed after drift/style QA |
| WB16-BRIDGE-007 | Any base → SD1.5 tiny repair | Last resort; tiny mask only |
| WB16-BRIDGE-008 | SDXL base → Flux refine | Held until Flux image-conditioning proof exists |

## Pass criteria

A bridge test passes only if:

- source and target engine families are explicit;
- transfer object is allowed;
- denoise is valid;
- output exists and decodes;
- preservation QA passes;
- no forbidden object crossing occurs.
