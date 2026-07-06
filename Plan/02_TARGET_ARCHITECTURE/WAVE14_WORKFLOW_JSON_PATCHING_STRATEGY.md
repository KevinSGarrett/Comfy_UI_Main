# Workflow JSON Patching Strategy

Patchable targets include prompt text, negative text, seed, steps, CFG, sampler, scheduler, denoise, latent dimensions, SaveImage prefixes, image/mask/control-map inputs, IPAdapter attention masks, and ControlNet strength.

The patcher must preserve the source workflow and emit a patch manifest. It must fail closed if a node id, widget index, or input slot is missing.
