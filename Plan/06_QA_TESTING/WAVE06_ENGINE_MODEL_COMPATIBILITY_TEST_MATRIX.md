# Wave 06 Engine/Model Compatibility Test Matrix

| Test ID | Test | Local only? | EC2 needed? | Blocks promotion if fail? |
|---|---|---:|---:|---:|
| W06-T01 | Engine registry JSON parses | Yes | No | Yes |
| W06-T02 | Every engine has unique engine_id | Yes | No | Yes |
| W06-T03 | Every model candidate has family and promotion_status | Yes | No | Yes |
| W06-T04 | Route request returns deterministic decision | Yes | No | Yes |
| W06-T05 | Cross-family LoRA route is rejected | Yes | No | Yes |
| W06-T06 | Rejected/superseded model is blocked | Yes | No | Yes |
| W06-T07 | Flux2 route remains blocked before proof | Yes | No | Yes |
| W06-T08 | SDXL detail pass selects only SDXL-compatible assets | Yes | No | Yes |
| W06-T09 | Pony specialty pass does not load SDXL/Flux LoRAs | Yes | No | Yes |
| W06-T10 | Video route does not use image-only QA | Yes | No | Yes |
| W06-T11 | Audio route requires audio manifest | Yes | No | Yes |
| W06-T12 | object_info confirms required node classes | No | Local/EC2 ComfyUI | Yes |
| W06-T13 | Flux2 model-loading proof | No | Local/EC2 GPU | Yes for Flux2 |
| W06-T14 | Output file proof for each engine | No | Local/EC2 GPU | Yes |
| W06-T15 | Visual QA comparison across Flux2/Flux1/SDXL | Partly | Yes for GPU outputs | Yes |
