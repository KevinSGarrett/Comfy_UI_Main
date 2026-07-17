# Wave64 Hyperreal Video Generation and Temporal Intelligence Strategy

## Representation

Every shot binds a rational clock, camera/lens state, approved boundary
keyframes, per-character identities, pose/skeleton, depth, masks, contacts,
surface/material state, lighting/exposure/color state, motion channels, audio
events, and continuity parents. Each decoded frame registers tracks, ownership,
visibility, flow, defects, and immutable artifact identity.

## First-pass selection

Choose the first temporal route from the request and available authority:

- keyframe-to-video when an approved image is the visual authority;
- image-to-video for looser motion around one source;
- reference-guided when choreography/camera timing authority exists;
- text-to-video only when identity/pose authority is intentionally weak;
- interpolation between approved boundaries for controlled transitions;
- extension only with locked overlap handles and continuity QA.

The controller can divide a shot into route segments. A hero face span may use
one engine while a wide motion span uses another, but decoded bridge and
boundary certification are mandatory.

## Motion layers

Primary action, gaze/blink/breath, muscle/effort, contact/compression,
hair/fabric/accessory follow-through, fluids/particles, camera movement,
stabilization, and settling each receive independent amplitude, frequency,
driver, phase, and physical constraint contracts. Reference motion is evidence,
not permission to copy identity or unsupported scene state.

## Temporal multipass order

1. shot proxy and camera/choreography validation;
2. approved boundary and anchor keyframes;
3. base temporal generation;
4. identity and ownership stabilization;
5. anatomy, hands, face, gaze, and mouth stabilization;
6. contact, occlusion, depth, and interaction stabilization;
7. surface/material temporal lock;
8. hair/fabric/secondary-motion refinement;
9. lighting, reflection, exposure, color, blur, and grain continuity;
10. localized defect repair;
11. temporal upscale and delivery encode;
12. regional, boundary, whole-clip, and long-form QA.

The order is a dynamic DAG: a pass is included only when its defect/objective
requires it. Every pass declares targets, protected regions, parents, bridge,
denoise/change budget, metrics, and rollback.

## Multi-character video

Each character keeps a scene instance ID, identity revision, skeleton, depth,
silhouette, masks, visibility, contact roles, and render order. Contact is
reciprocal and time-bound. Occlusion never transfers identity. Repair masks may
overlap only under an explicit conflict policy, and all other characters are
protected by default.

## QA scorecard

Use deterministic geometry/signal metrics, specialist identity and temporal
models, and qualified calibrated autonomous VLM/critic review for the
`core_autonomous_runtime` decision. Human-blinded comparison belongs only to the
optional `independent_perceptual_calibration` profile or a separately recorded
explicit user override; its absence cannot block or revoke core. Report per-character,
per-region, per-span, per-shot, and project aggregates. Required slices include
camera motion, occlusion, low light, fast motion, dialogue, hands, contact,
multi-character crossings, hair/fabric, reflections, and long-form cuts.

No metric is accepted without a version, threshold, confidence interval,
evidence reference, and calibration snapshot. Blocking failures cannot be
averaged away.
