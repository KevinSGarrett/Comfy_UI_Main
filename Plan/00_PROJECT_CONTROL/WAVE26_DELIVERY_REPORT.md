# Wave 26 Delivery Report

Wave 26 adds the temporal planning layer.

## Delivered capability
- still-to-keyframe promotion contracts
- temporal scene state model
- pose/depth/mask timeline architecture
- GIF loop planning rules
- video shot plan system
- continuity scoring and rerun policies
- keyframe and export QA gates
- example schemas and planning artifacts

## Runtime boundary
The current Main Flow remains the source/staging canvas. Wave 26 establishes how image states become motion-ready plans, but real output evidence is still required before promotion.

## Reference video correction delivered
This corrected Wave 26 pack adds first-class support for real reference video files.

New deliverables include reference-video ingestion architecture, accepted file-format contracts, frame extraction plans, pose/depth/mask timeline plans, frame manifest schemas, QA gates, rerun rules, and example contracts for MP4/MOV/WebM-style sources.
