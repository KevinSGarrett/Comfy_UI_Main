# Wave 21 Soft-Body Scene Director Binding

The Scene Director must convert user words into profile ids and region bindings.

## Example normalization
- "firm stomach" -> profile axis: firmness up, sag down
- "soft thighs" -> profile: skin_soft_natural or soft_tissue_high_sag depending on identity bible
- "fabric clinging" -> fabric_elastic_cling
- "couch compression" -> cushion_soft_furniture + support owner
- "subtle jiggle" -> motion_profile subtle_rebound
- "ripple" -> ripple axis with temporal evidence requirement for video

## Output contracts
- soft_body_material_profile
- soft_body_region_binding
- deformation_pass_plan
- compression_rebound_contract
- QA goals
