# Wave 15 — Image Base Generation Lanes Architecture

Wave 15 creates the reliable **base image generation layer** for the larger image, video, and audio hyper-realism system.

The base lane is the first visually committed image pass. It is not the final image by itself. It becomes the source for later identity, control, mask, regional inpaint, detail, upscale, video keyframe, and QA/promotion passes.

## Required lane families

Wave 15 formalizes these lane families:

| Lane family | Role | Promotion stance |
|---|---|---|
| Flux2 | Future Flux-first primary lane | Planned; requires runtime proof |
| Flux1 Dev | Current Flux-first primary lane | Target primary when proven |
| Flux1 Schnell | Fast smoke/fallback lane | Smoke/fallback until quality proof |
| SDXL / RealVisXL | Compatibility/detail lane | Essential for SDXL LoRA/refine ecosystem |
| Z-Image | Fast alternative/experimental base | Separate engine, not Flux |
| Pony | Specialty lane only | Not default; separate prompt/model profile |
| SD1.5 | Legacy last-resort | Avoid as primary hyperreal base |

## Base lane boundary

The base lane may create the first full image, but it must not:

- Promote itself.
- Enable the disabled LoRA library globally.
- Mix checkpoint/model/LoRA families.
- Pretend a lane is proven because it exists in the UI workflow.
- Use Pony/SD1.5 as default hyper-real base unless explicitly routed and proven.
- Bridge across engines by latent/model objects.

Cross-engine transfer must happen through saved images, image manifests, and validated reload/refine steps.

## Base generation lifecycle

```text
Scene Director plan
→ base lane router
→ model-family compatibility check
→ workflow template/API JSON patch
→ ComfyUI dry-run/object_info check
→ ComfyUI prompt submission
→ history/output collection
→ decode/composition/identity/quality QA
→ fallback/rerun or promotion candidate
```

## Main Flow reality

The current Main Flow already contains several useful image lanes, but the lane names are not enough. Wave 15 records the concrete SaveImage lane, upstream nodes, loaders, samplers, and patch targets. Any lane with a naming/engine mismatch is blocked from production promotion until runtime proof and compatibility evidence pass.
