# Wave 19 Prop Contact and Object Ownership Graph

Props require ownership and contact logic.

## Ownership types
- held prop
- worn accessory
- supported prop on furniture/surface
- prop touching body
- prop interacting with clothing

## Required proof
- prop mask
- hand/body/furniture contact mask
- contact shadow or occlusion edge
- no-floating score
- no-clipping score
- geometry consistency score

## Failure examples
- object hovering with no support
- fingers not wrapping around held object
- prop cuts through clothing/body
- missing shadow where object touches a surface
