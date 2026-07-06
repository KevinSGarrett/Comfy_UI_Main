# Wave 15 — Base Lane Test Matrix

| Test ID | Lane | Purpose | Expected result |
|---|---|---|---|
| W15-T001 | Flux2 Dev | object_info and smoke proof | blocked until installed/proven |
| W15-T002 | Flux1 Dev | primary Flux base | output candidate or fallback |
| W15-T003 | Flux Schnell | fast smoke | decode/composition evidence |
| W15-T004 | SDXL/RealVisXL | SDXL compatibility | checkpoint/LoRA family proof |
| W15-T005 | Z-Image | fast alternative base | separate Z-Image proof |
| W15-T006 | Pony | specialty | blocked until template exists |
| W15-T007 | fallback chain | bounded fallback | failure reason and next lane recorded |
| W15-T008 | bridge to SDXL detail | image bridge only | no latent/model mixing |
| W15-T009 | base-to-video handoff | keyframe eligibility | only passed base candidate can hand off |
