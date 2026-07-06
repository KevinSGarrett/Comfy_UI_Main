# Wave 17 — Body Correction Test Matrix

| Test ID | Scenario | Required Evidence | Pass Condition |
|---|---|---|---|
| W17-T01 | Preserve existing body | baseline + candidate | no body drift |
| W17-T02 | Subtle stomach correction | abdomen mask + output | stomach improves, identity stable |
| W17-T03 | Waist correction | paired waist masks | balanced waist, no fabric tear |
| W17-T04 | Hip/thigh balance | hip/thigh masks | stance and crop preserved |
| W17-T05 | Full silhouette repair | silhouette mask | no body merge, no extra fragments |
| W17-T06 | Clothing boundary repair | clothing edge mask | fabric follows body surface |
| W17-T07 | Skin texture restore | skin mask | no smeared texture |
| W17-T08 | Multi-character scene | instance masks | only target character changes |
| W17-T09 | Low-denoise bridge | source/candidate hashes | base preserved |
| W17-T10 | Rerun failure | failed candidate + rerun | failed candidate not promoted |
