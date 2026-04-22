"""Per-request dataset identity via ContextVar.

Holds the (dataset_id, snapshot_id) pair the current request (or the current
CLI invocation) should read/write against. DatasetManager methods are pure
statics and never touch this module; callers must pass the ids explicitly.
This helper is just a convenient transport for code paths where threading
the ids through every function would be intrusive.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DatasetCtx:
    dataset_id: str
    snapshot_id: str


_ctx_var: ContextVar[Optional[DatasetCtx]] = ContextVar(
    "autodoc_dataset_ctx", default=None
)


def set_dataset_ctx(dataset_id: str, snapshot_id: str) -> None:
    if not dataset_id or not snapshot_id:
        raise ValueError("dataset_id and snapshot_id are both required")
    _ctx_var.set(DatasetCtx(dataset_id=dataset_id, snapshot_id=snapshot_id))


def get_dataset_ctx() -> DatasetCtx:
    v = _ctx_var.get()
    if v is None:
        raise RuntimeError(
            "Dataset context not set. Call set_dataset_ctx() at the top of the "
            "request handler or CLI entry point before invoking DatasetManager."
        )
    return v


def try_get_dataset_ctx() -> Optional[DatasetCtx]:
    return _ctx_var.get()


def clear_dataset_ctx() -> None:
    _ctx_var.set(None)
