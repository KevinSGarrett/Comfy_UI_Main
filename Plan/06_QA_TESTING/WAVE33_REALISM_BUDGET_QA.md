# Wave 33 Realism Budget QA

Realism budget QA checks whether the system is spending detail in the right place.

## Pass examples
- high detail only on visible hero regions
- low detail on background regions
- extra final polish reserved for selected takes
- video/audio final cost blocked until previews pass

## Fail examples
- hero render requested without preview proof
- expensive detail requested for hidden regions
- full-scene final render requested when only local preview failed
- final EC2 render requested without preflight
