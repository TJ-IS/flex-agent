"""Load workspace-level context for axial coding evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flex_agent.eval.axial_core import (
    agent_axial_dims_for_coding,
    agent_dimensions_detail,
    build_codebook_item_index,
    codebook_axial_dims,
    human_categories_from_record,
    human_category_taxonomy,
)
from flex_agent.eval.core import normalize_content_key
from flex_agent.eval.pairs import load_eval_pairs
from flex_agent.models import DimensionDetail
from flex_agent.workspace import Workspace


@dataclass(frozen=True)
class AxialGlobalEvalContext:
    agent_axial_dims: set[str]
    human_categories: set[str]
    agent_dimensions_detail: list[dict[str, Any]]


def load_axial_global_eval(workspace: Workspace) -> AxialGlobalEvalContext:
    """Build workspace-level axial eval: full codebook vs human category taxonomy."""
    dimensions = workspace.load_dimensions()
    agent_dims = codebook_axial_dims(dimensions)
    return AxialGlobalEvalContext(
        agent_axial_dims=agent_dims,
        human_categories=human_category_taxonomy(),
        agent_dimensions_detail=agent_dimensions_detail(dimensions, agent_dims),
    )


# --- legacy per-text helpers (used by unit tests for codebook lookup) ---


@dataclass(frozen=True)
class AxialEvalPair:
    text_id: int
    content: str
    human_categories: set[str]
    agent_axial_dims: set[str]
    human_record: dict[str, Any]
    agent_items_raw: list[dict[str, Any]]
    agent_dimensions_detail: list[dict[str, Any]]


def load_axial_eval_pairs(
    workspace: Workspace,
    *,
    benchmark_path: Path | None = None,
) -> tuple[list[AxialEvalPair], int]:
    """Build per-text axial pairs (diagnostic only; runner uses global eval)."""
    open_pairs, agent_only = load_eval_pairs(workspace, benchmark_path=benchmark_path)
    dimensions = workspace.load_dimensions()
    if not dimensions:
        return [], agent_only

    item_index = build_codebook_item_index(dimensions)
    pairs: list[AxialEvalPair] = []

    for open_pair in open_pairs:
        coding = workspace.load_coding(open_pair.text_id)
        if coding is None:
            continue
        human_categories = human_categories_from_record(open_pair.human_record)
        agent_axial_dims = agent_axial_dims_for_coding(coding, item_index)
        pairs.append(
            AxialEvalPair(
                text_id=open_pair.text_id,
                content=open_pair.content,
                human_categories=human_categories,
                agent_axial_dims=agent_axial_dims,
                human_record=open_pair.human_record,
                agent_items_raw=open_pair.agent_items_raw,
                agent_dimensions_detail=agent_dimensions_detail(dimensions, agent_axial_dims),
            )
        )

    pairs.sort(key=lambda pair: pair.text_id)
    return pairs, agent_only
