# Wave 08 — Character Image Continuity Plan

## Purpose

Every image pass must know which character it is modifying and which identity fields must remain stable.

## Image Continuity Inputs

- Character Bible
- reference pack manifest
- scene character bindings
- camera/framing plan
- mask plan
- engine route
- model selection plan
- QA goals

## Image Pass Types

| Pass | Character Concern | QA Requirement |
|---|---|---|
| base generation | count, silhouette, face/hair/outfit approximation | count + identity rough match |
| face reference | face structure | face identity match |
| body shape | silhouette/proportions | body profile match |
| skin detail | tone/texture/markers | no marker loss or incorrect transfer |
| hair detail | color/length/style | hair profile match |
| outfit/fabric | clothing continuity | outfit profile match |
| inpaint/detail | localized correction | no global identity drift |
| upscale | preserve all character traits | before/after continuity check |

## Character Continuity Output

Each generated image should produce a continuity report containing:

- output path
- character_id/version
- pass id
- reference pack id
- used models/LoRAs
- mask ids
- locked traits checked
- failures and rerun instructions
- promotion status

## Base vs Detail Philosophy

The base pass establishes scene layout and approximate character identity. Detail passes refine targeted regions. If the base pass gets the wrong body/face/character count, do not overuse inpainting; rerun the base or control pass.
