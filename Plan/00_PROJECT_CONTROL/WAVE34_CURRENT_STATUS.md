# Wave 34 Current Status

## Status
PASS — cumulative final integration pack created.

## Release status
Final integration release pack: **created**

## Runtime certification status
Runtime certification remains **proof-bound**. This pack contains the final integration architecture, release contracts, proof gates, QA certification format, manifest requirements, handoff docs, and validation scripts.

## Runtime proof boundaries
- App Mode release: requires exported App Mode workflow/control-surface proof.
- Image Main Flow proof: requires exact Main_Flow output artifacts and evidence manifests.
- Video/GIF proof: requires generated video/GIF artifacts and temporal QA.
- Audio proof: requires generated audio/mix artifacts and sync QA.
- EC2 final render: blocked until preview QA, preflight, hydration, run logs, and QA evidence pass.

## Source inventory
- Main Flow nodes observed: 356
- Main Flow links observed: 91
- SaveImage lanes observed: 8
- PreviewImage nodes observed: 8
- KSampler nodes observed: 7
- Fast-preview anchors observed: 4
- Low-denoise anchors observed: 2
- Mask/inpaint/control candidate nodes observed: 13
- ControlNet-related nodes observed: 2
- Notes/runtime boundary nodes observed: 13
- App Mode candidate signals observed: 285
- Orchestrator candidate signals observed: 12
- Local/EC2 proof candidate signals observed: 282
- QA certification candidate signals observed: 16
- Manifest candidate signals observed: 286
- Handoff candidate signals observed: 19
- Runtime boundary signals observed: 295
- Tracker rows observed: 12887
- Tracker columns observed: 73
- Tracker release/proof/manifest related rows observed: 12887

## Uploaded side-source summaries
[
  {
    "name": "Advaned_Additions(37).zip",
    "exists": true,
    "file_count": 20,
    "top_extensions": {
      ".md": 20
    }
  },
  {
    "name": "comfyui_assistant_replies_txt(37).zip",
    "exists": true,
    "file_count": 4,
    "top_extensions": {
      ".txt": 4
    }
  },
  {
    "name": "Plans(40).zip",
    "exists": true,
    "file_count": 4870,
    "top_extensions": {
      ".json": 1285,
      ".md": 1256,
      ".pyc": 628,
      ".csv": 517,
      "[no_ext]": 500,
      ".py": 314,
      ".txt": 235,
      ".ps1": 61,
      ".sh": 59,
      ".png": 10,
      ".yaml": 2,
      ".template": 1
    }
  }
]
