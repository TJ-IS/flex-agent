"""Helpers for running async eval code from sync or nested async contexts."""

from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import Coroutine, Mapping
from typing import Any, TypeVar

from flex_agent.config import trace_invoke_config

T = TypeVar("T")


async def ainvoke_chain(
    chain: Any,
    payload: Mapping[str, Any],
    *,
    component: str | None = None,
) -> Any:
    """Invoke a LangChain runnable, preferring native async when available."""
    invoke_config = trace_invoke_config(component)
    ainvoke = getattr(chain, "ainvoke", None)
    if callable(ainvoke):
        if invoke_config:
            return await ainvoke(dict(payload), config=invoke_config)
        return await ainvoke(dict(payload))
    if invoke_config:
        return await asyncio.to_thread(
            lambda: chain.invoke(dict(payload), config=invoke_config)
        )
    return await asyncio.to_thread(chain.invoke, dict(payload))


def run_async(coro: Coroutine[object, object, T]) -> T:
    """Run *coro* whether or not an event loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()
