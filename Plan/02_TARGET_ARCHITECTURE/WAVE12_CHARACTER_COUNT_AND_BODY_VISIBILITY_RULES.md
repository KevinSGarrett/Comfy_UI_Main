# Wave 12 Character Count and Body Visibility Rules

## Character count

Every scene plan must declare an expected character count. The detector evidence must then prove the output matches it.

Required output evidence:

- Expected character count.
- Detected person instance count.
- Detected skeleton count.
- Detected face count when faces should be visible.
- Assigned character IDs.
- Unassigned body fragments.
- Extra person-like regions.

A frame fails when it contains missing primary characters, unexplained extra people, duplicate bodies, split bodies, or unassigned fragments.

## Body visibility

Body visibility is a profile, not a vague prompt phrase.

- Full body: head through feet visible.
- 3/4 body: head through knees or lower legs visible.
- Half body: head through waist/hips visible.
- 1/3 body: head/face and upper torso emphasis.
- 1/4 body: tight close-up or region-specific crop.
- Face close-up: face landmarks must be intact.

Each profile defines required landmarks, minimum visible body ratio, safe margins, forbidden crop points, and promotion thresholds.
