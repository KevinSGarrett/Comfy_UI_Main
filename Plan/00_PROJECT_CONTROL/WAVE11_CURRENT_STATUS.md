# Wave 11 Current Status

## Production Claim Status

| Capability | Current Status |
|---|---|
| Canny ControlNet branch | Wired in current Main Flow; ready to verify |
| IPAdapter face/reference branch | Wired in current Main Flow; ready to verify |
| DWPose / OpenPose | Designed; not yet runtime-proven in current Main Flow |
| Depth map ControlNet | Designed; not yet runtime-proven in current Main Flow |
| Normal map ControlNet | Designed; not yet runtime-proven in current Main Flow |
| Lineart ControlNet | Designed; not yet runtime-proven in current Main Flow |
| Per-character skeleton ownership | Designed; requires workflow modules and QA |
| Multi-character blocking | Designed; requires masks, depth, skeleton ownership |
| Video pose/depth sequence bridge | Designed; separate runtime lane proof required |

## Why This Matters

Pose/action systems fail when they rely only on prompt wording. Wave 11 creates the contracts that make pose/action explicit: skeleton map, depth layer, occlusion mask, character ownership, control strength, control start/end, and QA evidence.
