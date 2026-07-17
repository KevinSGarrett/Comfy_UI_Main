# Wave64 Hyperreal Audio, AV Generation, and Spatial Intelligence Strategy

## Event-first architecture

Compile a canonical event graph before generating sound. Events bind source
ownership, visual cause, force/contact/material evidence, position, duration,
priority, continuity, and QA. The graph includes explicit silence and room tone;
the absence of a sound can be intentional evidence.

## Source selection

Represent source choice on three orthogonal axes. `origin_class` distinguishes
field/studio/voice recordings, procedural renders, neural text/audio/video
conditioning, and hybrids. `realization_action` distinguishes reuse, new
recording, neural generation, procedural synthesis, and layer assembly.
`derivation_state` tracks raw, segmented, prepared, transformed, layered,
spatially rendered, and mastered artifacts. Retrieval is an action, not an
origin; a neural asset may later be retrieved without becoming a recording.

Hard-filter sources for event class, duration, transient/loop behavior, sample
rate, channel layout, identity/material match, license/usage scope, installed
availability, certificate, and runtime envelope. Rank eligible candidates using
event-specific benchmark evidence, editability, spatial cleanliness, noise,
artifacts, continuity, cost, and uncertainty. Hybrid layers must name every
component and its purpose.

## Speech and nonverbal voice

Keep dry character speech immutable. Version pronunciation, language, emotion,
prosody, pace, pitch range, breath, effort, and nonverbal events. Align phonemes
and words, derive viseme candidates, and validate the mouth-region owner. Run
identity, intelligibility, pronunciation, timing, artifact, and performance QA
before acoustics. Never repair a voice identity defect with reverb or mix EQ.

## Foley and sound design

Bind transient, body, resonance, friction, debris, cloth, and tail layers to
visual force and material evidence. Repetition uses variation policies that
preserve source identity without obvious sample cycling. Generated layers are
separated from retrieved/recorded truth so future QA can learn by source method.

## Acoustic and spatial rendering

Use object/stem rendering with source/listener tracks, directivity, distance,
occlusion, geometry/IR evidence, early reflections, late reverb, and automation.
Keep dry stems. A panning curve inferred only from camera framing is a draft
unless scene geometry and source tracking support it.

## Mix and mastering

Preserve the stem graph and nondestructive recipe. Dialogue and critical events
receive intelligibility and masking gates. Measure peak, true peak, loudness,
range, dynamics, spectrum, phase, noise, discontinuity, and loop seams against a
versioned delivery profile. Render review and final masters separately.

## AV synchronization

Map all events through the canonical rational clock. Validate expected and
observed PTS, sample positions, frame boundaries, event-class tolerances, drift,
monotonic container timestamps, and exact frame/sample counts. Repair the
smallest event/span. Remuxing must not silently drop a terminal frame or sample.

## Learning

Every use writes an observation containing exact source/bundle, context,
assignment probability, settings, metrics, failures, repair, operator decision,
and promoted outcome. Learning jobs use held-out and shadow partitions to avoid
turning historical selection bias into false evidence.
