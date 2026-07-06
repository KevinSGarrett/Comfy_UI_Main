# Wave 32 Targeted Rerun Implementation

## Rerun routing priority
- repair metadata if the visual/audio output is good but state labels are incomplete
- repair local region if only a mask/region failed
- repair single frame/span if temporal drift is limited
- repair audio layer if visual output passed but audio failed
- rerun shot if multiple visible domains failed
- rerun segment if continuity fails across shots

## Never rerun full scene by default
Full-scene rerun is the last option, not the default.
