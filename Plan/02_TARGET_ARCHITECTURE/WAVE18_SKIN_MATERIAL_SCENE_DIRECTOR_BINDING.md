# Wave 18 Skin/Material Scene Director Binding

The Scene Director must translate user intent into a structured surface plan.

## Example intent normalization
- "more pores" -> pore_density = medium_up
- "slight cellulite on thighs" -> target_regions = thighs; cellulite_intensity = low_to_medium
- "oiled skin" -> moisture_state = oiled; specular = controlled
- "pressure marks from hands" -> pressure_marks = true; contact_owner required
- "sweaty fabric" -> fabric_state = damp / clinging; surface continuity with clothing required

## Outputs required from Scene Director
- skin_material_contract
- target region list
- surface profile selection
- mask scale recommendation
- pass order recommendation
- QA goals
