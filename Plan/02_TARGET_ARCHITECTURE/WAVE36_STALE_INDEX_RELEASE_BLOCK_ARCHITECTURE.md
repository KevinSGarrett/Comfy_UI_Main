# Wave 36 Stale Index Release Block Architecture

A release is blocked if the current file state and the catalogs disagree.

## Block examples
- important file not cataloged
- catalog entry references missing file
- workflow not registered
- asset not registered
- QA evidence not linked
- App Mode control not mapped
- EC2 sync payload lacks manifest
