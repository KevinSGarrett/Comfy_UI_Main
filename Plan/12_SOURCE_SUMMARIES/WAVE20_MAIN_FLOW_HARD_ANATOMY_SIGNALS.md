# Wave 20 Main Flow Hard-Anatomy Signals

The current Main Flow exposes the following Wave 20 signals:

- nodes: 356
- links: 91
- SaveImage lanes: 8
- mask input slots: 2
- low-denoise anchors: 2
- ControlNet-related nodes: 2
- hard-anatomy/detail LoRA signals: 80

## Interpretation
The current workflow has useful runtime anchors for future hard-anatomy repair: the SDXL inpaint/detail lane, cross-engine-to-SDXL low-denoise refine lane, mask input, IPAdapter staging, and Canny ControlNet branch. Wave 20 turns these into repair contracts and QA gates for face, eyes, mouth/teeth, hands/fingers, feet/toes, and nails.
