# Wave 02 AI Project Manager Tasks — Model Storage, S3/EC2/Local Cache, and Civitai Metadata

## Wave focus

Wave 02 builds the model-asset foundation for the full 35-wave system.

## Required outcomes

1. Keep all model binaries out of Git.
2. Treat S3 as the canonical model binary store.
3. Treat local and EC2 model folders as caches, not sources of truth.
4. Add `.env.example` and optional `.ec2.example` templates.
5. Add Civitai API metadata ingestion requirements.
6. Add a 70+ column model registry standard.
7. Add strict QA gates for model availability, hash integrity, engine compatibility, and metadata completeness.

## AI PM execution contract

The AI system must not mark Wave 02 complete until all of these are true:

- `.env.example` exists and includes GitHub, Civitai, AWS/S3, EC2, local path, ComfyUI API, model cache, and QA variables.
- `.env.example` contains placeholders only; no real tokens or secrets.
- `.gitignore` continues to block real `.env`, `.env.*`, `.ec2`, model binaries, archives, renders, and large media.
- Civitai metadata ingestion has a clear local cache, raw JSON cache, normalized registry, and QA procedure.
- Model registry column catalog includes at least 70 fields. This Wave 02 pack defines 146.
- Model storage strategy includes canonical S3 paths, local cache paths, EC2 paths, hydration manifests, and dry-run-first commands.
- Every model asset must be addressable by hash, source metadata, local path, S3 URI, engine compatibility, and QA status.
- EC2 remains off by default and is used only after local registry/model-hydration validation passes.

## Wave 02 deliverables

- `07_IMPLEMENTATION/templates/repo/.env.example`
- `07_IMPLEMENTATION/templates/repo/.ec2.example`
- `02_TARGET_ARCHITECTURE/CIVITAI_API_MODEL_METADATA_SYSTEM.md`
- `02_TARGET_ARCHITECTURE/WAVE02_MODEL_STORAGE_S3_EC2_LOCAL_CACHE_STRATEGY.md`
- `02_TARGET_ARCHITECTURE/CIVITAI_TO_ENGINE_COMPATIBILITY_AND_TAGGING_STRATEGY.md`
- `07_IMPLEMENTATION/WAVE02_CIVITAI_API_IMPLEMENTATION_MANUAL.md`
- `07_IMPLEMENTATION/WAVE02_MODEL_STORAGE_IMPLEMENTATION_MANUAL.md`
- `07_IMPLEMENTATION/scripts/civitai_metadata_ingest.py`
- `07_IMPLEMENTATION/scripts/validate_wave02_model_registry.py`
- `08_SCHEMAS/civitai_model_registry_70plus.schema.json`
- `09_EXAMPLES/civitai_model_registry_70plus.columns.csv`
- `10_REGISTRIES/civitai_metadata_column_catalog.json`
- `10_REGISTRIES/model_storage_path_conventions.json`
- `06_QA_TESTING/WAVE02_MODEL_ASSET_QA_GATES.md`
