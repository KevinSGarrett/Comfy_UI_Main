# Wave 09 Environment Reference Pack Build Instructions

## Folder layout
```text
Implementation/environment_packs/{environment_id}/{environment_version}/
├─ manifest.json
├─ room_profile.json
├─ lighting_rig.json
├─ prop_registry.json
├─ material_surface_profiles.json
├─ scale_reference.json
├─ references/
│  ├─ room/
│  ├─ lighting/
│  ├─ materials/
│  ├─ props/
│  ├─ camera/
│  └─ masks/
├─ video/
│  ├─ camera_paths/
│  └─ keyframe_requirements/
└─ audio/
   ├─ ambience_profile.json
   ├─ acoustic_profile.json
   └─ foley_profile.json
```

## Manifest rules
Every file in the pack should be recorded with:
- relative path,
- size,
- SHA256,
- file type,
- role,
- created/updated time when available.

## Reference naming
Use stable names:
```text
room_front_wide_001.png
room_left_45_001.png
window_light_reference_001.png
floor_material_wood_001.png
prop_bed_queen_reference_001.png
camera_anchor_low_front_001.png
```

## Do not store huge generated binaries in Git
Store pack manifests and lightweight references in Git only if acceptable. Large assets should follow the Wave 02 S3/local/EC2 cache rules.
