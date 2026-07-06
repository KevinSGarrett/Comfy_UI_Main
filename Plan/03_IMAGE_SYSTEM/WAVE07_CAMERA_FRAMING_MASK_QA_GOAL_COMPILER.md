# Wave 07 Camera, Framing, Mask, and QA Goal Compiler

## Purpose

Camera, masks, and QA are tied together. The Scene Director must compile them together, not separately.

## Camera-to-QA mapping

| Camera requirement | QA goal |
|---|---|
| full body | qa_camera_framing + head/feet visible |
| half body | qa_camera_framing + correct crop line |
| close-up | qa_camera_framing + face detail |
| wide room | qa_environment_scale + subject visibility |
| multi-character | qa_character_count + instance separation |
| low angle | qa_perspective + no distortion |
| shallow DOF | qa_subject_sharp + background blur acceptable |

## Mask-to-QA mapping

| Mask type | Required evidence |
|---|---|
| macro person mask | overlay + no background bleed |
| major body region | overlay + before/after crop |
| minor region | crop + edge check |
| micro texture | crop at native/upscaled resolution |
| nano polish | before/after crop |
| contact mask | source/target/contact-zone overlay |
| protect mask | protected-region before/after comparison |

## Camera plan fields

The Director must produce:

- shot type
- body crop
- subject count visible
- camera distance
- camera height
- angle
- lens/focal length hint
- depth of field
- occlusion warnings
- safe margins
- environment scale notes
- QA requirements

## Mask plan fields

The Director must produce, when needed:

- mask ID
- scale
- target entity
- target region
- purpose
- source entity/source region for contact
- contact zone
- feather/dilate/erode settings
- protect regions
- QA overlay requirement

## QA goal fields

The Director must produce:

- QA goal ID
- scope
- checks
- evidence required
- blocking yes/no
- promotion required yes/no

## Failure routing

### Camera failure

If camera/framing fails, rerun base or layout. Do not patch with detail.

### Mask failure

If mask bleed occurs, rerun mask generation or regional pass. Do not promote.

### Engine compatibility failure

If a selected model is wrong-engine, block the pass before runtime.

### Contact failure

If source/target contact is unreadable, rerun contact graph, pose plan, or contact pass. Do not apply final polish over a broken contact.
