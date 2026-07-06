# Wave 08 Implementation Manual

## Step 1 — Create Character Registry

Create:

```text
C:\Comfy_UI_Main\Implementation\characters\character_identity_registry.json
```

Every reusable character gets a stable `character_id`.

## Step 2 — Create Character Pack

Create one folder per character/version:

```text
C:\Comfy_UI_Main\character_packs\char_<slug>001```

Do not put private or large reference media into Git. Store those locally/S3/EC2 and keep manifests in Git.

## Step 3 — Build Character Bible

Create:

```text
character_packs\char_<slug>001ible\character_bible.json
```

Populate:

- identity locks
- body profile
- skin profile
- hair profile
- outfit profile
- voice profile
- reference pack IDs
- QA goals
- allowed engine families

## Step 4 — Add Reference Pack Manifest

Create:

```text
character_packs\char_<slug>001\manifestseference_pack_manifest.json
```

Each asset must include:

- asset id
- asset type
- local path
- optional S3 URI
- optional EC2 path
- file size
- SHA256
- approval status
- intended runtime consumer

## Step 5 — Bind Character in Scene Director

Scene Director plans must reference characters by ID:

```json
{
  "characters": [
    {
      "character_id": "char_elena_demo",
      "character_version": "v001",
      "role_in_scene": "primary_subject"
    }
  ]
}
```

## Step 6 — Compile Model Selection

The model selector uses the Character Bible and Wave 06 engine router to select compatible models/LoRAs. Character-specific LoRAs must not be globally enabled unless the pass is single-character or globally safe.

## Step 7 — Run Local Validation

Run:

```powershell
python ._IMPLEMENTATION\scriptsun_wave08_local_validation.py --root .
```

## Step 8 — Runtime Proof Later

After real reference packs exist, run ComfyUI local/EC2 proof:

- load approved references
- generate base image
- generate identity detail pass
- export QA evidence
- score continuity
- promote only if QA passes
