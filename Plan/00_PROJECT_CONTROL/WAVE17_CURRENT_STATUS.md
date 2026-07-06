# Wave 17 Current Status

## Status
PASS — cumulative pack created.

## Runtime status
Runtime body correction is not marked proven yet. This wave adds contracts, registries, schemas, implementation instructions, and local validation scripts. Real promotion still requires generated images, mask artifacts, evidence reports, and QA.

## Source inventory
- Main Flow nodes observed: 356
- Main Flow links observed: 91
- SaveImage lanes observed: 8
- Mask input slots observed: 2
- Low-denoise anchors observed: 2
- Body-shape/body-proportion LoRA signals observed: 37
- Tracker rows observed: 12887
- Tracker body-shape related rows observed: 243

## Implementation readiness
Wave 17 is ready for local integration work:
1. generate person-instance and body-region masks,
2. compile a body correction contract,
3. patch an inpaint/refine workflow,
4. run low-denoise passes,
5. score body-shape evidence,
6. rerun or block if QA fails.
