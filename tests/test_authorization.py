from __future__ import annotations

import os
import sys

import pytest
from starlette.exceptions import HTTPException

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import authorization as auth


@pytest.mark.parametrize(
    "fn,arg",
    [
        (auth.require_domino_job_start, "p1"),
        (auth.require_domino_job_stop, "run-1"),
        (auth.require_domino_job_list, "p1"),
        (auth.require_project_write, "p1"),
    ],
)
def test_require_helpers_are_no_ops(fn, arg):
    fn(arg)
    fn(None)


def test_require_helpers_never_raise_http_exception():
    for fn in (
        auth.require_domino_job_start,
        auth.require_domino_job_stop,
        auth.require_domino_job_list,
        auth.require_project_write,
    ):
        try:
            fn("x")
        except HTTPException:
            pytest.fail(f"{fn.__name__} should not raise HTTPException")
