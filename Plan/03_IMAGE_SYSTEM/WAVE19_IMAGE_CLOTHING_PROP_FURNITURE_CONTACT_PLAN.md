# Wave 19 Image Clothing/Prop/Furniture Contact Plan

## Image pass order
1. establish approved image and masks
2. validate contact ownership graph
3. run fabric fold/stretch pass if needed
4. run prop contact/support pass if needed
5. run furniture compression/support pass if needed
6. run contact-shadow/occlusion cleanup
7. score and promote/rerun

## Mask requirements
- person-instance mask
- body-region mask
- clothing/fabric mask
- prop mask
- furniture/support-surface mask
- contact-edge mask

## Required machine gates
- `contact_graph_check`
- `shadow_contact_check`
- `no_floating_check`
- `visual_reject_on_clip`

Promotion is fail-closed. Every required gate must be an inspectable pass, clipping must
be explicitly absent, and the linked visual-QA record must be scoped to Wave19 and allow
final certification. Local evidence from another wave can support review but cannot
certify this contract.
