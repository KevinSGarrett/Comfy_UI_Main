# Wave 13 — Implementation Manual

## Local-first implementation

1. Compile a mask contract from the Scene Director plan.
2. Validate mask contract JSON.
3. Generate or collect masks.
4. Build mask evidence manifest.
5. Score mask evidence.
6. Patch workflow modules only with validated masks.
7. Run ComfyUI generation.
8. Collect output evidence.
9. Promote only when evidence passes.

## Suggested local folders

```text
C:\Comfy_UI_Main\Implementation\masks\contracts
C:\Comfy_UI_Main\Implementation\masks\runtime
C:\Comfy_UI_Main\Implementation\masks\evidence
C:\Comfy_UI_Main\Implementation\masks\reports
```

## Required naming

```text
scene_id__person_001__whole_person__major.png
scene_id__person_001__face__minor.png
scene_id__person_001__fabric_001__minor.png
scene_id__contact_001__person_person_boundary__minor.png
```

## EC2 rule

EC2 is not needed for contract validation. EC2/GPU use begins only when real detector, segmentation, mask generation, or ComfyUI runtime proof is required.
