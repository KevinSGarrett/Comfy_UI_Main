# Wave 12 Scene Director, Camera, and Pose Binding

Wave 12 binds three upstream plans:

- Scene Director intent.
- Camera/framing plan.
- Pose/control-map plan.

The output is a frame composition contract.

## Required binding fields

- Expected character count.
- Character IDs and slots.
- Shot size.
- Body visibility profile.
- Crop safety margin.
- Allowed and forbidden crop points.
- Character spacing plan.
- Occlusion plan.
- Pose skeleton IDs.
- Camera plan ID.

If any of these are missing, the compiler should block runtime execution or fall back to a conservative default, depending on the workflow mode.
