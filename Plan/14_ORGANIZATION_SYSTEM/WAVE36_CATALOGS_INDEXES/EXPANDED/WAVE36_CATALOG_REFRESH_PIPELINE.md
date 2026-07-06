# Wave 36 Catalog Refresh Pipeline

## Refresh order

1. scan filesystem
2. generate file catalog
3. generate workflow catalog
4. generate asset catalog
5. generate QA evidence catalog
6. generate registry search index
7. detect stale references
8. write catalog refresh report
9. block release if stale-index blockers exist

## Refresh triggers

- new wave added
- new workflow added
- model/LoRA library changed
- App Mode control changed
- QA evidence generated
- release candidate generated
- migration moved files
