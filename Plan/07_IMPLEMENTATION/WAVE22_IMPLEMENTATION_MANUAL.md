# Wave 22 Implementation Manual

## Build sequence
1. Compile physical contact graph from Scene Director output.
2. Validate every edge.
3. Attach masks from the Mask Factory.
4. Attach soft-body profiles from Wave 21.
5. Attach fabric/prop/furniture rules from Wave 19.
6. Attach hard anatomy protection from Wave 20.
7. Patch workflow JSON for selected pass.
8. Run pass and collect evidence.
9. Score contact graph evidence.
10. Promote, rerun, fallback, or block.

## Developer note
This wave should be integrated as a contract-driven layer. Do not add one-off prompt text patches as the main control mechanism.
