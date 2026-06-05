#!/usr/bin/env python3
"""CLI entry point for Auto Model Documentation."""

import asyncio
import logging
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

# Add the parent directory to path for local development
sys.path.insert(0, str(Path(__file__).parent))

from autodoc.core.config import Settings
from autodoc.core.models import DocumentSpec
from default_consts import (
    DEFAULT_GENERATION_WORKERS,
    DEFAULT_LANGUAGE,
    DEFAULT_MAX_FILES,
    DEFAULT_PLANNING_WORKERS,
    DEFAULT_PROVIDER,
    DEFAULT_TIMEOUT,
)
from autodoc.llm import LLMClient
from autodoc.orchestrator import Orchestrator
from autodoc.scanning import ContentSanitizer


console = Console()


@click.command()
@click.option(
    "--spec",
    "-s",
    required=True,
    type=click.Path(exists=True),
    help="Path to YAML document specification",
)
@click.option(
    "--code-root",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Root directory of codebase to analyze",
)
@click.option(
    "--provider",
    "-p",
    default=DEFAULT_PROVIDER,
    type=click.Choice(["anthropic", "openai"]),
    help="LLM provider to use",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model name override (uses provider default if not set)",
)
@click.option(
    "--provider-base-url",
    default=None,
    type=str,
    help="Override API base URL for the selected provider (OpenAI or Anthropic)",
)
@click.option(
    "--max-retries",
    default=None,
    type=int,
    help="Max retries for LLM requests",
)
@click.option(
    "--initial-backoff",
    default=None,
    type=float,
    help="Initial backoff delay in seconds",
)
@click.option(
    "--max-backoff",
    default=None,
    type=float,
    help="Maximum backoff delay in seconds",
)
@click.option(
    "--backoff-jitter",
    default=None,
    type=float,
    help="Random jitter factor applied to backoff",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--max-files",
    default=DEFAULT_MAX_FILES,
    type=int,
    help="Maximum number of files to scan",
)
@click.option(
    "--generation-workers",
    "-w",
    "workers",
    default=DEFAULT_GENERATION_WORKERS,
    type=int,
    help="Number of parallel workers for content generation",
)
@click.option(
    "--planning-workers",
    default=DEFAULT_PLANNING_WORKERS,
    type=int,
    help="Number of parallel workers for section planning",
)
@click.option(
    "--notebook",
    is_flag=True,
    help="Also generate editable Jupyter notebook",
)
@click.option(
    "--notebook-from-cache",
    is_flag=True,
    help="Regenerate notebook from cached results (skips full pipeline)",
)
@click.option(
    "--notebook-path",
    type=click.Path(),
    help="Custom path for the generated notebook (default: <output>/model_docs_notebook.ipynb)",
)
@click.option(
    "--timeout",
    default=DEFAULT_TIMEOUT,
    type=float,
    help="Timeout for individual LLM API calls in seconds (default: 120)",
)
@click.option(
    "--filtered-experiments",
    "filtered_experiments",
    type=str,
    help="Comma-separated experiment names/patterns to include. Wildcards: * and ?. Example: customer_churn*,fraud_detection",
)
@click.option(
    "--filtered-models",
    "filtered_models",
    type=str,
    help="Comma-separated MLflow model names/patterns to include. Wildcards: * and ?. Example: churn*,fraud_detector",
)
@click.option(
    "--latest-only",
    is_flag=True,
    help="Only include the latest version of each model",
)
@click.option(
    "--language",
    default=DEFAULT_LANGUAGE,
    type=click.Choice(["auto", "python", "r", "sas", "matlab"], case_sensitive=False),
    help="Programming language for scanning, or auto to detect from repository files",
)
@click.option(
    "--output_dir",
    type=click.Path(),
    default="/mnt/artifacts",
    help="Root artifacts directory where docs and cache are stored (default: /mnt/artifacts)",
)
@click.option(
    "--bundle-id",
    default=None,
    type=str,
    help="Governance bundle UUID for this document run",
)
@click.option(
    "--governance-api-host",
    default=None,
    type=str,
    help="Domino cluster origin for governance API calls (from the browser)",
)
@click.option(
    "--findings-scope",
    default=None,
    type=click.Choice(["open", "all"], case_sensitive=False),
    help="Findings filter: open (To do only) or all",
)
def main(
    spec: str,
    code_root: str,
    provider: str,
    model: str | None,
    provider_base_url: str | None,
    max_retries: int | None,
    initial_backoff: float | None,
    max_backoff: float | None,
    backoff_jitter: float | None,
    verbose: bool,
    max_files: int,
    workers: int,
    planning_workers: int,
    notebook: bool,
    notebook_from_cache: bool,
    notebook_path: str | None,
    timeout: float,
    filtered_experiments: str | None,
    filtered_models: str | None,
    latest_only: bool,
    language: str,
    output_dir: str,
    bundle_id: str | None,
    governance_api_host: str | None,
    findings_scope: str | None,
) -> None:
    """Generate model documentation from ML codebases.

    This tool analyzes your ML codebase and generates a professional
    Word document with documentation about your models, features,
    and training pipelines.

    Example usage:

        python main.py --spec doc_spec.yaml --provider anthropic

    Environment variables (can be set in .env file):

        DOMINO_PROJECT_ID - Required. Domino project ID for MLflow filtering metadata.
        ANTHROPIC_API_KEY / OPENAI_API_KEY - LLM credentials (see Settings)

    For full configuration options, see the Settings class in autodoc/core/config.py
    """
    if not (os.environ.get("DOMINO_PROJECT_ID") or "").strip():
        console.print(
            "\n[bold red]Error:[/] DOMINO_PROJECT_ID is required. "
            "Set it to your Domino project ID before running.",
            style="red",
        )
        sys.exit(1)

    if not str(code_root).strip():
        console.print("\n[bold red]Error:[/] --code-root must be a non-empty path.", style="red")
        sys.exit(1)

    try:
        # Configure logging based on verbosity
        log_level = logging.INFO if verbose else logging.WARNING
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )

        # Load settings from .env and environment
        settings = Settings()

        # Override settings with CLI arguments if provided
        if provider:
            settings.llm_provider = provider
        if model:
            settings.llm_model = model
        if provider_base_url:
            b = provider_base_url.strip() or None
            if (settings.llm_provider or "").lower() == "anthropic":
                settings.anthropic_base_url = b
            else:
                settings.openai_base_url = b
        if max_retries is not None:
            settings.llm_max_retries = max_retries
        if initial_backoff is not None:
            settings.llm_initial_backoff = initial_backoff
        if max_backoff is not None:
            settings.llm_max_backoff = max_backoff
        if backoff_jitter is not None:
            settings.llm_backoff_jitter = backoff_jitter
        settings.code_root = Path(code_root)
        if max_files:
            settings.max_files = max_files
        if workers:
            settings.parallel_workers = workers
        if planning_workers:
            settings.planning_workers = planning_workers

        from artifact_layout import init_layout, get_layout
        init_layout()
        artifacts_root = output_dir.rstrip("/") or "/mnt/artifacts"
        code_dir = Path(code_root)

        # Handle --notebook-from-cache mode (regenerate from cache)
        if notebook_from_cache:
            _regenerate_notebook_from_cache(artifacts_root, verbose)
            return

        experiment_names = None
        if filtered_experiments:
            experiment_names = [
                name.strip() for name in filtered_experiments.split(",") if name.strip()
            ]

        model_names = None
        if filtered_models:
            model_names = [name.strip() for name in filtered_models.split(",") if name.strip()]

        console.print(f"\n[bold blue]Loading specification:[/] {spec}")
        doc_spec = DocumentSpec.from_yaml(spec)
        console.print(f"[bold]Document:[/] {doc_spec.title}")
        console.print(f"[bold]Sections:[/] {len(doc_spec.sections)}")

        if verbose:
            console.print(f"[dim]Code root:[/] {code_dir}")
            console.print(f"[dim]Artifacts root:[/] {artifacts_root}")
            console.print(f"[dim]Provider:[/] {settings.llm_provider}")
            console.print(f"[dim]Model:[/] {settings.get_model_name()}")
            console.print(f"[dim]Max files:[/] {settings.max_files}")
            console.print(f"[dim]Generation workers:[/] {settings.parallel_workers}")
            console.print(f"[dim]Planning workers:[/] {settings.planning_workers}")
            console.print(f"[dim]Notebook:[/] {notebook}")
            console.print(f"[dim]Max retries:[/] {settings.llm_max_retries}")
            console.print(f"[dim]Initial backoff:[/] {settings.llm_initial_backoff}")
            console.print(f"[dim]Max backoff:[/] {settings.llm_max_backoff}")
            console.print(f"[dim]Backoff jitter:[/] {settings.llm_backoff_jitter}")
            console.print(f"[dim]Timeout:[/] {timeout}s")
            if experiment_names:
                console.print(f"[dim]Experiments:[/] {', '.join(experiment_names)}")
            if model_names:
                console.print(f"[dim]Models:[/] {', '.join(model_names)}")
            if latest_only:
                console.print(f"[dim]Version filtering:[/] latest only")

        # Get API key from settings
        try:
            api_key = settings.get_api_key()
        except ValueError as e:
            console.print(f"\n[bold red]Error:[/] {e}", style="red")
            console.print("[dim]Set API keys in .env file or environment variables[/]")
            sys.exit(1)

        # Initialize components
        _pbu = (
            settings.anthropic_base_url
            if (settings.llm_provider or "").lower() == "anthropic"
            else settings.openai_base_url
        )
        llm = LLMClient(
            provider=settings.llm_provider,
            model=settings.get_model_name(),
            api_key=api_key,
            base_url=_pbu,
            max_retries=settings.llm_max_retries,
            initial_backoff=settings.llm_initial_backoff,
            max_backoff=settings.llm_max_backoff,
            backoff_jitter=settings.llm_backoff_jitter,
            timeout_seconds=timeout,
        )
        sanitizer = ContentSanitizer()
        orchestrator = Orchestrator(
            llm=llm,
            sanitizer=sanitizer,
            code_root=code_dir,
            output_dir=artifacts_root,
            mlflow_tracking_uri=settings.mlflow_tracking_uri,
            parallel_workers=settings.parallel_workers,
            planning_workers=settings.planning_workers,
            max_files=settings.max_files,
            max_file_size=settings.max_file_size,
            generate_notebook=notebook or bool(notebook_path),
            exclude_patterns=settings.exclude_patterns,
            max_selected_files=settings.max_selected_files,
            batch_size=settings.batch_size,
            analysis_timeout=settings.analysis_timeout,
            scan_retries=settings.scan_retries,
            scan_workers=settings.scan_workers,
            # Pass filtering options to orchestrator
            experiment_names=experiment_names,
            model_names=model_names,
            latest_only=latest_only,
            language=language,
        )

        governance_context = None
        if bundle_id:
            from domino_auth import cli_auth, configure_auth
            from autodoc.governance_read import GovernanceLoadError, load_governance_context

            configure_auth(cli_auth)
            scope = findings_scope or doc_spec.governance_findings_scope
            gov_host = (governance_api_host or "").strip()
            if not gov_host:
                console.print(
                    "\n[bold red]Error:[/] --governance-api-host is required when --bundle-id is set",
                    style="red",
                )
                sys.exit(1)
            try:
                governance_context = load_governance_context(
                    bundle_id,
                    api_host=gov_host,
                    findings_scope=scope,
                )
            except GovernanceLoadError as exc:
                console.print(f"\n[bold red]Error:[/] {exc}", style="red")
                sys.exit(1)
            if verbose:
                console.print(f"[dim]Governance bundle:[/] {bundle_id}")

        # Run generation with progress
        console.print("\n[bold blue]Starting document generation...[/]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("Initializing...", total=100)

            def on_progress(phase: str, pct: float) -> None:
                # Update progress with current phase and percentage
                completed = pct * 100
                progress.update(task_id, completed=completed, description=f"{phase}...")

            # Run async generation
            output_path = asyncio.run(
                orchestrator.generate(
                    doc_spec,
                    on_progress,
                    governance_context=governance_context,
                )
            )

        # Success!
        console.print(f"\n[bold green]Success![/] Document generated:")
        console.print(f"  [cyan]{output_path}[/]")
        if notebook or notebook_path:
            actual_notebook_path = f"{orchestrator.run_dir}/model_docs.ipynb"
            console.print(f"  [cyan]{actual_notebook_path}[/]")
        console.print()

    except FileNotFoundError as e:
        console.print(f"\n[bold red]Error:[/] File not found: {e}", style="red")
        sys.exit(1)
    except ValueError as e:
        console.print(f"\n[bold red]Error:[/] {e}", style="red")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/] {e}", style="red")
        if verbose:
            console.print_exception()
        sys.exit(1)


