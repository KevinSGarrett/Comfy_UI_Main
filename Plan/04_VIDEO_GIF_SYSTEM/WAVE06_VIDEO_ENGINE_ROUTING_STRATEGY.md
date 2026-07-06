# Wave 06 Video/GIF Engine Routing Strategy

## Purpose
Video routing must remain separate from image routing. A still image engine can create keyframes, but video engines create temporal motion.

## Planned video engines
| Engine | Role |
|---|---|
| Wan2.2 | Primary video candidate |
| HunyuanVideo 1.5 | Efficient/lower barrier video candidate |
| LTX-2 | Audio-video candidate |
| AnimateDiff-style fallback | Legacy/fallback only if still useful |

## Video route decision inputs
- output type: GIF, MP4, WebM, image sequence
- duration
- FPS
- character count
- camera movement
- required body/action motion
- reference video present or not
- keyframe count
- identity lock requirement
- contact/deformation requirement
- audio required or silent
- local/EC2 cost budget

## Video engine routing
### Wan2.2
Use for high-priority video tests, image-to-video, text-to-video, or video-to-video candidates.

### HunyuanVideo 1.5
Use for cost/VRAM-sensitive tests and compare with Wan2.2 for motion coherence.

### LTX-2
Use when synchronized audio-video is part of the test. Do not automatically replace the separate audio system until AV QA passes.

## QA gates
Every video route must include:

- keyframe QA
- identity drift QA
- flicker QA
- contact drift QA
- body-shape drift QA
- frame crop/framing QA
- temporal mask consistency QA
- output manifest with frame count/FPS/duration/hash

## Rule
A still-image success does not prove video success. Video has its own promotion gate.
