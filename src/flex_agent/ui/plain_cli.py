from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from time import strftime
from typing import Any

from langchain_core.messages import HumanMessage

from flex_agent.orchestration import create_flex_agent
from flex_agent.config import DEFAULT_WORKSPACE, PROJECT_ROOT, load_env_file
from flex_agent.ui.events import (
    StreamEventParser,
    StepStatus,
    UIUpdate,
    format_step_line,
    todo_icon,
)
from flex_agent.ui.helpers import handle_slash_command
from flex_agent.ui.interrupt import EscInterruptWatcher
from flex_agent.workspace import Workspace

SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

ACTIVITY_LABELS = {
    "thinking": "Agent 思考中",
    "tool": "执行工具",
    "streaming": "生成回复",
}


class TermStyle:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def _use_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _style(text: str, *codes: str) -> str:
    if not _use_color() or not codes:
        return text
    return "".join(codes) + text + TermStyle.RESET


def _print_line(text: str = "", *, file: Any = sys.stdout) -> None:
    print(text, flush=True, file=file)


def _clear_stderr_line() -> None:
    if _use_color():
        print("\r\033[K", end="", file=sys.stderr, flush=True)


def _format_workspace_summary(workspace: Workspace) -> str:
    status = workspace.status()
    parts = [
        f"texts={status.get('texts_total', 0)}",
        f"coded={status.get('coded_count', 0)}",
        f"queue={status.get('queue_remaining', 0)}",
        f"constructs={status.get('constructs_count', 0)}",
    ]
    run = status.get("run")
    if run and run.get("max_nums") is not None:
        parts.append(f"max={run['max_nums']}")
    return " · ".join(parts)


def _print_banner(workspace: Workspace) -> None:
    title = _style("flex-agent", TermStyle.BOLD)
    root = workspace.root
    summary = _format_workspace_summary(workspace)
    _print_line(f"{title}  workspace={root}")
    _print_line(_style(summary, TermStyle.GRAY))
    _print_line(_style("输入 open coding 任务，或 /status /tree /export /clear /help · Esc 中断 · exit 退出", TermStyle.GRAY))


def _print_timeline_entry(text: str, kind: str) -> None:
    if kind == "user":
        _print_line(_style(f"> {text}", TermStyle.BOLD, TermStyle.CYAN))
        return
    if kind == "assistant":
        _print_line(text)
        return
    if kind == "system":
        _print_line(_style(text, TermStyle.GRAY))
        return
    if kind == "error":
        _print_line(_style(f"error: {text}", TermStyle.YELLOW), file=sys.stderr)
        return
    _print_line(text)


def _print_todos(parser: StreamEventParser) -> None:
    if not parser.todos:
        return
    _print_line()
    _print_line(_style("Plan", TermStyle.BOLD, TermStyle.MAGENTA))
    for item in parser.todos:
        icon = todo_icon(item.status)
        line = f"  {icon} {item.content}"
        if item.status == "in_progress":
            _print_line(_style(line, TermStyle.YELLOW))
        elif item.status == "completed":
            _print_line(_style(line, TermStyle.GREEN))
        else:
            _print_line(_style(line, TermStyle.GRAY))


def _print_workspace_status(workspace: Workspace) -> None:
    try:
        summary = _format_workspace_summary(workspace)
    except Exception as exc:
        _print_line(_style(f"workspace · status unavailable: {exc}", TermStyle.YELLOW))
        return
    _print_line(_style(f"workspace · {summary}", TermStyle.GRAY))


def _apply_update(update: UIUpdate, *, parser: StreamEventParser, workspace: Workspace) -> None:
    for entry in update.timeline:
        _print_timeline_entry(entry.text, entry.kind)
    if update.todos:
        _print_todos(parser)
    if update.refresh_workspace:
        _print_workspace_status(workspace)


async def _activity_spinner(stop_event: asyncio.Event, mode_holder: list[str]) -> None:
    frame_index = 0
    while not stop_event.is_set():
        mode = mode_holder[0]
        label = ACTIVITY_LABELS.get(mode, "运行中")
        frame = SPINNER_FRAMES[frame_index % len(SPINNER_FRAMES)]
        frame_index += 1
        if _use_color():
            print(
                f"\r{TermStyle.GRAY}{frame} {label}...{TermStyle.RESET}",
                end="",
                file=sys.stderr,
                flush=True,
            )
        else:
            print(f"\r{frame} {label}...", end="", file=sys.stderr, flush=True)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=0.12)
        except TimeoutError:
            continue
    _clear_stderr_line()


