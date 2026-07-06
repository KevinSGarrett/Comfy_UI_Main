# Motion Physics Without Reference Video or 3D

## Decision

The system can create approximate GIF/video motion without reference video or Blender/3D by using planned keyframes, pose/depth/mask interpolation, motion curves, and frame repair. It cannot guarantee true physical simulation from text alone, so QA must be strict.

## GIF and video are both frame pipelines

The system should generate frame sequences first, then export:

- GIF for short review loops and quick motion tests,
- MP4/WebM for higher-quality playback,
- image sequence for QA and frame repair.

## Soft-body motion approximation

```text
Frame 000: neutral / pre-contact
Frame 008: first contact
Frame 016: maximum compression
Frame 024: release / rebound
Frame 032: settle
```

Each keyframe requires:

- same character IDs,
- same identity references,
- compatible pose skeletons,
- consistent depth maps,
- consistent body/contact masks,
- surface/body-state continuity,
- audio force markers if audio is present.

## Required QA

- identity does not drift,
- body shape does not jump,
- contact point stays assigned,
- motion does not flicker,
- soft-body deformation follows planned phase,
- hands remain readable,
- no extra bodies/limbs appear,
- final GIF/video matches frame timeline.
