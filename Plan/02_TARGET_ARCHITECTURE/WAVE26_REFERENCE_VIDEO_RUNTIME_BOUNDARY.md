# Wave 26 Reference Video Runtime Boundary

Wave 26 now defines real reference-video support, but runtime proof is still required.

## Runtime proof required
To mark reference-video support as proven, the system must show:
- an actual MP4/MOV/WebM source was ingested,
- metadata was extracted,
- frames were sampled or extracted,
- a frame manifest was produced,
- pose/depth/mask/contact timelines were produced where requested,
- the generated output used those timelines,
- temporal QA and repair decisions were recorded.

## Not enough
The following are not sufficient by themselves:
- a GIF-only example,
- a still image keyframe plan,
- a note saying video is supported,
- a reference filename with no decoded frame evidence.
