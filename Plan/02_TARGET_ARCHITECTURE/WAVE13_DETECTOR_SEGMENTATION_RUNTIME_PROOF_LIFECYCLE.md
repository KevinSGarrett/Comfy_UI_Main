# Wave 13 — Detector, Segmentation, and Runtime Proof Lifecycle

## Expected detector/segmentation stages

1. Generate or receive source image.
2. Detect person instances.
3. Detect body regions where available.
4. Generate fabric/object/contact masks as needed.
5. Normalize mask names and ownership.
6. Validate mask coverage and edges.
7. Route masks to workflow modules.
8. Save mask artifacts.
9. Score mask evidence.
10. Promote only if masks and output evidence pass.

## Runtime proof requirements

A promoted Mask Factory run needs:

- contract JSON,
- mask PNG or equivalent mask tensor evidence,
- per-mask metadata,
- before/after image evidence,
- score report,
- blocker list,
- output SHA256 or file fingerprint.

## Why this matters

Without runtime evidence, a mask system is only an architecture plan. Runtime proof is the difference between a staged system and a production-ready system.
