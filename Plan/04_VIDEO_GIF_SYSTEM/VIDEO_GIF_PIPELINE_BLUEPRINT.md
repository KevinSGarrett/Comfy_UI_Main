# Video/GIF Pipeline Blueprint

## GIF and video share the same frame pipeline

A GIF is a frame sequence with a different export container. The system should plan frames first, then export to GIF, MP4, or WebM.

## No-reference-video strategy

When no reference video or 3D simulation exists:

```text
approved still keyframe
→ motion plan
→ keyframe states
→ pose/depth/mask per keyframe
→ interpolation
→ video/GIF generation
→ per-frame QA
→ frame repair
→ export
```

## Soft-body approximation sequence

Example states:
- frame 0: no contact / neutral
- frame 8: light contact
- frame 16: maximum compression
- frame 24: release
- frame 32: settle

Each state needs:
- pose map
- depth/normal map
- body masks
- contact-zone mask
- identity reference
- contact QA

## Required outputs

- frames directory
- keyframe manifest
- control-map manifest
- per-frame QA report
- temporal QA report
- repaired frames manifest
- export manifest
