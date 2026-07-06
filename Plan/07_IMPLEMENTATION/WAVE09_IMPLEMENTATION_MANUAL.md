# Wave 09 Implementation Manual

## Step 1 — Create environment records
Create a JSON record for every reusable environment:
- environment ID
- version
- type
- room profile
- lighting rig
- material/surface profiles
- prop registry
- scale anchors
- reference pack
- continuity rules.

## Step 2 — Build reference packs
For each environment, collect:
- room reference images,
- layout sketches,
- camera angle references,
- lighting references,
- material swatches,
- prop references,
- depth maps if available,
- edge maps if available,
- masks if available,
- audio ambience notes,
- video camera path notes.

## Step 3 — Bind Scene Director
Update the Scene Director so every scene plan has:
- `environment_binding`,
- `camera_plan`,
- `lighting_plan`,
- `prop_plan`,
- `material_surface_plan`,
- `scale_reference_plan`,
- `qa_goals`.

## Step 4 — Validate locally
Run:
```powershell
python .\07_IMPLEMENTATION\scripts\run_wave09_local_validation.py --root .
```

## Step 5 — Route image/video/audio separately
Image, video, and audio use the same scene/environment IDs, but each modality has its own runtime workflow and proof gate.

## Step 6 — Promote only with evidence
Do not promote notes, planned nodes, or placeholder workflows. Promotion requires output files, hashes, QA reports, and explicit decisions.
