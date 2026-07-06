# Wave 20 Current Status

## Status
PASS — cumulative pack created.

## Runtime status
Runtime hard-anatomy repair is not marked promoted yet. This wave adds contracts, registries, schemas, implementation instructions, App Mode controls, QA gates, and local validation scripts. Production promotion still requires real generated crops, masks, before/after images, evidence reports, and QA.

## Source inventory
- Main Flow nodes observed: 356
- Main Flow links observed: 91
- SaveImage lanes observed: 8
- Mask input slots observed: 2
- Low-denoise anchors observed: 2
- ControlNet-related nodes observed: 2
- Hard-anatomy/detail LoRA signals observed: 80
- Tracker rows observed: 12887
- Tracker columns observed: 73
- Tracker hard-anatomy-related rows observed: 8355

## Implementation readiness
Wave 20 is ready for local integration work:
1. detect hard-anatomy regions,
2. create crop and mask contracts,
3. run strict crop/detail repair lanes,
4. score local anatomy evidence,
5. rerun failed local regions only,
6. block promotion if identity, pose, frame, contact, or body shape drifts.
