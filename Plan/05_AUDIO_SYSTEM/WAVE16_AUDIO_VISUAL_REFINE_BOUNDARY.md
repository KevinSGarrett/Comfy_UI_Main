# Wave 16 — Audio/Visual Refine Boundary

Audio remains in scope for the full hyper-realism system, but image refinement must not create visual states that contradict the planned audio scene.

## Audio-sensitive visual details

Refine passes must preserve:

- character count;
- mouth state when dialogue/speech is planned;
- room/environment for acoustics;
- prop contact relevant to sound;
- visible action timing for future video/audio sync.

## Boundary rule

Image refinement does not generate final audio. It exports visual state metadata that the audio planner can use later.

## Exported fields for audio

Refined image artifacts should provide:

- character ids;
- visible mouth state if known;
- room/environment id;
- material/surface ids;
- prop ids;
- action/contact notes;
- video handoff eligibility;
- audio continuity warnings.

## QA interaction

If a refine pass changes mouth expression, prop interaction, or environment materials, it may invalidate future audio planning and must be flagged.
