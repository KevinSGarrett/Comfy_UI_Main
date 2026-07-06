# Wave 19 Clothing, Fabric, Props, and Furniture Contact Architecture

Wave 19 makes contact realism a first-class system layer. The goal is to stop clothing, props, and furniture from looking pasted on, floating, unsupported, or unaffected by body weight.

## Core components
- contact ownership graph
- cloth/fabric behavior profile
- prop grip/support profile
- furniture compression/support profile
- contact shadow and occlusion requirements
- low-denoise regional refinement plan
- evidence and QA scoring

## Default sequence
1. approved base image
2. approved body/frame/mask plan
3. clothing/fabric/prop/furniture contact contract
4. pass planner selects contact/fabric/support passes
5. masked low-denoise refinements
6. QA score and rerun policy

## Important boundary
The system must not invent uncontrolled deformations. Every fold, stretch, prop contact, or furniture compression should have a target region, contact owner, force/support profile, and evidence output.
