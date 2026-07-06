# Wave 10 Scene Director Camera Binding

## Role

The Scene Director converts user wording into a structured `camera_plan`.

## Input Examples

```text
full body
half body
close-up
wide angle
zoomed in
overhead
low angle
two people
group shot
show the room
focus on hands
```

## Output

The Scene Director must produce:

```json
{
  "shot_size": "full_body",
  "lens_profile": "classic_35mm",
  "camera_angle": "eye_level",
  "framing": {},
  "depth_plan": {},
  "subjects": [],
  "qa_goals": []
}
```

## Binding Rules

- User wording is interpreted, but structured fields become the source of truth.
- Character Bible and Environment Bible must be consulted before camera finalization.
- App Mode values may override defaults but must still pass validation.
- Workflow compiler cannot run if required camera fields are missing.
- QA cannot promote if the generated image/video does not match the camera plan.

## Conflict Handling

If a request conflicts, the system resolves in this order:

1. Explicit user instruction
2. Character Bible constraints
3. Environment/room constraints
4. Modality constraints
5. Camera registry defaults
6. QA safety/quality gates

Example conflict:

```text
Request: full body close-up
Resolution: choose either full_body OR close_up; do not silently mix. If intent is body detail, use detail_insert or three_quarter_body.
```