async def _stream_agent_turn(
    agent,
    user_text: str,
    config: dict[str, Any],
    parser: StreamEventParser,
    workspace: Workspace,
) -> bool:
    """Run one agent turn. Returns False if interrupted."""
    stop_event = asyncio.Event()
    activity_mode = ["thinking"]
    spinner = asyncio.create_task(_activity_spinner(stop_event, activity_mode))
    inputs = {"messages": [HumanMessage(content=user_text)]}
    watcher = EscInterruptWatcher()
    watcher.start()

    async def _consume() -> None:
        async for chunk in agent.astream(inputs, config=config, stream_mode="values"):
            update = parser.consume(chunk)
            if update.activity_mode:
                activity_mode[0] = update.activity_mode
            _apply_update(update, parser=parser, workspace=workspace)

    consume_task = asyncio.create_task(_consume())
    interrupted = False

    try:
        if watcher.enabled:
            interrupt_task = asyncio.create_task(watcher.wait())
            done, _pending = await asyncio.wait(
                {consume_task, interrupt_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if interrupt_task in done:
                interrupted = True
                consume_task.cancel()
                try:
                    await consume_task
                except asyncio.CancelledError:
                    pass
            else:
                interrupt_task.cancel()
                try:
                    await interrupt_task
                except asyncio.CancelledError:
                    pass
                await consume_task
        else:
            await consume_task
    except asyncio.CancelledError:
        interrupted = True
        consume_task.cancel()
        try:
            await consume_task
        except asyncio.CancelledError:
            pass
        raise
    finally:
        watcher.stop()
        stop_event.set()
        await spinner

    if interrupted:
        update = parser.mark_interrupted()
        _apply_update(update, parser=parser, workspace=workspace)
        for step in update.steps.values():
            if step.status == StepStatus.ERROR and step.result_preview == "interrupted":
                _print_line(format_step_line(step))
        _print_line(_style("已中断，可继续输入新指令", TermStyle.YELLOW))
        _print_workspace_status(workspace)
        return False

    final = parser.flush_assistant_text()
    _apply_update(final, parser=parser, workspace=workspace)
    _print_workspace_status(workspace)
    return True


async def run_plain_cli(
    *,
    workspace_path: str | Path = DEFAULT_WORKSPACE,
) -> int:
    load_env_file(PROJECT_ROOT / ".env")
    workspace = Workspace(Path(workspace_path))
    workspace.ensure_layout()
    agent = create_flex_agent(workspace)
    parser = StreamEventParser()

    thread_id = f"flex_agent_{strftime('%Y%m%d_%H%M%S')}"
    config = {"configurable": {"thread_id": thread_id}}

    _print_banner(workspace)

    while True:
        try:
            prompt = _style("> ", TermStyle.BOLD, TermStyle.CYAN) if _use_color() else "> "
            user_text = input(f"\n{prompt}").strip()
        except KeyboardInterrupt:
            _print_line()
            continue
        except EOFError:
            _print_line("\nbye")
            return 0

        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit", "/exit", "/quit"}:
            _print_line("bye")
            return 0

        handled, output = handle_slash_command(workspace, user_text)
        if handled:
            if output:
                cmd = user_text.strip().lower()
                if cmd == "/status":
                    _print_workspace_status(workspace)
                    _print_line(output)
                elif cmd == "/help":
                    _print_line(output)
                elif cmd == "/clear":
                    _print_timeline_entry(output, "system")
                    _print_workspace_status(workspace)
                else:
                    _print_timeline_entry(output, "system")
            continue

        try:
            parser.note_user_message(user_text, emit=False)
            await _stream_agent_turn(agent, user_text, config, parser, workspace)
        except KeyboardInterrupt:
            _clear_stderr_line()
            update = parser.mark_interrupted()
            _apply_update(update, parser=parser, workspace=workspace)
            _print_line(_style("\n已中断，可继续输入新指令", TermStyle.YELLOW))
            _print_workspace_status(workspace)
        except Exception as exc:
            update = parser.mark_error(exc)
            _apply_update(update, parser=parser, workspace=workspace)
            for step in update.steps.values():
                if step.status == StepStatus.ERROR:
                    _print_line(format_step_line(step))

    return 0
