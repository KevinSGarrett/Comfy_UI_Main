# Wave 22 Audio Force Event Binding Interface

Wave 22 produces audio metadata for future audio synthesis/scoring.

## Audio event binding
Each physical contact edge can produce zero or more audio force events.

Fields:
- event id
- contact edge id
- source/target material pair
- expected foley family
- force class
- duration
- timing alignment
- loudness hint
- confidence

## Audio QA
Audio force events must agree with the visual contact intensity and duration.
