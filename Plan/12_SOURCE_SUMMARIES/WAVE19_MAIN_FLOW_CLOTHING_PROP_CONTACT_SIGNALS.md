# Wave 19 Main Flow Clothing/Prop/Furniture Contact Signals

The current Main Flow exposes these Wave 19 signals:

- node count: 356
- link count: 91
- SaveImage lanes: 8
- mask input slots: 2
- low-denoise anchors: 2
- ControlNet-related nodes: 2
- clothing/fabric/prop/contact LoRA signals: 37
- tracker contact-related rows: 9450

## Interpretation
The workflow has useful future hooks for contact/fabric/furniture refinement, especially masked inpaint and low-denoise refine anchors. The current graph still does not prove furniture compression, prop ownership, or fabric contact behavior until runtime evidence is generated and scored.
