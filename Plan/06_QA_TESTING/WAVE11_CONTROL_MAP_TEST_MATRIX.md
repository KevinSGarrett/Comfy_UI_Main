# Wave 11 Control Map Test Matrix

| Test | Map Type | Required Evidence | Promotion Decision |
|---|---|---|---|
| Current Canny branch smoke | Canny | generated Main_Flow/ControlNet_Canny_Edge output | allow branch verification |
| DWPose single character | DWPose | pose map + final image | block until runtime proof |
| OpenPose simple body | OpenPose | skeleton map + final image | block until runtime proof |
| Depth room structure | Depth | depth map + final image | block until runtime proof |
| Normal surface support | Normal | normal map + final image | block until runtime proof |
| Lineart contour lock | Lineart | lineart map + final image | block until runtime proof |
| Two-character skeleton ownership | DWPose + masks | two skeletons + two masks + final image | block until runtime proof |
| Video keyframe pose bridge | DWPose sequence | keyframe maps + video sample | block until video proof |
