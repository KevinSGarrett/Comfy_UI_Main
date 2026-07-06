# Wave 26 Keyframe State Model

Each keyframe is a complete scene state.

## Required keyframe fields
- keyframe_id
- time_index
- phase_name
- camera_state
- frame_composition_state
- active_characters
- per-character pose state
- per-character visibility state
- depth order
- interaction/contact state
- object/prop state
- environment state
- lighting state
- required masks
- required control maps
- expected motion entering frame
- expected motion leaving frame
- QA targets

## Keyframe classes
- anchor_start
- directional_motion
- contact_start
- contact_hold
- pressure_peak
- release
- recovery
- loop_close
