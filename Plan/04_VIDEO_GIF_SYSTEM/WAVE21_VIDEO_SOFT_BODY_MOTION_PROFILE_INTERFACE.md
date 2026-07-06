# Wave 21 Video Soft-Body Motion Profile Interface

Video/GIF soft-body behavior requires temporal proof.

## Required video metadata
- tracked region mask ids
- material profile id per region
- motion profile id
- frame window
- contact/support timeline
- damping/rebound expectation

## Temporal QA checks
- no flicker in deformation
- no identity drift
- no pose drift outside allowed motion
- no silhouette teleporting
- rebound timing is plausible
- material profile remains stable across frames
