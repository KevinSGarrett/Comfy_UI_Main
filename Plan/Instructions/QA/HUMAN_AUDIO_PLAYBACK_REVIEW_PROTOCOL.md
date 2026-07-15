# Human Audio Playback Review Protocol

## Purpose

This protocol defines the irreducible human listening gate for production audio. Automation prepares and hash-binds the packet, verifies every technical prerequisite, validates the completed record, and updates project evidence. The reviewer supplies only the listening judgment.

## Eligibility

A candidate may enter human review only after decode, content/transcript, duration, loudness, clipping, applicable speaker-continuity, and applicable synchronization gates pass. A rejected or superseded candidate must not be sent for approval.

## Review packet

The request must identify the immutable audio or audio-video artifact by path, byte count, and SHA-256. It must include the expected transcript, character and voice profile, emotion class when supported, delivery style, intensity, pace, duration target, sync requirement, automated evidence bindings, required review sections and categories, and the minimum score.

The engine identity is hidden during the initial listening pass. This prevents preference for a tool name from replacing judgment of the artifact.

## Reviewer authority

Human authority uses `authority_type: human`. A reviewer must be allowlisted for one role, attest that they did not generate the artifact, disclose no conflict, review the exact hash, and record playback device and environment. A human must never be represented with fabricated model, model-version, or model-hash fields.

Playback review and final production authority are separate roles. Passing playback evidence does not itself authorize production promotion.

Final human production authority uses a separate hash-bound bundle and allowlist. The bundle binds the exact media artifact, prompt-alignment proof, and playback proof. Its authority must be different from the generator, prompt-alignment authority, and playback reviewer. An empty final-authority allowlist keeps promotion blocked without preventing playback review.

## Scoring

Each applicable category is scored from 0 through 5. The default minimum is 4.0 for exact content, intelligibility, character voice match, continuity, delivery style, intensity, pacing/timing, pronunciation, naturalness, and technical cleanliness. Mix balance and AV sync may be marked not applicable only with a specific reason.

For a short clip, loud, quiet, or transition sections may be not applicable when the artifact genuinely contains no such passage. Beginning, middle, and end remain required.

A passing record requires:

- final decision `PASS`;
- every applicable mandatory score at or above the request threshold;
- no high or critical defect;
- complete section coverage or justified not-applicable entries;
- verified request, artifact, evidence, and record hashes.

## Project updates

The validated proof may clear only the playback-review gate for the exact artifact hash. It does not clear speaker identity, contact ownership, production authority, global review, multimodal review, or final certification unless those independent gates also pass.
