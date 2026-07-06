# Model Registry Field Dictionary

Wave: 60

This dictionary standardizes model registry fields used by the Civitai, model download, compatibility, and runtime validation protocols.

| Field | Meaning | Required |
|---|---|---:|
| `registry_schema_version` | Schema version for the record | yes |
| `record_id` | Unique local registry ID | yes |
| `source` | Origin such as `civitai`, `local`, `manual` | yes |
| `source_url` | Model or API URL without secret token | when known |
| `source_model_id` | Civitai or source model ID | when known |
| `source_model_version_id` | Civitai or source version ID | when known |
| `model_name` | Human-readable model name | yes |
| `model_type` | Checkpoint, LORA, ControlNet, VAE, etc. | yes |
| `base_model` | Normalized base such as `sdxl`, `flux_dev`, `pony_sdxl` | yes |
| `version_name` | Model version name | when known |
| `file_name` | Local file name | yes after download |
| `file_extension` | `.safetensors`, `.ckpt`, etc. | yes after download |
| `file_size_bytes` | Local file size | yes after download |
| `sha256` | Local SHA256 | yes after download |
| `source_hashes` | Source-provided hashes | when known |
| `local_path` | Local absolute or project-relative path | yes after download |
| `storage_location` | local, ec2, s3, external | yes |
| `workflow_lane` | Project lane where the model belongs | yes |
| `compatibility_status` | candidate, compatible, incompatible, needs_runtime_validation, rejected | yes |
| `compatible_engines` | Engines allowed to load/use this asset | yes |
| `trigger_words` | Trained words or required trigger phrases | when known |
| `intended_use` | Why the model exists in the system | yes |
| `qa_status` | not_tested, passed, failed, needs_review | yes |
| `runtime_validation_status` | not_run, queued, passed, failed | yes |
| `evidence_paths` | Paths to validation/QA evidence | when tested |

No model is done until `runtime_validation_status` and `qa_status` are updated.
