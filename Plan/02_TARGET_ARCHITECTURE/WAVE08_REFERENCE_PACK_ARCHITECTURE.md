# Wave 08 — Reference Pack Architecture

## Purpose

A reference pack is the media and metadata evidence behind a Character Bible. It gives the Scene Director, IPAdapter/reference modules, masks, detailers, video continuity tools, and audio tools the assets needed to preserve a character.

## Git-Safe Rule

Reference media can be private, large, or runtime-only. Therefore:

- Git stores manifests, schemas, hash records, and path conventions.
- Local/EC2/S3 store the actual reference images, masks, embeddings, and audio.
- Every media file must have a SHA256 hash before it is used for promotion.
- Raw references and approved references must be separated.

## Recommended Folder Layout

```text
C:\Comfy_UI_Main\character_packs  char_<name_or_slug>    v001      bible        character_bible.json
        revision_history.json
      references        raw        approved        rejected      masks        face        hair        body        skin        outfit        accessories      embeddings        face        body        voice      prompts        positive_identity.txt
        negative_identity.txt
        outfit_variants.json
      voice        voice_profile.json
        reference_audio_manifest.json
      qa        continuity_reports        reference_pack_validation.json
      manifests        reference_pack_manifest.json
        file_hash_manifest.json
```

## Reference Asset Types

| Asset Type | Purpose | Runtime Consumer |
|---|---|---|
| approved_face_reference | Face identity anchor | IPAdapter/face reference/detailer |
| approved_body_reference | Body shape/silhouette anchor | base pass, ControlNet, mask planner |
| approved_skin_reference | skin tone/texture/markers | skin/detail pass |
| approved_hair_reference | hair style/color/length | identity/detail pass |
| approved_outfit_reference | wardrobe continuity | outfit/fabric pass |
| approved_pose_reference | recurring pose/action | pose/control pass |
| approved_voice_reference | voice identity | audio/voice stage |
| mask_reference | region ownership | mask factory |
| embedding_reference | compressed identity cue | future identity QA/runtime tools |

## Reference Pack Acceptance Rules

A reference pack cannot be promoted until:

1. All referenced files exist in the expected local/S3/EC2 path.
2. Every file has size and SHA256 recorded.
3. Approved and rejected references are separated.
4. At least one face/body/skin/hair reference exists for visual characters.
5. Voice profile exists for audio-enabled characters.
6. QA report confirms no conflicting identity anchors.
7. Character Bible points to the exact reference pack version.

## Conflict Examples

- Two different hair colors marked as locked without variant rules.
- Multiple body silhouettes with no version split.
- Outfit reference treated as permanent when it should be scene-specific.
- Face reference from one character used for another.
- Voice profile missing while audio continuity is required.
