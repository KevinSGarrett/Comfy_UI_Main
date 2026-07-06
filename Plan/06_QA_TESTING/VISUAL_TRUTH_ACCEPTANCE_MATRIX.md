# Visual Truth Acceptance Matrix

| Target | Required evidence | Blockers |
|---|---|---|
| Character identity | face crop, reference comparison, prompt/reference manifest | identity drift, wrong face, hair/outfit drift |
| Body shape | full body crop, silhouette overlay, mask/control evidence | wrong waist/hips/stomach, broken spine, chopped edit |
| Pose/camera | pose map, depth map, full image crop | wrong pose, wrong angle, impossible body orientation |
| Hands | left/right hand crops, hand mask, hand QA | fused fingers, extra/missing fingers, unreadable hand |
| Cellulite/skin detail | target body-part mask, crop before/after | detail outside mask, disease-like artifacts, over-sharpening |
| Fabric | clothing mask, fabric crop | skin/fabric bleed, fake texture, moire/banding |
| Contact/deformation | hand mask, target mask, contact crop | no contact, impossible collision, melted fingers, no pressure when requested |
| Multi-character | instance masks, per-character crops | merged bodies, wrong count, identity swap |
| Video/GIF | frame crops, temporal report | flicker, drift, merged frames, frame failures |
| Audio/AV | timing manifest, mix QA, lip-sync QA | wrong speaker, desync, clipping, unintelligible dialogue |
