# Wave 24 Instance Layout Workflow Build Instructions

1. Compile the instance layout contract.
2. Validate character count and required fields.
3. Build or load person-instance masks.
4. Build or load per-character skeleton maps.
5. Build or load region ownership maps.
6. Validate depth order and frame placement.
7. Patch workflow JSON only for the target instance/pass.
8. Run QA against before/after evidence.
9. Promote only if all instance ownership checks pass.
