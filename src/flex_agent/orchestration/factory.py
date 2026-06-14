from __future__ import annotations

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from langgraph.checkpoint.memory import MemorySaver

from flex_agent.config import build_llm, load_model_config
from flex_agent.orchestration.prompt import ORCHESTRATOR_PROMPT
from flex_agent.orchestration.subagents import build_subagents
from flex_agent.orchestration.tools import CodingToolContext, build_coding_tools, create_coding_tool_context
from flex_agent.workspace import Workspace


def build_backend(workspace: Workspace) -> CompositeBackend:
    root = workspace.root.resolve()
    return CompositeBackend(
        default=FilesystemBackend(root_dir=root, virtual_mode=True),
        routes={"/agent/": StateBackend()},
    )


def create_flex_agent(workspace: Workspace, *, tool_ctx: CodingToolContext | None = None):
    ctx = tool_ctx or create_coding_tool_context(workspace)
    model_cfg = load_model_config()
    model = build_llm(
        model_cfg.pro_model,
        timeout=model_cfg.timeout,
        max_retries=model_cfg.max_retries,
        seed=model_cfg.seed,
    )
    workspace.ensure_layout()
    return create_deep_agent(
        model=model,
        tools=build_coding_tools(ctx),
        system_prompt=ORCHESTRATOR_PROMPT,
        subagents=build_subagents(ctx.prompt_ctx),
        backend=build_backend(workspace),
        checkpointer=MemorySaver(),
        name="flex-agent-orchestrator",
    )
