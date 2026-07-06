# Wave 20 Face, Hands, Feet, and Hard Anatomy Architecture

Wave 20 is a strict repair layer for the regions that most often fail under close inspection.

## Target regions
- face structure
- eyes / eyelids / pupils / iris symmetry
- mouth / teeth / lips
- hands / fingers / thumbs / wrists / palms / knuckles
- feet / toes / ankles / soles / heels
- nails / nail beds / polish / small hard-detail cleanup

## Core principle
Hard-anatomy repair is not a global prompt problem. It must use local detection, crop planning, masks, low-denoise repair, and local QA.

## Position in the pipeline
1. base image approval
2. body / frame / pose approval
3. hard-anatomy detector pass
4. crop/detail repair plan
5. local repair execution
6. local QA plus global preservation QA
7. promote or rerun only failed regions
