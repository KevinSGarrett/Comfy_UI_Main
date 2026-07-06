# Wave 17 — Scene Director Binding

## What the Scene Director must output
When a user requests body shape correction, the Scene Director must not output only prompt text. It must output a body correction intent block.

## Intent fields
- target character
- target body regions
- target profile
- visibility requirements
- pose preservation requirement
- identity preservation requirement
- clothing preservation requirement
- strength level
- allowed engine families
- QA goals

## Example intent mapping
"Make the stomach smaller" becomes:
- target_regions: abdomen_stomach, waist_left, waist_right, outer_silhouette
- target_profile: subtle_waist_stomach_refine
- strength: low/medium
- protected_regions: face_identity, hands_contact_exclusion, background
- required_qa: identity, pose, silhouette, clothing, crop boundary

"Fix hips and thighs" becomes:
- target_regions: hips_pelvis, thigh_left, thigh_right, outer_silhouette
- target_profile: hip_thigh_balance_correction
- strength: low/medium
- required_qa: left_right_balance, stance preservation, clothing continuity

## Invalid Scene Director output
The Scene Director must not say:
- "just prompt it harder"
- "enable all body LoRAs"
- "redraw the whole body"
- "ignore the base image"

Those are blocked because they are likely to corrupt identity, pose, frame composition, and clothing continuity.
