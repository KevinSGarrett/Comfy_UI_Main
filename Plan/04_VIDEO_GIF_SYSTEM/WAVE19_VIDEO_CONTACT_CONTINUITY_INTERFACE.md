# Wave 19 Video Contact Continuity Interface

Video/GIF outputs must keep contact states stable over time.

## Temporal requirements
- prop ownership cannot switch hands without a declared action
- clothing folds cannot flicker every frame
- furniture compression must track body weight and position
- contact shadows must move consistently with camera/body motion

## Evidence
Store per-frame contact graph, mask ids, support state, and failure flags.
