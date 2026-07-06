# Autonomous Pass Planner / Orchestrator Architecture

The orchestrator is the runtime decision layer between the Scene Director and ComfyUI.

Default sequence:
request compile → preflight → base composition → identity/reference → pose/control → mask factory → regional inpaint/detail → upscale/polish → video handoff → audio handoff → promotion.

It decides which passes are required, which workflow template is used, what gets patched, whether ComfyUI can run, whether QA passes, and whether the next action is rerun/fallback/stop/promotion.
