# Wave 24 Multi-Character Instance QA Gates

A multi-character output fails if:

1. character count is wrong,
2. any visible character lacks an instance id,
3. identity binding is missing or swapped,
4. person-instance masks overlap as merged bodies,
5. skeleton maps conflict,
6. region ownership is missing,
7. depth order contradicts occlusion,
8. a repair pass edits the wrong character,
9. contact/deformation pass lacks source/target instance ownership.
