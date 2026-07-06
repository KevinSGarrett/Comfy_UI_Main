# Wave 27 Video Routing and Temporal QA Architecture

Wave 27 sits above Wave 26's keyframe and reference-video planning layer.

## Core mission
Given a temporal request, the system must:
1. choose the correct video route,
2. build or ingest a per-frame manifest,
3. run temporal QA,
4. repair failed frames or frame spans,
5. decide promotion or rerun.
