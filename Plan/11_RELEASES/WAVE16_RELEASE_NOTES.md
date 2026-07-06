# Wave 16 Release Notes

## Added

- Image refine and engine bridging architecture.
- Low-denoise policy.
- Cross-engine bridge matrix.
- SDXL/RealVisXL default refine target.
- Pony masked specialty-only path.
- Flux/Flux2 refiner hold state until runtime proof.
- Z-Image to SDXL image bridge contract.
- SD1.5 tiny repair last-resort policy.
- Base preservation and drift prevention QA.
- Rerun/fallback/stop policy.
- Workflow patching scripts.
- Local static validation.

## Not claimed

- No live ComfyUI execution is claimed by this architecture pack.
- No Flux2 refine runtime proof is claimed yet.
- No Pony masked specialty runtime proof is claimed yet.
- No SD1.5 repair runtime proof is claimed yet.
- No image output is promoted by this pack alone.

## Promotion requirement

A future runtime wave must produce actual output files, history records, hashes, QA reports, and promotion decisions before any refine lane becomes production-promoted.
