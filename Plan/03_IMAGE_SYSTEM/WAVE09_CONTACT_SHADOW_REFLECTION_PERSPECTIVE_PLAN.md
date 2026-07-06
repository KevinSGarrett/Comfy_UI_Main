# Wave 09 Contact Shadow, Reflection, and Perspective Plan

## Contact shadows
Contact shadows prove that a person, prop, or object is physically located in the environment. The QA gate should check contact at:
- feet/floor,
- body/furniture,
- hands/props,
- clothing/surface,
- hair/skin/props when relevant,
- objects resting on tables/beds/counters.

## Reflections
Reflection QA should check:
- mirrors,
- windows,
- glossy floors,
- wet surfaces,
- polished furniture,
- metal/glass objects.

Reflection direction and content must match the scene geometry.

## Perspective
Perspective QA should check:
- horizon line,
- camera height,
- lens feel,
- furniture scale,
- wall/floor alignment,
- person/object scale relationship,
- repeated objects not shrinking/growing incorrectly.

## Runtime use
The Scene Director should generate QA goals from the environment plan:
```text
if mirror present → reflection QA required
if glossy/wet surface present → specular/reflection QA required
if body/prop contact present → contact shadow QA required
if video plan present → perspective consistency across frames required
```