def _regenerate_notebook_from_cache(
    output_dir: str,
    verbose: bool,
) -> None:
    from autodoc.generation import NotebookBuilder
    from datetime import datetime
    from pathlib import Path as PathLib

    console.print("\n[bold blue]Regenerating notebook from cache...[/]\n")

    from artifact_layout import get_layout
    cache_path = get_layout().generation_cache
    if not (PathLib(output_dir) / cache_path).exists():
        console.print(
            f"[bold red]Error:[/] No cached results found at {cache_path}",
            style="red",
        )
        console.print("[dim]Run full generation first with --notebook flag[/]")
        sys.exit(1)

    from autodoc.orchestrator import Orchestrator

    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.output_dir = output_dir
    run_id = os.environ.get("DOMINO_RUN_ID", "")
    if run_id:
        orchestrator.run_dir = f"docs/{run_id[:8]}"
    else:
        orchestrator.run_dir = f"docs/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    orchestrator.notebook_builder = NotebookBuilder(output_dir=output_dir)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("Regenerating notebook...", total=100)

        def on_progress(phase: str, pct: float) -> None:
            completed = pct * 100
            progress.update(task_id, completed=completed, description=f"{phase}...")

        # Regenerate notebook from cache
        result_notebook_path = asyncio.run(orchestrator.regenerate_notebook(on_progress))

    console.print(f"\n[bold green]Success![/] Notebook regenerated:")
    console.print(f"  [cyan]{result_notebook_path}[/]")
    console.print()


if __name__ == "__main__":
    main()
