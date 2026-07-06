# Wave 26 Reference Video Correction

## Correction
Wave 26 must not be interpreted as GIF-only. GIF loops are only one export/use case.

The system must also handle **actual reference video files** for motion and temporal guidance.

## Required reference video capabilities
- accept real reference-video files
- fingerprint source video files
- extract metadata
- sample frames
- extract or bind pose/depth/mask timelines
- build keyframe candidates from real frames
- map reference timing to target shot timing
- preserve identity and frame ownership
- detect flicker / temporal artifacts
- support repair planning at frame or segment level

## Supported source categories
- MP4 / MOV / WebM / MKV / AVI video files
- numbered image sequences
- extracted frame folders
- short GIFs used as loops, not as the only reference path

## Required boundary
A GIF loop is an output format or short reference format. It is not a replacement for reference-video handling.
