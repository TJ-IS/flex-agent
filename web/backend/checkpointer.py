from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Any

from flex_agent.config import WORKSPACES_ROOT
from flex_agent.orchestration import factory as agent_factory
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

_checkpointer: AsyncSqliteSaver | None = None
_context: AbstractAsyncContextManager[AsyncSqliteSaver] | None = None


def _checkpoint_db_path() -> str:
    WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)
    return str(WORKSPACES_ROOT / ".checkpoints.sqlite")


async def init_checkpointer() -> AsyncSqliteSaver:
    """Replace in-memory checkpointer with sqlite-backed persistence for web."""
    global _checkpointer, _context
    if _checkpointer is not None:
        return _checkpointer

    _context = AsyncSqliteSaver.from_conn_string(_checkpoint_db_path())
    _checkpointer = await _context.__aenter__()
    await _checkpointer.setup()
    agent_factory._CHECKPOINTER = _checkpointer
    return _checkpointer


async def close_checkpointer() -> None:
    global _checkpointer, _context
    if _context is not None:
        await _context.__aexit__(None, None, None)
    _checkpointer = None
    _context = None


def get_checkpointer() -> AsyncSqliteSaver:
    if _checkpointer is None:
        raise RuntimeError("Checkpointer not initialized; call init_checkpointer() first.")
    return _checkpointer
