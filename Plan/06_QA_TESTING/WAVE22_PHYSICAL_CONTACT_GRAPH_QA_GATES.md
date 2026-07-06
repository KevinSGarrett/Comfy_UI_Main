# Wave 22 Physical Contact Graph QA Gates

## Mandatory gates
1. Source owner exists.
2. Target owner exists.
3. Source and target masks exist.
4. Contact edge type is valid.
5. Pressure/intensity profile is valid.
6. Occlusion profile is valid.
7. Duration profile is valid.
8. Audio force class is valid.
9. Output evidence exists.
10. Identity, pose, body proportion, hard anatomy, clothing, and frame boundaries are preserved.

## Blocked states
- floating body/object contact
- impossible overlap
- merged bodies
- broken hands/fingers/feet after contact
- no occlusion where occlusion is required
- wrong pressure response
- audio force contradicts visual force
