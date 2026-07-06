# Wave 09 World, Lighting, and Prop Test Matrix

| Test ID | Area | Pass condition | Failure condition |
|---|---|---|---|
| W09-ENV-001 | Room layout | doors/windows/walls stay consistent | room geometry changes unexpectedly |
| W09-ENV-002 | Furniture scale | furniture matches character scale | bed/chair/table scale changes |
| W09-ENV-003 | Prop continuity | props stay in assigned anchors | props disappear, duplicate, or drift |
| W09-ENV-004 | Lighting | light direction/softness matches rig | shadows change direction |
| W09-ENV-005 | Contact shadows | contact points grounded | floating body/props |
| W09-ENV-006 | Reflections | reflective surfaces obey geometry | impossible mirror/window/gloss reflection |
| W09-ENV-007 | Materials | surface classes stay stable | wood becomes plastic, fabric becomes metal |
| W09-ENV-008 | Image pass drift | inpaint/upscale preserve room | pass changes layout or scale |
| W09-ENV-009 | Video temporal | room stable through frames | background morphs or flickers |
| W09-ENV-010 | Audio ambience | audio matches room/materials | room tone contradicts visual environment |
| W09-ENV-011 | AV sync | audio events match visible actions | Foley/voice timing contradicts video |
| W09-ENV-012 | Promotion | all required reports exist | missing evidence or unsupported claims |
