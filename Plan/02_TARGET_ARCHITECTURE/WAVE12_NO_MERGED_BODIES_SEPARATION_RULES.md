# Wave 12 No-Merged-Bodies and Separation Rules

Multi-character scenes need explicit separation logic. A visually convincing scene can still fail if bodies are fused, skeletons share limbs, or character identities merge.

## Required checks

- One person instance per expected character unless an occlusion plan says otherwise.
- One skeleton per expected character.
- One face/body assignment per visible face.
- No unassigned body fragments.
- No shared torso or merged limb chain.
- No accidental extra arms, legs, heads, or hands.
- Contact areas must preserve separate silhouettes unless the occlusion plan explicitly permits overlap.

## Occlusion handling

Occlusion is allowed only when it is planned. The scene plan must declare which character is foreground, which is background, and what body regions may be hidden.

Unplanned occlusion that hides identity anchors or creates a fused body is a promotion blocker.
