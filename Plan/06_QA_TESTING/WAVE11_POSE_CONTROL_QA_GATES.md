# Wave 11 Pose Control QA Gates

## Gate 1 — Static Plan

- control-map plan validates against schema;
- every map has source/output path;
- every character has skeleton/mask binding;
- every route has engine family and compatible model slot.

## Gate 2 — Runtime Node Visibility

- DWPose/OpenPose node visible in object_info;
- depth node visible;
- normal node visible;
- Canny node visible;
- lineart node visible;
- ControlNet apply node visible.

## Gate 3 — Control Map Files

- files exist;
- dimensions match;
- hashes recorded;
- map type recorded;
- no missing required character maps.

## Gate 4 — Map-Specific QA

- pose: required keypoints visible;
- depth: foreground/background order correct;
- normal: plausible surface normals;
- Canny: useful edge density;
- lineart: clean contours;
- masks: correct ownership.

## Gate 5 — Final Output QA

- action matches request;
- identity stable;
- camera/framing correct;
- no limb/hand ownership mistakes;
- no map artifacts;
- promotion evidence written.
