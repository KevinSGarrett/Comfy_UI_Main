# Wave 07 Structured Plan Test Matrix

## Test group 1 — Basic image request

Input:

```text
Create a hyperreal image of one character in a room.
```

Expected:

- primary intent = image_single_hyperreal_character
- scene graph has one character
- camera plan exists
- engine route exists
- pass plan has base generation
- QA goal plan has basic file, scene intent, camera, anatomy

## Test group 2 — Full body framing request

Input:

```text
Make it full body and do not crop the feet.
```

Expected:

- camera shot type = full_body
- crop rule = head_to_feet_visible
- QA includes qa_camera_framing
- failure route says rerun base/camera if crop fails

## Test group 3 — Regional detail request

Input:

```text
Add realistic skin/fabric detail only in the selected area.
```

Expected:

- regional mask plan exists
- protect regions exist
- pass type = skin_material_microdetail or fabric_detail
- QA includes mask no-bleed before promotion

## Test group 4 — Body shape correction

Input:

```text
Adjust silhouette/proportion without changing the room.
```

Expected:

- body target region defined
- background protect mask defined
- pass type = body_shape_proportion
- QA includes silhouette and no-background-change checks

## Test group 5 — Contact/deformation request

Input:

```text
Show convincing contact/pressure between a hand/object and target region.
```

Expected:

- contact graph exists
- source/target/contact-zone masks exist
- required visual effects include occlusion/shadow/deformation
- QA includes contact readability and no fused anatomy

## Test group 6 — Multi-character scene

Input:

```text
Two characters in a realistic scene.
```

Expected:

- two character instances
- depth order defined
- character-count QA
- no merged people QA
- instance masks required

## Test group 7 — Video/GIF request

Input:

```text
Make this into a short GIF with motion.
```

Expected:

- target output = gif
- keyframe plan exists
- temporal QA exists
- video engine route exists
- approved keyframes required before final video

## Test group 8 — Audio/AV request

Input:

```text
Add synced foley and room ambience.
```

Expected:

- audio timeline exists
- room acoustics exists
- force/contact event mapping exists when contact graph exists
- AV sync QA exists

## Test group 9 — Model-selection request

Input:

```text
Find the best models for this scene from our Civitai library.
```

Expected:

- model-selection intent
- Civitai metadata lookup plan
- engine family compatibility checks
- blocked/rejected models listed
- missing metadata refresh jobs created

## Test group 10 — Wrong-engine prevention

Input:

```text
Use a Pony LoRA with Flux2.
```

Expected:

- plan may record request
- router compatibility status blocks direct mix
- bridge-only alternative proposed if valid
- no direct mixed pass created
