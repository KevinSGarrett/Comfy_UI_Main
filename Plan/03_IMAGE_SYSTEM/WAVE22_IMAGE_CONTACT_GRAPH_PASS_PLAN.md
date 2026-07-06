# Wave 22 Image Contact Graph Pass Plan

## Goal
Use the contact graph to decide which image repair/refine pass should run.

## Pass families
- contact-shadow repair
- occlusion boundary repair
- source/target separation repair
- soft-body indentation pass
- fabric compression pass
- prop/furniture support pass
- hard anatomy local repair after contact
- cleanup / seam blend

## Image evidence
Each pass must save:
- before image
- after image
- before crop
- after crop
- mask overlay
- source/target ownership metadata
- edge score report
