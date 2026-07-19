# Wave64 Autonomous Sound Library, Generation, and QA Plan

## Library roles

The source library, generated-candidate store, and promoted generated library are separate:

- `source_library`: immutable externally supplied media.
- `generated_candidate_store`: immutable outputs awaiting QA; never selected for production reuse.
- `promoted_generated_library`: generated assets that passed provenance, rights, technical, semantic, timing, uniqueness, and applicable playback gates.

No content-based suppression is added. Eligibility is determined by technical fitness, rights, event compatibility, and QA.

## Autonomous creation routes

### Deterministic derivatives

Create controlled variants from eligible sources using sample-accurate transforms. Suggested bounded controls are event-family specific and include pitch, duration, envelope, transient shaping, EQ, microtiming, stereo perspective, room response, and gain. A transform may not move the measured event anchor outside tolerance.

### Layered composites

Combine approved layers when no single recording matches the event. Each layer retains independent provenance and can be remixed or removed. The composite receives its own canonical PCM hash and QA record.

### Procedural sounds

Use deterministic physical/noise synthesis for simple swishes, whooshes, resonances, low-frequency impacts, room tones, and transition elements when the target event is appropriate. Procedural parameters and random seeds are provenance.

### Text-to-audio

Generate short candidates from a structured prompt compiled from event type, actor/object role, contact pair, material, footwear, force, motion, room, duration, perspective, and explicit exclusions. Generate an ensemble of seeds and evaluate all candidates; do not repeatedly reroll without a bounded decision rule.

### Audio-to-audio

Create a variation from an eligible source or promoted generated asset. Record source hash, conditioning prompt, strength/noise level, inpaint/continuation bounds, seed, and engine identity. Reject candidates that lose the target transient, timing, material, or event identity.

### Video-to-audio

Use the source video and canonical event script to generate continuous or complex Foley. Generated tracks remain candidates and should be decomposed or blended with deterministic one-shots when exact contact timing requires it.

## Structured generation prompt

```json
{
  "event": "footstep.heel_strike",
  "source": "right_heel",
  "target_material": "hardwood",
  "footwear": "hard_heel",
  "force": "medium",
  "duration_seconds": 0.65,
  "attack": "sharp_transient",
  "decay": "natural_short_wood_room",
  "perspective": "two_meters_camera_right",
  "room": "furnished_bedroom_wood_floor",
  "exclude": ["speech", "music", "multiple_steps", "crowd", "strong_pre_reverb"]
}
```

Prompts are generated from structured state, not free-form prose alone.

## Generated-sound QA

Every candidate is checked for:

- exact decode and duration;
- canonical PCM hash and near-duplicate similarity;
- silence, clipping, DC offset, dropouts, noise, and truncation;
- onset count, transient position, attack, sustain, release, and tail;
- event/text semantic similarity from more than one signal where possible;
- expected versus unexpected audio classes;
- material, body/object role, force, and acoustic fit;
- source-conditioning preservation for audio-to-audio;
- contact/transient alignment for video-to-audio;
- room dryness/reverb compatibility;
- loudness and true peak;
- model, seed, prompt, input, output, environment, rights, and attribution provenance;
- diversity versus existing library and recent scene usage;
- full-scene mix compatibility.

Metrics such as CLAP similarity and Frechet Audio Distance are supporting measurements, not sole production authorities. Generated audio evaluation must include event-specific tests and applicable playback review.

## Library promotion

Promotion creates a registry record with:

- generated asset ID and version;
- output container and canonical PCM hashes;
- parent/source hashes and derivative chain;
- engine/model/revision/hash/config/seed;
- structured prompt and event manifest hashes;
- license/output-rights decision;
- normalized technical metadata;
- semantic and acoustic tags;
- onset/trim/decay/segment metadata;
- autonomous QA report hash;
- playback review hash when required;
- promotion authority and timestamp;
- revocation state and supersession pointer.

Promotion never overwrites source files or earlier generated versions.

## Retry policy

1. Fix deterministic contract or implementation defects before regenerating.
2. Reuse passed stages and cached features.
3. Generate a bounded candidate batch with declared seeds.
4. Stop when a candidate passes or the route budget is exhausted.
5. Route to another engine or broader retrieval class only through an explicit decision.
6. Preserve rejected candidates as negative evidence.

## Production use policy

The selector may use only source assets and promoted generated assets. Staged generated candidates may appear in evaluation mixes but cannot be represented as reusable production-library sounds. Human listening is minimized to the irreducible final playback decision defined by the project protocol; all packet preparation, measurements, comparisons, and validation remain autonomous.
