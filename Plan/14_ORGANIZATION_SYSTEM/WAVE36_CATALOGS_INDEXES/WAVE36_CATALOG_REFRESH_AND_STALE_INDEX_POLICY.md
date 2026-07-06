# Wave 36 Catalog Refresh and Stale Index Policy

## Stale index indicators
- file exists but catalog does not list it
- catalog lists a file that no longer exists
- schema changed but examples were not refreshed
- workflow changed but workflow catalog was not regenerated
- release ZIP changed but release manifest hash was not updated

## Rule
A release cannot promote with stale indexes.
