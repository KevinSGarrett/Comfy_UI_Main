# Mask Factory Specification

## Purpose

The Mask Factory creates spatial truth. It decides where a pass is allowed to modify pixels.

## Required masks

### Entity masks
- character_A_mask
- character_B_mask
- character_C_mask
- character_D_mask
- character_E_mask
- object masks
- background mask

### Body-part masks
- face
- hair
- eyes/mouth if needed
- neck
- torso
- stomach
- waist
- hips
- thighs
- legs
- hands
- feet
- clothing
- fabric
- exposed skin
- contact zone

### Contact masks
- source hand/object mask
- target body/object mask
- contact edge mask
- falloff mask
- shadow/occlusion region mask

## Mask size rules

- Small mask: pores, blemishes, cellulite texture, fabric texture, finger/nail repair.
- Medium mask: thigh cellulite area, hair patch, clothing fold section, local hand/body contact.
- Large mask: body silhouette, stomach size, waist/hip ratio, outfit reshaping.
- Full rerun: character count, pose, camera, composition, major body orientation.

## Mask failure rules

Reject mask if:
- it includes the wrong character
- it cuts anatomy too tightly
- it excludes required surrounding context
- feathering is missing
- mask crosses a seam without context
- mask preview does not match target region
- target region cannot be confidently identified

## Chopped-body prevention

For body-shape edits:
- include surrounding anatomy
- include clothing seams
- include both sides of the shape boundary
- use depth/edge guidance
- use moderate denoise
- QA before/after overlay
