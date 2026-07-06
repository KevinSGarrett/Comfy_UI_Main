# Wave 26 GIF Loop Planning System

GIF loops need tighter closure constraints than linear video shots.

## Loop rules
1. Frame 0 and final frame must be visually compatible.
2. Motion direction at loop close must feel natural.
3. Identity, framing, and environment cannot jump at the loop seam.
4. Contact and deformation states must either fully close or intentionally ping-pong.
5. Loop class must be declared:
   - seamless_cycle
   - ping_pong
   - breath_loop
   - idle_loop
   - repeating_action_loop

## Recommended minimal structure
- start anchor
- anticipation keyframe
- action keyframe
- peak keyframe
- recovery keyframe
- loop-close keyframe
