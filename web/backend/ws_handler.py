from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable

from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError

from flex_agent.config import load_recursion_limit
from flex_agent.i18n import get_bundle
from flex_agent.ui.events import StepStatus, TimelineEntry, UIUpdate
from flex_agent.ui.helpers import handle_slash_command

from web.backend.events_serializer import (
    serialize_banner_event,
    serialize_error_message,
    serialize_idle,
    serialize_system_message,
    serialize_ui_update,
    serialize_user_echo,
    workspace_summary,
)
from web.backend.session_manager import AgentRuntime, agent_turn_lock, session_manager

SendFn = Callable[[dict[str, Any]], Awaitable[None]]


async def send_banner(runtime: AgentRuntime, send: SendFn) -> None:
    await send(serialize_banner_event(runtime.workspace, runtime.language))


async def send_workspace_status(runtime: AgentRuntime, send: SendFn) -> None:
    bundle = get_bundle(runtime.language)
    await send(
        {
            "type": "update",
            "timeline": [
                {
                    "kind": "system",
                    "text": f"{bundle.cli.workspace_prefix} · {workspace_summary(runtime.workspace)}",
                    "step_id": None,
                }
            ],
            "steps": {},
            "todos": [],
            "streaming_assistant": None,
            "activity_mode": None,
        }
    )


async def handle_user_message(
    runtime: AgentRuntime,
    user_text: str,
    send: SendFn,
) -> bool:
    """Process one user message. Returns False if session should close (exit)."""
    cleaned = user_text.strip()
    if not cleaned:
        return True

    if cleaned.lower() in {"exit", "quit", "/exit", "/quit"}:
        bundle = get_bundle(runtime.language)
        await send(serialize_system_message(bundle.cli.bye))
        return False

    await send(serialize_user_echo(cleaned))

    handled, output = handle_slash_command(runtime.workspace, cleaned)
    if handled:
        await _emit_slash_output(runtime, cleaned, output, send)
        return True

    runtime.parser.note_user_message(cleaned, emit=False)

    async with agent_turn_lock:
        session_manager.activate_session_globals(runtime)
        await _stream_agent_turn(runtime, cleaned, send)

    return True


async def _emit_slash_output(
    runtime: AgentRuntime,
    command: str,
    output: str | None,
    send: SendFn,
) -> None:
    if not output:
        return
    cmd = command.strip().lower().split()[0]
    async with agent_turn_lock:
        session_manager.activate_session_globals(runtime)
        if cmd == "/status":
            await send_workspace_status(runtime, send)
            await send(serialize_system_message(output))
        elif cmd in {"/help", "/eval:open", "/eval:axial"}:
            await send(serialize_system_message(output))
        elif cmd == "/clear":
            update = UIUpdate(
                timeline=[TimelineEntry(kind="system", text=output)],
                refresh_workspace=True,
            )
            await send(
                serialize_ui_update(
                    update,
                    workspace=runtime.workspace,
                    language=runtime.language,
                )
            )
        else:
            await send(serialize_system_message(output))


