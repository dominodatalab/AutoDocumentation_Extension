from __future__ import annotations

import os
import sys

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

import default_consts as dc


def test_defaults_match_product_spec():
    assert dc.DEFAULT_PROVIDER == "openai"
    assert dc.DEFAULT_MAX_FILES == 50
    assert dc.DEFAULT_GENERATION_WORKERS == 4
    assert dc.DEFAULT_PLANNING_WORKERS == 4
    assert dc.DEFAULT_TIMEOUT == 120.0
    assert dc.DEFAULT_LANGUAGE == "auto"
    assert dc.DEFAULT_LLM_MAX_RETRIES == 5
    assert dc.DEFAULT_LLM_INITIAL_BACKOFF == 10.0
    assert dc.DEFAULT_LLM_MAX_BACKOFF == 120.0
    assert dc.DEFAULT_LLM_BACKOFF_JITTER == 0.2
    assert "auto" in dc.ALLOWED_LANGUAGES
    assert "fortran" not in dc.ALLOWED_LANGUAGES
