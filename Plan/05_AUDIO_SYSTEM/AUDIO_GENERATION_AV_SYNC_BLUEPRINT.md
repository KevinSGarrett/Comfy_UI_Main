# Audio Generation and AV Sync Blueprint

## Audio lanes

- dialogue/speech
- voice profile
- emotion/tone/pacing
- SFX
- foley
- ambience
- room tone
- music
- mix/timeline
- lip-sync/viseme tracks

## Audio planning order

```text
scene graph
→ dialogue plan
→ speech timing
→ foley/SFX cue plan
→ ambience/room tone/music plan
→ generation requests
→ audio manifests
→ master AV sync timeline
→ mix QA
→ final sync QA
```

## Required bindings

Every audio event must bind to:
- scene_id
- character_id or object_id when applicable
- start/end time
- purpose
- source event
- expected video frame range
- QA rule

## QA requirements

- correct speaker
- voice profile consistency
- speech intelligibility
- lip-sync/mouth-region ownership
- foley tied to actual contact/action
- ambience does not mask dialogue
- no clipping
- mix metadata passes true peak/risk thresholds
