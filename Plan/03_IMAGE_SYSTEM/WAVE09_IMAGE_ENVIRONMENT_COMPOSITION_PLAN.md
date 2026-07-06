# Wave 09 Image Environment Composition Plan

## Image pass responsibilities
The image system must use the environment plan for:
- base prompt composition,
- camera angle,
- room layout,
- prop placement,
- lighting,
- shadows,
- reflections,
- material appearance,
- inpaint masks,
- background detail,
- upscale preservation,
- final QA.

## Base pass
The base image pass should establish:
- environment ID,
- room profile,
- primary character anchor,
- camera anchor,
- lighting rig,
- major props,
- scale anchors,
- material/surface targets.

## Detail/inpaint pass
The detail pass must not randomly redesign the room. It should target:
- contact shadows,
- local material detail,
- localized prop repairs,
- reflection fixes,
- background cleanup,
- surface texture,
- lighting continuity.

## Upscale pass
The upscale pass must preserve:
- layout,
- identity,
- lighting direction,
- shadow boundaries,
- prop shape,
- scale anchors,
- material cues.

## Negative constraints
Every environment pass should carry negatives for:
- warped room geometry,
- inconsistent scale,
- floating objects,
- missing contact shadows,
- impossible reflections,
- duplicated furniture,
- changed wall/window/door layout,
- wrong light direction,
- plastic-looking surfaces,
- background hallucination.

## Output evidence
Every image output should record:
- environment ID/version,
- lighting rig,
- camera anchor,
- pass ID,
- workflow ID,
- seed,
- model stack,
- output path,
- dimensions,
- hash,
- QA status.
