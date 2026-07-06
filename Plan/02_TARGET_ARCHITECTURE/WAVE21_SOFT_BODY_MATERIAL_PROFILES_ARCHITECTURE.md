# Wave 21 Soft-Body Material Profiles Architecture

Wave 21 creates a profile system for controlling soft-body-looking behavior.

## Why this exists
Prompt words like "soft," "jiggle," "sag," or "compressed" are not reliable enough by themselves. The system needs structured material profiles that can drive masks, low-denoise passes, video planning, and QA scoring.

## Core profile axes
- firmness
- softness
- sag
- bounce
- ripple
- jiggle
- compression
- rebound

## Material families
- skin / soft tissue
- muscle / firm tissue
- elastic fabric
- loose fabric
- cushion / furniture support
- hard surface / no deformation

## Runtime placement
Wave 21 profiles sit between:
- Wave 13 mask factory
- Wave 17 body correction
- Wave 18 skin/material realism
- Wave 19 clothing/furniture contact
- Wave 20 hard anatomy repair
- Wave 14 orchestrator

The profile system does not replace those layers; it gives them material behavior rules.
