# Advanced Additions to 35-Wave Crosswalk

| Advanced addition | Primary waves | Implementation destination | QA requirement |
|---|---|---|---|
| Physical Interaction Engine | 21, 22, 23, 25 | Contact graph, pressure map, deformation pass, interaction QA | Contact crop proves source/target placement, pressure, occlusion, and no merged anatomy. |
| Micro-Motion Layer | 26, 27, 28 | Keyframe planner, motion tracks, temporal QA | Per-frame/body-region motion remains phase-consistent and does not break identity or anatomy. |
| Skin and Material Realism | 18, 19, 29 | Surface-state ledger, masks, skin/fabric/detail passes | Surface state appears only in target masks and persists across shots. |
| Fluid and Body-State Continuity | 18, 29, 32 | Scene-state ledger, continuity diff, revision manager | Planned state matches generated state in before/after/shot-to-shot QA. |
| Pose-to-Audio Force Model | 30, 31 | Audio force map, foley timing, spatial mix | Audio transients align to visual contact/motion timing. |
| Long-Form Fatigue and Variation | 26, 28, 29, 32 | Variation scheduler, fatigue curves, take manager | Scene does not reset, over-repeat, or contradict prior state. |
| Room Acoustics and Spatial Audio | 9, 30, 31 | Environment room profile, spatial audio renderer | Audio room/pan/reverb matches camera and environment. |
| LLM Scene Director | 7, 14, 32 | Scene parser, pass planner, state diff/rerun | Output plan validates against schemas and executes only supported passes. |
| Auto-Preset Library | 7, 16, 21, 33 | Presets, successful-run learning, budget modes | Presets are versioned, testable, and cannot bypass QA. |
| Proxy Preview/Animatic | 26, 33 | Low-cost storyboard, pose/contact preview, scratch audio | Expensive EC2 final render cannot run until proxy preview passes required checks. |
| State Diff / Take Variants | 32 | Revision debugger, take manager, variant generator | Every revision states which failed QA metric it is correcting. |
