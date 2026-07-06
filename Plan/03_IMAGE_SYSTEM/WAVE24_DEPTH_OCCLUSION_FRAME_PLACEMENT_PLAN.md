# Wave 24 Depth, Occlusion, and Frame Placement Plan

## Placement checks
- instance bounding boxes do not violate requested composition
- character count is correct
- full/half/close-up coverage agrees with Wave 12 frame rules
- no cropped head/feet/hands unless requested

## Depth checks
- foreground/background ordering is stable
- occlusion is mask-backed
- contact overlaps match Wave 22 contact graph
- merged bodies are blocked
