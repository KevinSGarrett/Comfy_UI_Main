# Wave 09 Video and Audio Proof-Bound Clarification

## The misunderstanding
The phrase `video/audio remain proof-bound` can sound like video/audio are not part of the system. That is **not** what it means.

## Correct meaning
Video and audio are first-class parts of the final hyper-realism system. The current uploaded Main Flow is mainly an image-generation canvas. It produces image outputs that can become video keyframes, references, and QA inputs. It does not by itself prove that the video or audio runtime lanes are already wired and working.

## What is included
The final system includes:
- image generation,
- image refinement,
- inpaint/detail,
- upscaling,
- video/GIF generation,
- temporal consistency,
- motion/pose/camera planning,
- audio generation,
- spatial audio,
- room ambience,
- Foley/contact sound,
- voice continuity,
- audio-video sync,
- QA and promotion across all of the above.

## What proof-bound means
`Proof-bound` means:
- do not mark a lane as production-ready until it has a workflow or module,
- do not promote from notes,
- do not promote from unrelated smoke tests,
- require ComfyUI/API execution proof when applicable,
- require concrete output files,
- require evidence manifests,
- require QA scoring,
- require runtime logs.

## Required evidence by modality

| Modality | Required proof |
|---|---|
| Image | workflow JSON, object_info, model availability, output images, evidence manifest, QA report |
| Video/GIF | video workflow/module, keyframes, output video/GIF, temporal QA, flicker/identity/pose continuity report |
| Audio | audio workflow/module, output audio, room/acoustic plan, voice/ambience/Foley report, AV sync report |
| Cross-modal | scene ID, character ID, environment ID, pass IDs, file manifests, promotion decision |

## Design decision
Video and audio should be separate runtime modules because they have different failure modes than still images. They must be connected to the same Scene Director, Character Bible, Environment Bible, Engine Router, and QA system.
