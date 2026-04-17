# Auto Model Documentation

A FastHTML app that generates ML model documentation (.docx and .ipynb) from codebases and MLflow artifacts using LLM-powered analysis. Runs as a Domino App with documentation generation dispatched as Domino Jobs, or standalone via CLI.

## Architecture & Design

See [auto_model_docs/README.md](./auto_model_docs/README.md) for the pipeline architecture, scanner stages, Studio UI design, and full configuration reference. Studio design tokens are in [auto_model_docs/DESIGN.md](./auto_model_docs/DESIGN.md).

## Prerequisites

- Python 3.10 or newer
- An Anthropic or OpenAI API key
- MLflow tracking server (optional, only needed for model metadata in generated docs)
- For Domino deployment: a Domino Data Lab workspace with Extended Identity Propagation enabled

## Installation

From the repository root:

```bash
cd auto_model_docs
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

This installs the `autodoc` package along with dev dependencies (pytest, etc.).

## Configuration

Set at least one API key as an environment variable. Any of these work:

```bash
# Option 1: export in your shell
export ANTHROPIC_API_KEY=sk-ant-...

# Option 2: inline per command
ANTHROPIC_API_KEY=sk-ant-... python main.py --spec doc_spec.yaml

# Option 3: use a .env file (optional)
cp .env.example .env
```

Common optional variables:
<<<<<<< HEAD

```bash
LLM_PROVIDER=anthropic              # or openai (default: anthropic)
LLM_MODEL=claude-sonnet-4-20250514  # override the provider default
MLFLOW_TRACKING_URI=http://localhost:5000
CODE_ROOT=/path/to/your/ml/project  # default: /mnt/code or current dir
```

Any variable can be prefixed with `AUTODOC_` for namespace isolation (e.g. `AUTODOC_LLM_PROVIDER`). Full configuration reference lives in [auto_model_docs/README.md](./auto_model_docs/README.md#configuration).

## Usage

### Web UI (Studio)

Studio is the primary interface. Run it locally:

```bash
cd auto_model_docs
python web_app_studio.py
# Open http://localhost:8888
```

The UI is a 3-column FastHTML app: spec file selection, run configuration (branch, hardware tier, advanced settings), and job history. When running locally the job history and dataset browser features require a Domino backend; without one, use the CLI.

### Domino deployment

The app is designed to run as a Domino App with Extended Identity Propagation enabled. The startup script is `auto_model_docs/app_studio.sh`.

1. In your Domino project, set the App command to `auto_model_docs/app_studio.sh`.
2. Set the following environment variables on the App:
   - `DOMINO_API_HOST` (required) -- Domino API host URL
   - `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (required)
   - `AUTODOC_MAX_JOBS` (optional, default: 1) -- max concurrent jobs per user
3. Start the App. Access it with `?projectId=<target-project-id>` appended to the URL. All specs, jobs, output, and history live in the target project's `autodoc` dataset; the App project only hosts the process.

Documentation generation runs as a separate Domino Job in the target project, so the App container only needs FastHTML plus the Domino client libraries.

### CLI

The CLI is useful for local runs, scripted generation, and regenerating notebooks from cached results.

```bash
cd auto_model_docs
python main.py --spec doc_spec.yaml
```

Common flags:

| Flag | Description |
|---|---|
| `--spec`, `-s` | Path to YAML spec (required) |
| `--provider`, `-p` | `anthropic` or `openai` (CLI default: `openai`) |
| `--model`, `-m` | Model name override |
| `--code-root`, `-c` | Directory to scan (default: `/mnt/code` or `.`) |
| `--notebook` | Also generate an editable Jupyter notebook |
| `--notebook-from-cache` | Regenerate notebook from cached results (skips LLM calls) |
| `--models` | Comma-separated model name patterns (supports `*` wildcards) |
| `--latest-only` | Only include the latest version of each model |
| `--verbose`, `-v` | Verbose logging |

Example spec file (`doc_spec.yaml`):

```yaml
title: "Model Documentation"
authors: "Data Science Team"
sections:
  - "Executive Summary"
  - "Data Overview"
  - "Feature Engineering"
  - "Model Performance: per_model"   # one subsection per registered model
  - "Deployment Considerations"

hints:
  "Executive Summary": >
    Focus on business impact and key metrics.
    Keep it suitable for non-technical stakeholders.
```

<<<<<<< HEAD
Output is written to `output/` by default (or `/mnt/data/{project}` under Domino).

## Sample Projects

