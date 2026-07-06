# Wave 18 Image Skin/Material Pass Implementation Plan

## Objective
Add localized skin/material realism after base generation and body-shape approval.

## Recommended regional pass order
1. select approved source image
2. attach owned region mask
3. choose pass profile
4. patch workflow for low-denoise regional refine
5. generate before/after evidence
6. score continuity and drift
7. promote or rerun

## Required inputs
- approved image from Wave 15 or Wave 17
- owned mask from Wave 13
- engine routing decision from Wave 06 / Wave 16
- scene director contract from Wave 07
- QA goals from Wave 18
