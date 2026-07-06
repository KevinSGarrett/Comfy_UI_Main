# Wave 21 Soft-Body Material Profile QA Gates

## Mandatory gates
1. Region mask exists and is owned.
2. Material profile exists and is valid.
3. Contact/support context exists when compression is requested.
4. Denoise stays inside the pass profile range.
5. Evidence shows the target material behavior.
6. Identity, pose, body proportions, frame integrity, clothing/fabric continuity, and hard anatomy are preserved.

## Hard fail flags
- unsupported compression
- mask bleed
- body-proportion drift
- temporal flicker
- floating contact
- material profile mismatch
