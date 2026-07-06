# Wave 09 Environment Continuity Runtime Lifecycle

## Lifecycle
```text
environment draft
→ environment reference pack
→ static validation
→ image smoke test
→ image continuity test
→ video keyframe test
→ video temporal test
→ audio environment test
→ AV sync environment test
→ promotion
```

## Evidence required
- environment manifest,
- room profile,
- lighting rig,
- prop manifest,
- material/surface manifest,
- scale reference,
- scene plan,
- pass plan,
- output files,
- file hashes,
- QA scores,
- promotion decision.

## Environment continuity metrics
- layout consistency,
- camera perspective consistency,
- lighting consistency,
- shadow consistency,
- prop consistency,
- material consistency,
- scale plausibility,
- character-environment interaction,
- video temporal stability,
- audio ambience match,
- AV sync plausibility.

## Failure handling
If a single pass breaks the environment:
1. mark the pass failed,
2. keep the previous accepted output,
3. retry with stricter environment constraints,
4. use masked/inpaint correction if localized,
5. escalate to manual review if repeated.
