# Wave 19 Scene Director Contact Binding

The Scene Director must convert requests into structured contact plans.

## Examples
- "sitting on a couch" -> body_to_furniture support, soft cushion compression, contact shadow
- "tight shirt" -> fabric stretch profile, torso adjacency, seam preservation
- "holding a glass" -> hand_to_prop grip ownership, finger wrap QA, object mask
- "fabric clinging to body" -> material cling profile, body-region adjacency, wrinkle/tension direction
- "leaning against table" -> hard-surface support, contact shadow, no furniture deformation

## Required output fields
- contact_contract_id
- involved character ids
- involved prop/furniture ids
- mask ids
- contact owner graph
- support material profile
- pass profiles
- QA goals
