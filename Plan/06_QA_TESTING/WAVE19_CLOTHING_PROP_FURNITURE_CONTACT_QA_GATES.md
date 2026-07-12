# Wave 19 Clothing/Prop/Furniture Contact QA Gates

## Mandatory gates
1. Contact ownership graph exists.
2. Required masks exist.
3. Depth/control/support evidence exists when needed.
4. Fabric/prop/furniture pass profile is compatible with engine route.
5. No-floating and no-clipping checks pass.
6. Contact shadows/occlusion are plausible.
7. Identity, pose, body proportions, and frame integrity are preserved.

## Promotion blockers
- floating prop or unsupported body
- missing contact shadow at required touch point
- furniture not compressing when soft material requires it
- body/fabric/prop clipping
- wrinkle/fold field disconnected from contact geometry
- object ownership ambiguity

## Machine-readable decision
Evidence must contain `contact_graph_check`, `shadow_contact_check`,
`no_floating_check`, and `visual_reject_on_clip`. All must be inspectable passes,
`visual_reject_on_clip.clip_detected` must be false, and a Wave19-scoped visual-QA
reference must explicitly allow final certification. Weighted scores cannot override a
required-gate failure.
