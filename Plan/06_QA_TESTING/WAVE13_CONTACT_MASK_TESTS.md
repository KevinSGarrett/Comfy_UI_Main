# Wave 13 — Contact Mask Tests

## Required contact validation

A contact mask must prove:

- both participants are named,
- the contact edge exists,
- occlusion order is plausible,
- grounding or contact shadow is present when applicable,
- the mask does not accidentally include unrelated body/object regions.

## Common failure modes

- floating object,
- hand not touching object,
- body parts merged,
- fabric edge cuts through body,
- contact shadow absent,
- object/person ownership unclear,
- mask bleeds into background.

## Promotion boundary

Contact masks are promotion-critical for scenes where physical interaction, overlap, gripping, leaning, sitting, standing, or object use is part of the requested action.
