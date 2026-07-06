# Wave 23 Deformation Pass Routing and Order

## Routing goal
Choose the smallest pass that solves the problem.

## Preferred ordering
1. If masks are invalid -> reroute to mask QA and block the visual pass.
2. If anatomy ownership is ambiguous -> block and request layout correction.
3. If contact shadow is missing -> run contact shadow primer.
4. Run primary deformation pass.
5. If edges look cut/chopped -> run boundary repair.
6. If texture drift occurs -> run material continuity repair.
7. If identity/pose/framing drift occurs -> reject and lower denoise or reroute engine.

## Default denoise windows
- contact shadow primer: 0.10–0.18
- micro indentation: 0.12–0.22
- finger indentation: 0.18–0.30
- compression/squeeze: 0.20–0.35
- broad support compression: 0.22–0.38
- pull/push/shear repair: 0.18–0.34
