# Wave 10 Workflow Patching Camera Control Strategy

## Purpose

Camera plans must become workflow changes, not just text.

## Patch Targets

### Latent Size

Patch width/height to match shot size and aspect ratio.

```text
full_body → vertical 4:5 or 2:3
close_up → 1:1 or 4:5
wide/two-shot → 16:9 or 3:2
```

### Prompt Modules

Insert structured camera prompt modules:

```text
shot size
lens look
camera height
camera angle
framing margin
depth of field
focus target
crop guard
```

### Reference Routing

Reference images should be routed based on shot type:

```text
identity close-up → face reference/IPAdapter
full body → body/outfit/pose reference
pose/action → pose/depth/openpose when proven
environment → room reference/environment profile
```

### Control Maps

ControlNet/pose/depth/OpenPose should be used only after local object_info and runtime proof.

### Save Prefixes

Save prefix should include camera intent:

```text
Main_Flow/Camera/full_body
Main_Flow/Camera/close_up
Main_Flow/Camera/two_shot
```

## Patch Manifest

Each run should create a patch manifest with:

- source workflow
- camera plan id
- patched nodes
- old values
- new values
- expected output prefixes
- validation status
