# Wave 08 — Character Bible and Identity Registry Architecture

## Purpose

The Character Bible is the stable source of truth for reusable characters. It prevents a character from changing every time a prompt changes. Instead of saying “make a woman with X hair and Y body” every time, the system resolves a `character_id`, loads the correct `character_version`, and uses locked fields, reference packs, model selection, mask plans, and QA goals to preserve identity.

## Core Entities

### 1. Character Bible

One JSON document per character version. It describes:

- identity locks
- face description
- body profile
- skin profile
- hair profile
- outfit profile
- voice profile
- reference packs
- allowed engines
- allowed model stacks
- continuity QA goals
- revision history

### 2. Identity Registry

A global index of all known characters. It maps:

- `character_id`
- display name
- active version
- status
- reference-pack root
- allowed scene roles
- allowed engines
- QA requirements

### 3. Reference Pack

A file-system bundle containing raw references, approved references, masks, embeddings, metadata, and QA evidence. The pack is not stored in Git when it contains large or private media. Git stores only manifests and hashes.

### 4. Character Binding

The Scene Director attaches a character to a scene by ID:

```json
{
  "character_id": "char_elena_demo",
  "character_version": "v001",
  "role_in_scene": "primary_subject",
  "identity_lock_strength": "high",
  "allowed_revision_scope": "outfit_only"
}
```

## Locked Fields

Identity-critical fields require a character revision instead of direct prompt overwrite:

- face structure
- approximate age band/adult status
- body silhouette
- skin marker set
- hair root color and hairline
- permanent tattoos/marks/scars
- core voice/timbre profile
- recurring wardrobe/accessory anchors

Scene-specific fields may change without a new character version:

- facial expression
- pose
- temporary outfit variant
- temporary lighting
- temporary environment
- camera angle
- short-term skin state such as sweat, makeup, dirt, pressure marks, or fatigue

## Character State Model

```text
draft → candidate → active → frozen → superseded/deprecated
```

- `draft`: incomplete, not allowed in production routing.
- `candidate`: may be tested, not promoted.
- `active`: allowed for normal generation.
- `frozen`: stable reference for long-running continuity.
- `superseded`: replaced by a newer version.
- `deprecated`: kept for history but blocked from new scenes.

## Design Rule

The prompt is not the identity source of truth. The prompt describes the requested scene. The Character Bible defines who the character is.