async def _stream_agent_turn(
    runtime: AgentRuntime,
    user_text: str,
    send: SendFn,
) -> None:
    interrupt_event = asyncio.Event()
    runtime.interrupt_event = interrupt_event
    inputs = {"messages": [HumanMessage(content=user_text)]}
    consume_task: asyncio.Task | None = None

    async def _consume() -> None:
        async for chunk in runtime.agent.astream(
            inputs,
            config=runtime.config,
            stream_mode="values",
        ):
            if interrupt_event.is_set():
                break
            update = runtime.parser.consume(chunk)
            await send(
                serialize_ui_update(
                    update,
                    workspace=runtime.workspace,
                    language=runtime.language,
                )
            )

    consume_task = asyncio.create_task(_consume())
    runtime.active_turn = consume_task
    interrupted = False

    try:
        await consume_task
    except asyncio.CancelledError:
        interrupted = True
    finally:
        runtime.active_turn = None
        runtime.interrupt_event = None

    if interrupted or interrupt_event.is_set():
        bundle = get_bundle(runtime.language)
        update = runtime.parser.mark_interrupted()
        await send(
            serialize_ui_update(
                update,
                workspace=runtime.workspace,
                language=runtime.language,
            )
        )
        for step in update.steps.values():
            if step.status == StepStatus.ERROR and step.result_preview == "interrupted":
                await send(
                    {
                        "type": "step_refresh",
                        "step": {
                            "step_id": step.step_id,
                            "tool_name": step.tool_name,
                            "label": step.label,
                            "summary": step.summary,
                            "status": step.status.value,
                            "result_preview": step.result_preview,
                        },
                    }
                )
        await send(serialize_error_message(bundle.cli.interrupted))
        await send_workspace_status(runtime, send)
        await send(serialize_idle())
        return

    final = runtime.parser.flush_assistant_text()
    await send(
        serialize_ui_update(
            final,
            workspace=runtime.workspace,
            language=runtime.language,
        )
    )
    await send_workspace_status(runtime, send)
    await send(serialize_idle())


async def handle_interrupt(runtime: AgentRuntime, send: SendFn) -> None:
    if runtime.interrupt_event:
        runtime.interrupt_event.set()
    if runtime.active_turn and not runtime.active_turn.done():
        runtime.active_turn.cancel()
        try:
            await runtime.active_turn
        except asyncio.CancelledError:
            pass


async def handle_agent_error(
    runtime: AgentRuntime,
    exc: BaseException,
    send: SendFn,
) -> None:
    bundle = get_bundle(runtime.language)
    if isinstance(exc, GraphRecursionError):
        limit = runtime.config.get("recursion_limit", load_recursion_limit())
        update = runtime.parser.mark_error(exc)
        await send(
            serialize_ui_update(
                update,
                workspace=runtime.workspace,
                language=runtime.language,
            )
        )
        for step in update.steps.values():
            if step.status == StepStatus.ERROR:
                await send(
                    {
                        "type": "step_refresh",
                        "step": {
                            "step_id": step.step_id,
                            "tool_name": step.tool_name,
                            "label": step.label,
                            "summary": step.summary,
                            "status": step.status.value,
                            "result_preview": step.result_preview,
                        },
                    }
                )
        await send(
            serialize_error_message(
                bundle.cli.recursion_limit_reached.format(limit=limit)
            )
        )
    else:
        update = runtime.parser.mark_error(exc)
        await send(
            serialize_ui_update(
                update,
                workspace=runtime.workspace,
                language=runtime.language,
            )
        )
        for step in update.steps.values():
            if step.status == StepStatus.ERROR:
                await send(
                    {
                        "type": "step_refresh",
                        "step": {
                            "step_id": step.step_id,
                            "tool_name": step.tool_name,
                            "label": step.label,
                            "summary": step.summary,
                            "status": step.status.value,
                            "result_preview": step.result_preview,
                        },
                    }
                )
    await send_workspace_status(runtime, send)
    await send(serialize_idle())


async def ws_message_loop(
    runtime: AgentRuntime,
    websocket: Any,
) -> None:
    async def send(payload: dict[str, Any]) -> None:
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))

    await send_banner(runtime, send)

    while True:
        raw = await websocket.receive_text()
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            message = {"type": "message", "text": raw}

        msg_type = message.get("type", "message")
        if msg_type == "interrupt":
            await handle_interrupt(runtime, send)
            continue

        text = str(message.get("text", ""))
        try:
            should_continue = await handle_user_message(runtime, text, send)
        except GraphRecursionError as exc:
            await handle_agent_error(runtime, exc, send)
            continue
        except Exception as exc:
            await handle_agent_error(runtime, exc, send)
            continue

        if not should_continue:
            break
