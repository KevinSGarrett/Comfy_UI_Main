# Wave 17 — Orchestrator and Rerun Loop

## Body correction pass loop

```text
body_shape_precheck
→ mask validation
→ low-denoise correction
→ edge/fabric cleanup
→ skin texture restore
→ QA scoring
→ pass / rerun / fallback / stop
```

## Rerun decision rules
- If target region did not improve, rerun with slightly higher denoise only if identity and pose are stable.
- If identity or pose drifted, rerun lower denoise with stronger exclusion masks.
- If mask edge is visible, rerun with stronger feather/blur and edge cleanup.
- If body merges with another character, stop and require person-instance mask correction.
- If clothing floats or tears, run clothing boundary repair.
- If texture smears, run skin texture restore.

## Stop conditions
The orchestrator must stop body correction when:
- identity changes,
- character count changes,
- body merges with another person,
- full-image redraw was attempted,
- crop cuts the corrected region,
- output loses pose/action,
- fabric and skin continuity cannot be repaired after allowed reruns.
