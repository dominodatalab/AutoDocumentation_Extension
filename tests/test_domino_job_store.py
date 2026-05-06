"""Tests for domino_job_store.py."""

from __future__ import annotations

import os
import sys

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import domino_job_store as store


def test_get_user_jobs_empty():
    assert store.get_user_jobs("ds", "snap", "alice", limit=10) == []


def test_cancel_queued_jobs_noop():
    store.cancel_queued_jobs("ds", "snap", "alice")
