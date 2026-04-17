import os
import sys

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from studio.job_engine import _build_job_command
from studio.state import JobRequest


def _sample_request(**overrides):
    base = dict(
        spec_path="s.yaml",
        provider="openai",
        model="m",
        code_root="/code",
        max_files=50,
        workers=4,
        planning_workers=2,
        timeout=120.0,
        notebook=False,
        notebook_path="",
        filtered_experiment_names="",
        filtered_model_names="",
        latest_only=False,
        verbose=False,
        hardware_tier="",
        environment_id="",
        environment_revision_id="",
        project_id="p",
        provider_base_url="",
        max_retries=3,
        initial_backoff=1.0,
        max_backoff=20.0,
        backoff_jitter=0.2,
        notebook_from_cache=False,
        prompts_file="",
    )
    base.update(overrides)
    return JobRequest(**base)


def test_build_job_command_includes_prompts_file_when_set():
    req = _sample_request(prompts_file="/mnt/data/custom_prompts.yaml")
    cmd = _build_job_command(req, "/spec.yaml")
    idx = cmd.index("--prompts-file")
    assert cmd[idx + 1] == "/mnt/data/custom_prompts.yaml"


def test_build_job_command_omits_prompts_file_when_empty():
    req = _sample_request(prompts_file="")
    cmd = _build_job_command(req, "/spec.yaml")
    assert "--prompts-file" not in cmd


def test_build_job_command_uses_domino_mdocs_cli_install_dir(monkeypatch):
    monkeypatch.setenv("DOMINO_MDOCS_CLI_INSTALL_DIR", "/opt/autodoc")
    req = _sample_request()
    cmd = _build_job_command(req, "/spec.yaml")
    assert cmd[0] == "/opt/autodoc/cli.sh"
