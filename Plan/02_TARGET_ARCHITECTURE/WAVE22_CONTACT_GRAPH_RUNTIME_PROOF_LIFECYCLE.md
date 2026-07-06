# Wave 22 Contact Graph Runtime Proof Lifecycle

## Required proof
A graph edge is runtime-proven only when all required artifacts exist:

- source image id
- target image id / output path
- source region mask
- target region mask
- contact edge contract
- before/after crop evidence
- occlusion report
- deformation report
- preservation report
- audio force metadata record

## Hard block
Never promote from:
- prompt text only
- LoRA name only
- detector-free guesses
- unrelated smoke output
- missing mask ownership
