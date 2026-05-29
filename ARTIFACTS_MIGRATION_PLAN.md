# Artifacts Migration Plan: Replacing Dataset Output with DFS

**Date:** 2026-05-27
**Objective:** Replace dataset-based file storage with Domino Artifacts (DFS) for autodoc output

## Overview

Currently, autodoc writes generated DOCX/IPYNB files to a dataset mount path. This migration switches to Domino Artifacts, which:
- Mounts at `/mnt/artifacts/` in job containers (filesystem I/O, no API overhead)
- Persists independently from git branches
- Provides better integration with Domino's DFS UI
- Simplifies file management (no dataset mount path threading)

## New Directory Structure

```
/mnt/artifacts/
├── docs/
│   └── 2026-05-27_14-30-45/         # Timestamp-based run directory
│       ├── model_docs.docx
│       ├── model_docs.ipynb
│       └── model_docs.json           # Cache metadata (optional)
├── specs/
│   └── *.yaml                        # User-uploaded/synced specs
└── .autodoc/
    └── cache.json                    # Generation results cache
```

## Implementation Steps

### Phase 1: Core Artifact Support Modules

**Files to add:**
- `auto_model_docs/domino_artifacts.py` — Artifact store API wrapper (from reference branch)
- `auto_model_docs/artifact_layout.py` — Path resolver (from reference branch)

**Purpose:**
- `domino_artifacts.ArtifactStore` — REST API for web app reads/writes
- `domino_artifacts.write_artifact()` / `read_artifact()` — Filesystem I/O for job containers
- `artifact_layout` — Central path resolution for docs, specs, cache

**Testing:**
- Unit tests in `tests/test_artifact_layout.py` (basic path resolution)
- No REST API tests needed (Domino integration layer)

### Phase 2: Job Command Building (artifact-based)

**File: `auto_model_docs/studio/job_engine.py`**

Changes:
1. Remove `dataset_path` parameter from `_build_job_command()`
2. Hardcode `--output_dir` to `/mnt/artifacts`
3. Update validation to not require dataset mount path

**Before:**
```python
def _build_job_command(req: JobRequest, spec_path: str, dataset_path: str = "") -> list[str]:
    if not (dataset_path or "").strip():
        raise ValueError("internal: dataset_path is required to build the job command")
    command = [
        "python", "/mnt/imported/code/...",
        "--spec", spec_path,
        "--dataset-path", dataset_path.strip(),
        ...
    ]
```

**After:**
```python
def _build_job_command(req: JobRequest, spec_path: str) -> list[str]:
    command = [
        "python", "/mnt/imported/code/...",
        "--spec", spec_path,
        "--output_dir", "/mnt/artifacts",
        ...
    ]
```

**Callsites:**
- `_submit_domino_job()` — Remove `dataset_mount_path` parameter
- Route handler `/api/jobs/submit` — Remove dataset mount resolution

### Phase 3: CLI Updates

**File: `auto_model_docs/main.py`**

Changes:
1. Replace `--dataset-path` with `--output_dir`
2. Default to `/mnt/artifacts` if running in job container
3. Allow override for local development

**Before:**
```python
@click.option(
    "--dataset-path",
    type=click.Path(),
    required=True,
    help="Mount path of the autodoc dataset (e.g. /domino/datasets/local/autodoc)",
)
def main(..., dataset_path: str):
    init_layout()
    output_dir = get_layout().docs_dir  # Incorrect: this is just "docs"
```

**After:**
```python
@click.option(
    "--output_dir",
    type=click.Path(),
    default="/mnt/artifacts",
    help="Root artifacts directory (default: /mnt/artifacts)",
)
def main(..., output_dir: str):
    from artifact_layout import init_layout
    init_layout()
    # output_dir is now /mnt/artifacts
    # docs get written to /mnt/artifacts/docs/<timestamp>/
```

### Phase 4: DocumentBuilder & NotebookBuilder

