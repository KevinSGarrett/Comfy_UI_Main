# Wave 25 Cross-Character Contact and Occlusion Model

## Occlusion roles
- foreground_source
- foreground_target
- background_source
- background_target
- interleaved_limbs
- prop_between_characters
- shared_contact_boundary

## Contact rules
1. Source and target must be separate instances.
2. Each side must have a region owner.
3. The contact boundary must not erase either body region.
4. Contact shadow must belong to the correct depth order.
5. Occlusion must match the skeleton and frame placement plan.
