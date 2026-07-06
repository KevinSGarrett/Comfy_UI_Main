# Wave 24 Advanced Additions Instance Layout Integration

Wave 24 integrates advanced additions through a new ownership gate.

Any future module that edits a character must declare:

- target character_instance_id
- target region ownership
- protected non-target instances
- allowed overlap/contact boundary
- depth/occlusion assumptions

This prevents advanced additions from bypassing per-character identity and mask ownership.