**File: `auto_model_docs/autodoc/generation/builder.py`**

Current behavior:
- Takes `dataset_mount_path` as init parameter
- Uses timestamp for filename: `model_docs_<timestamp>.docx`
- Writes to local path, then assumes DatasetManager handles upload

Changes:
1. Take `output_dir` (root artifacts path) instead of `dataset_mount_path`
2. Generate timestamp-based run directory: `docs/<date_yyy-mm-dd_hh-mm-ss>/`
3. Write directly to `/mnt/artifacts/docs/<timestamp>/model_docs.docx`
4. Use `artifact_layout.get_layout().docs_dir` for path resolution

**Before:**
```python
def __init__(self, output_dir: str = "docs", dataset_mount_path: str = "", run_id: str = ""):
    self.output_dir = output_dir
    self.dataset_mount_path = dataset_mount_path
    self.run_id = run_id

def save(self):
    filename = f"model_docs_{self.run_id}.docx"
    dataset_path = f"{get_layout().docs_dir}/{filename}"
    docx_bytes = ...
    DatasetManager.write_file(snap, dataset_path, docx_bytes)
```

**After:**
```python
def __init__(self, output_dir: str = "/mnt/artifacts", run_id: str = ""):
    self.output_dir = output_dir
    self.run_id = run_id
    self.timestamp_dir = generate_timestamp_dir()  # e.g., "docs/2026-05-27_14-30-45"

def save(self):
    filepath = f"{self.timestamp_dir}/model_docs.docx"
    docx_bytes = ...
    artifact_layout.get_layout().write_file(filepath, docx_bytes)
    # OR for filesystem: domino_artifacts.write_artifact(filepath, docx_bytes)
```

**Similar updates for:**
- `auto_model_docs/autodoc/generation/notebook_builder.py` — Write notebooks to `docs/<timestamp>/model_docs.ipynb`
- `auto_model_docs/autodoc/generation/notebook_exporter.py` — Same pattern

### Phase 5: Routes & Endpoints

**File: `auto_model_docs/studio/routes_api.py`**

Endpoints affected:

1. **`/api/jobs/submit`** — Remove dataset mount path resolution
   - Delete: `_autodoc_dataset_and_snapshot()` calls
   - Delete: `domino_datasets.resolve_dataset_mount_path()`
   - Pass only `spec_path` to `_submit_domino_job()`

2. **`/api/preview-doc`** — Read from artifacts instead of dataset
   - Before: Read from `snap` (dataset snapshot)
   - After: Read from `/mnt/artifacts/docs/<run_id>/model_docs.docx`
   - Use `artifact_layout` or `ArtifactStore` to resolve path

3. **`/api/job-history`** — List generated docs
   - Before: Query dataset files
   - After: List artifacts in `docs/` directory
   - Return relative paths for UI

### Phase 6: Remove DatasetManager Dependencies

**Files affected:**
- `auto_model_docs/studio/routes_api.py`
- `auto_model_docs/studio/routes_job.py`
- `auto_model_docs/orchestrator.py`

Changes:
1. Remove imports of `DatasetManager`, `domino_datasets`
2. Remove all `snap` (snapshot ID) references
3. Use `artifact_layout` and `domino_artifacts` instead

### Phase 7: Timestamp Directory Generation

**Add helper function to `artifact_layout.py`:**

```python
def generate_run_dir(timestamp: datetime | None = None) -> str:
    """Generate docs/<YYYY-MM-DD_HH-MM-SS> directory path."""
    if timestamp is None:
        timestamp = datetime.now()
    date_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    return f"docs/{date_str}"
```

Or store `run_id` and use `docs/<run_id>/` if DOMINO_RUN_ID is available.

## Testing Strategy

### Unit Tests

1. **`tests/test_artifact_layout.py`** (from reference)
   - Path resolution: `docs_dir`, `specs_dir`, `generation_cache`
   - Singleton behavior

