# Wave 26 Reference Video File Ingestion Architecture

## Purpose
Reference videos are first-class temporal source assets. They are used to guide motion, choreography, pose, depth, masks, contact, deformation timing, camera motion, and frame repair.

## Input types
- `.mp4`
- `.mov`
- `.webm`
- `.mkv`
- `.avi`
- `.m4v`
- image-sequence folders such as `frame_%05d.png`
- GIFs only when the source is intentionally a loop or short clip

## Ingestion pipeline
1. Accept source video path or uploaded reference asset id.
2. Validate file extension and container metadata.
3. Fingerprint file with size, duration, fps, resolution, frame count, and hash.
4. Extract or sample frames according to the reference-video profile.
5. Build per-frame manifest records.
6. Extract or bind pose, depth, segmentation, masks, optical-flow, and contact signals.
7. Build a target timeline contract.
8. Use the timeline contract to drive GIF or video generation.

## Important distinction
GIF loop planning is a subfeature. Reference-video ingestion is the broader system that handles real video files and should feed both GIF and full-video workflows.
