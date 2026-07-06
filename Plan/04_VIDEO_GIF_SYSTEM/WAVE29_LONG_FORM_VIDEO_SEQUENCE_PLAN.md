# Wave 29 Long-Form Video Sequence Plan

Long-form video is broken into segments.

## Segment fields
- segment_id
- previous_state_id
- next_state_id
- scene_phase
- active characters
- fatigue/exertion state
- clothing/hair/surface state
- contact/deformation state
- primary motion
- allowed variation
- QA gate set

Each segment must read the continuity ledger before generation and write an updated state after QA.
