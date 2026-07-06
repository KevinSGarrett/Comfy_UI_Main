# Wave 22 Audio Force Alignment Tests

## Alignment checks
- silent contacts are marked silent
- soft contacts map to soft foley
- object impacts map to impact/tap/drag classes
- furniture support can map to creak or compression metadata
- duration agrees with visual contact duration
- repeated contact carries repeat/rhythm metadata

## Failures
- loud force metadata for barely visible contact
- missing force metadata for visible impact
- force event timing outside visual contact window
