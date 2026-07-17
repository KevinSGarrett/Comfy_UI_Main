# Wave64 Pass-Level Engine/Model Specialization Architecture

## Core decision

The routing unit is an execution stack, not a brand name:

```text
engine family
+ exact model revision and SHA-256
+ workflow/API graph revision and SHA-256
+ VAE/text encoder/scheduler
+ LoRA/ControlNet/reference/specialist adapters
+ custom-node and Python runtime lock
+ precision/offload/hardware profile
+ capability-scoped benchmark certificate
```

Every base, refinement, specialist, temporal, speech, Foley, music, and AV pass requests a capability. The deterministic router filters and ranks execution stacks independently for that pass.

## Capability graph

The Engine/Model Capability Graph includes:

- engine families and exact model cards;
- supported modalities, pass intents, input/output types, edit modes, masks, controls, references, adapters, native resolutions/durations, and limits;
- character adapter bindings and per-instance constraints;
- certified target regions and content/scene classes;
- runtime/hardware/precision/offload envelopes;
- evidence/promotion/freshness state;
- decoded image, masked crop, control-map, timeline, audio-event, and AV bridge edges;
- explicit incompatibility edges;
- rollback and fallback relationships.

## Route request

A pass route request binds job/run/pass IDs; scene/shot/take; intent; modality; exact input hashes; target instances/regions/spans/stems; protected ownership; required controls/edit types; character revisions; MaskFactory authority; output contract; resolution/duration; runtime/cost budget; evidence freshness; and whether fallback is allowed.

## Route decision

The decision includes all evaluated candidates, hard eligibility failures, ranked eligible candidates, selected execution stack, benchmark scope, resource plan, bridge plan, fallback policy, prohibited substitutions, QA requirements, and decision hash. A blocked decision is a valid result.

## Specialist regional execution

A model or LoRA available only under one engine may be valuable. It is used only when:

1. its exact stack is registered and runtime-proven;
2. its capability card covers the target region and requested edit;
3. the target belongs to an unambiguous character instance;
4. target and protected masks have sufficient authority and matching transforms;
5. crop, padding, resolution, denoise/strength, and composite rules remain within the certificate;
6. the source parent is immutable;
7. target, protected-region, identity/morphology, seam, and whole-artifact gates pass.

If the specialist cannot satisfy an edit/control type, the router blocks or chooses a separately certified fallback. It never loads a similarly named asset from another model family.

## Learning and champion selection

Benchmarks are bucketed by capability, engine stack, model revision, adapter bundle, character/reference condition, character count, target region, mask tier, resolution/duration, hardware/precision, and scene/content class. Promotion requires sample floors, hard-bucket non-regression, failure/OOM/determinism evidence, and rollback proof. The router selects a Pareto champion per bucket, not a universal leaderboard winner.

Runtime outcomes update evidence only through immutable benchmark records. A single successful generation cannot promote an execution stack.

## Current research candidates

The registry may contain unselected research candidates for future benchmark intake. Listing is not installation or authority:

- image/global/reference edit: FLUX.2, Qwen-Image-2512, Qwen-Image-Edit-2511;
- video/control/animation: Wan2.2, HunyuanVideo-1.5, LTX-2.3;
- speech: Qwen3-TTS, Fun-CosyVoice3;
- Foley/video-to-audio: HunyuanVideo-Foley, MMAudio;
- SFX/music: Stable Audio 3, ACE-Step 1.5;
- lip-sync/dubbing: LTX LipDub, LatentSync, Wan S2V candidates.

Every candidate starts `research_unselected_not_installed_not_runtime_proven_not_promoted` unless exact project evidence proves otherwise.
