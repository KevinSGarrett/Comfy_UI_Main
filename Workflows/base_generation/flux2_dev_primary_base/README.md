# FLUX.2 Dev Primary Base

This lane uses the official ComfyUI FP8-mixed FLUX.2 Dev diffusion model, BF16 Mistral 3 Small encoder, and shared FLUX.2 VAE. Text-to-image and single-reference editing remain separate API graphs.

`workflow.api.json` is the package-compatible canonical alias of `text_to_image.api.json`; the two files must remain byte-identical. The 20-step, guidance-4 envelope follows the installed official ComfyUI blueprints without enabling the optional Turbo LoRA.

The local 8 GB GPU and the approved instance's current `g5.xlarge` shape are not selected runtime targets. The bounded target is the same stopped approved instance resized to `g5.4xlarge`, retaining one 24 GB A10G while increasing host RAM from 16 GiB to 64 GiB. Acquisition, resize, object-info, model load, generation, direct visual QA, and production promotion remain separate gates.
