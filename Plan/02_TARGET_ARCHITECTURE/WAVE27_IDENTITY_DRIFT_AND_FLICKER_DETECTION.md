# Wave 27 Identity Drift and Flicker Detection

## Identity drift
Occurs when a character's facial identity, body identity, clothing identity, or region ownership changes unintentionally across frames.

## Flicker
Occurs when local or global visual appearance jumps between adjacent frames without motion justification.

## Detection policy
- score identity continuity frame-to-frame and over sliding windows
- score flicker across pixels, regions, lighting, and textures
- route failed frames or failed spans into repair
