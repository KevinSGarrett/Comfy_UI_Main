# Wave 31 Visual Action to Audio Force Model

## Force sources
- body movement
- hand/foot/object contact
- prop impact
- furniture support/compression
- clothing/fabric shift
- camera-visible collision
- breath/exertion
- scene transition

## Force dimensions
- intensity
- speed
- pressure
- duration
- material hardness
- contact area
- visibility confidence
- off-screen confidence

## Rule
If visual force is high but audio is weak or missing, QA fails. If audio force is high but visual force is low or absent, QA also fails.
