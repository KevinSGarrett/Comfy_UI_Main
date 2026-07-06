# Wave 10 ComfyUI Patching Instructions

## Target Nodes

Patch where supported:

- `EmptyLatentImage`
- `EmptySD3LatentImage`
- `CLIPTextEncode`
- `SaveImage`
- reference image loaders
- IPAdapter settings
- ControlNet settings when proven

## Width and Height

Use the camera plan resolution:

```json
"resolution": { "width": 1024, "height": 1280 }
```

## Prompt Patching

Add camera module to the positive prompt:

```text
full body, head to toe visible, feet visible, natural 35mm lens look, eye-level camera, centered framing
```

Add crop guard to the negative prompt:

```text
cropped feet, cropped hands, cut off head, accidental close-up, warped perspective
```

## Save Prefix

Save outputs under a camera-aware prefix:

```text
Main_Flow/Camera/full_body
Main_Flow/Camera/close_up
Main_Flow/Camera/two_shot
```

## Runtime Proof

A patched workflow is not promoted until it renders and passes QA.
