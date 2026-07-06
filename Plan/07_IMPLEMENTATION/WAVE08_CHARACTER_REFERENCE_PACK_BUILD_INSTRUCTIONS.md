# Wave 08 — Character Reference Pack Build Instructions

## 1. Collect References

Collect references by category:

- face front
- face angled
- body full-frame
- hair close-up
- skin detail
- outfit full-frame
- outfit detail
- optional voice/audio

## 2. Sort References

Separate into:

```text
references/raw
references/approved
references/rejected
```

Only approved references can be used in production plans.

## 3. Create Masks

Create masks for:

- face
- hair
- body
- skin markers
- outfit
- accessories
- hands/contact zones when needed

## 4. Create Hash Manifest

For each file record:

- file path
- size bytes
- SHA256
- created/updated time
- reference asset type
- approval state
- intended consumer

## 5. Create Character Bible

The Character Bible should include stable traits and explicit allowed variations.

## 6. Validate

Run local validation. Fix missing fields before runtime testing.

## 7. Runtime Smoke Test

Use a simple scene. Do not test the character first in a complex multi-character/contact/video scene. Prove identity in a clean base image first.

## 8. Promote

Promote only when:

- reference pack validates
- generated image exists
- continuity QA passes
- model stack is compatible
- output and logs are saved as evidence
