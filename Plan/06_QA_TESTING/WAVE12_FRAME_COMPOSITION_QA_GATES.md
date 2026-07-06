# Wave 12 Frame Composition QA Gates

## Gate 1 — Contract completeness

Pass when the frame composition contract includes expected character count, body visibility profile, crop policy, character slots, and no-merged-body requirement.

## Gate 2 — Output evidence availability

Pass when generated image/video output has corresponding detector evidence.

## Gate 3 — Character count

Pass when expected count equals detected assigned primary characters.

## Gate 4 — Body visibility

Pass when the visible body ratio and required landmarks meet the selected profile.

## Gate 5 — Crop boundary

Pass when no forbidden crop event occurs.

## Gate 6 — No merged bodies

Pass when each character has a distinct person instance/skeleton or a planned occlusion assignment.

## Gate 7 — Promotion decision

Pass when score is above threshold and no hard fail overrides are present.
