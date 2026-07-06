# Wave 19 Contact Shadow, Occlusion, and Support Boundary

Contact realism requires shadow and occlusion evidence, not only object placement.

## Required checks
- contact shadow exists where body/fabric/prop/furniture touches
- occlusion order is correct
- no visible floating gap
- no mesh-like clipping or merged geometry
- fabric seams and body edges remain stable
- depth/control cues agree with support geometry

## Rerun priority
1. fix floating/clipping
2. fix missing support shadow
3. fix fabric fold/stretch direction
4. fix material continuity
5. clean up local artifacts
