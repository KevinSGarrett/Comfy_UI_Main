# Wave 11 Multi-Character Blocking and Occlusion Rules

## Required Layers

- Character registry lookup.
- Per-character skeleton.
- Per-character mask.
- Depth layer.
- Camera/framing relationship.
- Contact/occlusion plan.
- Control map strength plan.
- Final QA.

## Common Failure Cases

- Limb ownership swaps.
- One character's hand becomes attached to another character.
- Characters merge at contact points.
- A pose map controls the wrong subject.
- Depth order contradicts camera angle.
- Mask edges become visible after inpaint.
- Clothing/prop contours override anatomy or identity.

## Prevention

Use separate skeletons, separate masks, explicit depth layers, and staged control strengths. Strong pose control belongs early. Detail/inpaint belongs later. Do not run strong multi-control maps all the way to 100% unless the test proves it works.
