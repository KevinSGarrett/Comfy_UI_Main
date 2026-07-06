# Wave 24 Instance Mask, Skeleton, and Region Plan

## Mask stack
- full person-instance mask
- body-region masks
- clothing/accessory masks
- contact/occlusion masks
- protected identity masks

## Skeleton stack
- global scene pose map
- per-character skeleton map
- per-limb/hand detail control maps when needed

## Region stack
Every region mask must resolve to one character_instance_id.
