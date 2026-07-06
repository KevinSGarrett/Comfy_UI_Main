# Wave 10 Video Zoom / Pan / Tilt / Orbit Boundary

## Boundary Rule

Do not claim video camera motion is production-ready until the relevant video workflow renders and passes QA.

## Still vs Video

Still image camera planning can specify:

- shot size
- lens look
- camera angle
- framing
- depth

Video camera planning must additionally specify:

- start/end framing
- motion path
- temporal smoothing
- stabilization
- subject lock
- frame sampling QA

## Promotion Gate

A video output is blocked if:

- the start/end framing does not match the plan
- camera path jumps
- subject identity drifts
- environment geometry bends
- audio perspective contradicts camera distance
