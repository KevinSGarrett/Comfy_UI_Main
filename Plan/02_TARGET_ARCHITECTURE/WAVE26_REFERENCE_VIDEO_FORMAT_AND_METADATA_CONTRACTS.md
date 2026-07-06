# Wave 26 Reference Video Format and Metadata Contracts

## Required metadata
- source_video_id
- original_path_or_asset_id
- file_extension
- container_format
- codec if known
- duration_seconds
- fps
- frame_count
- width
- height
- audio_present
- hash or fingerprint
- extraction_profile_id

## Required generated artifacts
- frame manifest
- sampled frame folder or references
- pose timeline if enabled
- depth timeline if enabled
- mask timeline if enabled
- contact timeline if enabled
- QA report

## Blockers
A reference video cannot be promoted as usable if:
- it cannot be decoded,
- frame count is unknown,
- frames are blank/corrupt,
- orientation metadata is unresolved,
- timeline extraction fails,
- the video contains heavy cuts but is treated as one continuous shot.
