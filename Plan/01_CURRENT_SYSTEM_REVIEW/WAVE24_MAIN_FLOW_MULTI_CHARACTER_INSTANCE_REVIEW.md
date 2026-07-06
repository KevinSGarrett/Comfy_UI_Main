# Wave 24 Main Flow Multi-Character Instance Review

The current Main Flow is still primarily an image-generation canvas with runtime hooks for inpaint, reference, and ControlNet-style structure. It has **356 nodes**, **91 links**, **8 SaveImage lanes**, and **3 mask-capable anchors**.

## What is already useful
- The inpaint/detail lane can accept region masks.
- IPAdapter has an optional attention mask input.
- Canny ControlNet staging can support structural passes.
- Low-denoise samplers can be used for local per-instance repair.

## What Wave 24 adds around it
The Main Flow does not yet prove automatic multi-character instance segmentation, per-character skeleton extraction, or depth order resolution. Wave 24 therefore adds the missing contracts and QA layer so those items are explicit before runtime promotion.
