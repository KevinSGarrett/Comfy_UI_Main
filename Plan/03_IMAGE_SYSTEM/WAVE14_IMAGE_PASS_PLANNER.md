# Image Pass Planner

Default image path:
preflight → base composition → identity/reference → pose/control if needed → mask factory if needed → regional detail → upscale/polish → promotion.

The system should rerun only failing passes when earlier pass evidence remains valid.
