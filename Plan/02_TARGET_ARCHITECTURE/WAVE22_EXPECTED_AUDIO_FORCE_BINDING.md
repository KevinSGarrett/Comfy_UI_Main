# Wave 22 Expected Audio Force Binding

Wave 22 does not produce final audio by itself. It records audio-force metadata so the future audio system knows what kind of foley or force response should exist.

## Audio-force fields
- `audio_force_class`
- `expected_foley_family`
- `contact_duration_class`
- `surface_material_pair`
- `force_intensity`
- `timing_alignment_required`

## Audio force classes
- silent_contact
- soft_fabric_rustle
- skin_surface_contact
- firm_surface_contact
- object_tap
- object_drag
- furniture_creak
- impact_thud
- rebound_release

## Rule
If video shows contact, compression, or impact, the audio metadata must say whether the contact should be silent, subtle, or audible.
