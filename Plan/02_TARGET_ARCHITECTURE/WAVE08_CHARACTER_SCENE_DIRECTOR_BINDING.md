# Wave 08 — Character to Scene Director Binding

## Purpose

Wave 07 created the LLM Scene Director. Wave 08 gives the Scene Director stable character targets.

## Required Scene Director Behavior

When a request names or implies a reusable character, the Scene Director must:

1. Resolve `character_id` from the identity registry.
2. Load active `character_version` unless the user explicitly asks for another version.
3. Load Character Bible locks.
4. Load reference-pack manifest.
5. Compile per-character masks.
6. Compile engine/model choices compatible with that character.
7. Compile QA goals for identity/body/skin/hair/outfit/voice continuity.
8. Mark any requested identity changes as a revision request.

## Do Not Prompt-Override Identity

The Scene Director must not use a scene request to overwrite locked identity fields. Example:

```text
User: Make Elena with shorter blonde hair for this scene.
System: If Elena's locked hair is dark brown, this becomes an outfit/hair variant request or a new character revision request. It is not silently applied to the locked Character Bible.
```

## Character Binding Object

```json
{
  "character_binding_id": "bind_001",
  "character_id": "char_elena_demo",
  "character_version": "v001",
  "role_in_scene": "primary_subject",
  "screen_order": 1,
  "depth_order": "foreground",
  "identity_lock_strength": "high",
  "allowed_revision_scope": ["expression", "pose", "temporary_outfit", "temporary_skin_state"],
  "required_reference_assets": ["face", "body", "skin", "hair", "outfit"],
  "qa_goals": ["face_identity_match", "body_silhouette_match", "hair_match", "skin_marker_preservation"]
}
```

## Multi-Character Binding Rule

Every visible character gets an instance ID:

```text
character_id + character_version + scene_instance_id
```

The instance ID owns masks, depth order, pose controls, LoRA/model selections, and QA results. No pass may apply character-specific identity LoRAs globally unless the pass is single-character or region-masked.