2. **`tests/test_builder.py`** — New tests
   - DocumentBuilder writes to `/mnt/artifacts/docs/<timestamp>/model_docs.docx`
   - NotebookBuilder writes to `/mnt/artifacts/docs/<timestamp>/model_docs.ipynb`
   - Correct directory creation

3. **`tests/test_job_engine.py`** — Update existing
   - `_build_job_command()` includes `--output_dir /mnt/artifacts`
   - No `--dataset-path` in command
   - No dataset mount path validation

4. **`tests/test_routes.py`** — Update
   - `/api/preview-doc` reads from artifacts
   - `/api/job-history` lists docs from artifacts
   - Error handling for missing files

### Integration Tests (Chrome MCP)

**Manual test via UI:**

1. Start job via autodoc UI
2. Verify job completes successfully
3. Check `/mnt/artifacts/docs/<date>/model_docs.docx` exists
   - Via DFS UI in Domino
   - Via filesystem in job container
4. Verify docx is valid and openable
5. Verify notebook exists (if --notebook flag)

**Chrome test script (optional):**
```javascript
// In @agent_automation/scripts/verify_artifacts.sh
# After job completes, verify files exist
ls -la /mnt/artifacts/docs/*/model_docs.docx
file /mnt/artifacts/docs/*/model_docs.docx  # Should be Zip archive
```

## Risk Mitigation

1. **Backwards compatibility:** The change is one-directional (dataset → artifacts)
   - Old dataset-based jobs still work (read-only)
   - New jobs use artifacts
   - No mixed-mode required

2. **File I/O reliability:** Use `artifact_layout.write_artifact()` in job containers
   - Filesystem I/O is more reliable than REST API
   - Avoids network retries during generation

3. **Testing Coverage:** Add unit + integration tests
   - Ensure timestamp directory creation works
   - Verify file permissions and accessibility

## Dependencies

**New modules from reference repo:**
- `domino_artifacts.py` — 378 lines, no external deps
- `artifact_layout.py` — 77 lines, simple path logic

**Removed dependencies:**
- `dataset_manager.DatasetManager` (web app only)
- `domino_datasets` (web app only)
- `--dataset-path` CLI arg

## Files to Modify

1. ✅ Add: `auto_model_docs/domino_artifacts.py`
2. ✅ Add: `auto_model_docs/artifact_layout.py`
3. ✅ Modify: `auto_model_docs/main.py` — Replace `--dataset-path` with `--output_dir`
4. ✅ Modify: `auto_model_docs/studio/job_engine.py` — Remove dataset_path from command building
5. ✅ Modify: `auto_model_docs/autodoc/generation/builder.py` — Write to `/mnt/artifacts`
6. ✅ Modify: `auto_model_docs/autodoc/generation/notebook_builder.py` — Write to `/mnt/artifacts`
7. ✅ Modify: `auto_model_docs/autodoc/generation/notebook_exporter.py` — Write to `/mnt/artifacts`
8. ✅ Modify: `auto_model_docs/studio/routes_api.py` — Read from artifacts
9. ✅ Modify: `auto_model_docs/studio/routes_job.py` — Remove dataset handling
10. ✅ Modify: `auto_model_docs/orchestrator.py` — Pass output_dir instead of dataset_mount_path
11. ✅ Add: `tests/test_artifact_layout.py` — Unit tests
12. ✅ Update: `tests/test_job_engine.py` — Test command building
13. ✅ Update: `tests/test_builder.py` — Test artifact writes

## Timeline

- **Phase 1 (Artifact modules):** 30 min
- **Phase 2 (Job command building):** 30 min
- **Phase 3 (CLI updates):** 20 min
- **Phase 4 (Builder updates):** 45 min
- **Phase 5 (Routes):** 45 min
- **Phase 6 (Cleanup):** 30 min
- **Phase 7 (Testing):** 60 min
- **Manual testing (Chrome MCP):** 30 min

**Total: ~4-5 hours**