Three demo ML projects with MLflow integration live under [`sample_projects/`](sample_projects/). Each project includes data generation, training scripts, and MLflow experiment tracking so you can produce realistic input for the documentation pipeline:

```bash
cd sample_projects/01_customer_churn
pip install -r requirements.txt
python train.py --generate-data
```

See [sample_projects/README.md](./sample_projects/README.md) for the full walkthrough.

## Testing

Two test suites cover the codebase:

```bash
# Core library tests (scanning, generation, LLM client, config)
python -m pytest auto_model_docs/tests/

# Studio and Domino integration tests
python -m pytest tests/
```

Run both with coverage:

```bash
python -m pytest auto_model_docs/tests/ tests/ --cov=auto_model_docs
```
=======
### 4. Run

**CLI:**
=======
>>>>>>> 94730d2 (simplified README)

```bash
LLM_PROVIDER=anthropic              # or openai (default: anthropic)
LLM_MODEL=claude-sonnet-4-20250514  # override the provider default
MLFLOW_TRACKING_URI=http://localhost:5000
CODE_ROOT=/path/to/your/ml/project  # default: /mnt/code or current dir
```

Any variable can be prefixed with `AUTODOC_` for namespace isolation (e.g. `AUTODOC_LLM_PROVIDER`). Full configuration reference lives in [auto_model_docs/README.md](./auto_model_docs/README.md#configuration).

## Usage

### Web UI (Studio)

Studio is the primary interface. Run it locally:

```bash
cd auto_model_docs
python web_app_studio.py
# Open http://localhost:8888
```

The UI is a 3-column FastHTML app: spec file selection, run configuration (branch, hardware tier, advanced settings), and job history. When running locally the job history and dataset browser features require a Domino backend; without one, use the CLI.

### Domino deployment

The app is designed to run as a Domino App with Extended Identity Propagation enabled. The startup script is `auto_model_docs/app_studio.sh`.

1. In your Domino project, set the App command to `auto_model_docs/app_studio.sh`.
2. Set the following environment variables on the App:
   - `DOMINO_API_HOST` (required) -- Domino API host URL
   - `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (required)
   - `AUTODOC_MAX_JOBS` (optional, default: 1) -- max concurrent jobs per user
3. Start the App. Access it with `?projectId=<target-project-id>` appended to the URL. All specs, jobs, output, and history live in the target project's `autodoc` dataset; the App project only hosts the process.

Documentation generation runs as a separate Domino Job in the target project, so the App container only needs FastHTML plus the Domino client libraries.

### CLI

The CLI is useful for local runs, scripted generation, and regenerating notebooks from cached results.

```bash
cd auto_model_docs
python main.py --spec doc_spec.yaml
```

Common flags:

| Flag | Description |
|---|---|
| `--spec`, `-s` | Path to YAML spec (required) |
| `--provider`, `-p` | `anthropic` or `openai` (CLI default: `openai`) |
| `--model`, `-m` | Model name override |
| `--code-root`, `-c` | Directory to scan (default: `/mnt/code` or `.`) |
| `--notebook` | Also generate an editable Jupyter notebook |
| `--notebook-from-cache` | Regenerate notebook from cached results (skips LLM calls) |
| `--models` | Comma-separated model name patterns (supports `*` wildcards) |
| `--latest-only` | Only include the latest version of each model |
| `--verbose`, `-v` | Verbose logging |

Example spec file (`doc_spec.yaml`):

```yaml
title: "Model Documentation"
authors: "Data Science Team"
sections:
  - "Executive Summary"
  - "Data Overview"
  - "Feature Engineering"
  - "Model Performance: per_model"   # one subsection per registered model
  - "Deployment Considerations"

hints:
  "Executive Summary": >
    Focus on business impact and key metrics.
    Keep it suitable for non-technical stakeholders.
```

Output is written to `output/` by default (or `/mnt/data/{project}` under Domino).

## Sample Projects

Three demo ML projects with MLflow integration live under [`sample_projects/`](sample_projects/). Each project includes data generation, training scripts, and MLflow experiment tracking so you can produce realistic input for the documentation pipeline:

```bash
cd sample_projects/01_customer_churn
pip install -r requirements.txt
python train.py --generate-data
```

See [sample_projects/README.md](./sample_projects/README.md) for the full walkthrough.

## Testing

Two test suites cover the codebase:

```bash
# Core library tests (scanning, generation, LLM client, config)
python -m pytest auto_model_docs/tests/

# Studio and Domino integration tests
python -m pytest tests/
```
