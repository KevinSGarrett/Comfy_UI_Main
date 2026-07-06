# Wave 10 Multi-Character Composition QA

## Required Checks

- Correct subject count
- Correct screen position
- Correct depth order
- No identity blending
- No body/face/hair merge
- Required hands/contact/props visible
- Scale is consistent between subjects
- Clothing/outfit IDs remain separate
- Environment scale anchors still make sense

## Common Failures

- one extra person appears
- two characters merge into one
- faces swap
- one character loses identity
- hands appear on wrong subject
- depth order flips
- background object becomes body part
- contact point is cropped

## Evidence

QA report must include:

- camera plan id
- output path
- subject count
- crop verdict
- focus verdict
- identity-separation verdict
- blocking issues
