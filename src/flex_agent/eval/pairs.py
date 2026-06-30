"""Load aligned human-vs-agent coding pairs for open coding evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flex_agent.eval.core import (
    load_human_benchmark_by_content,
    load_human_records_by_content,
    normalize_content_key,
)
from flex_agent.workspace import Workspace


@dataclass(frozen=True)
class EvalPair:
    text_id: int
    content: str
    human_items: set[str]
    human_record: dict[str, Any]
    agent_items_raw: list[dict[str, Any]]


def load_eval_pairs(
    workspace: Workspace,
    *,
    benchmark_path: Path | None = None,
) -> tuple[list[EvalPair], int]:
    """Scan coding/*.json and human benchmark; return aligned pairs and agent-only count."""
    benchmark = benchmark_path or workspace.human_benchmark_path
    human_by_content = load_human_benchmark_by_content(benchmark)
    human_records_by_content = load_human_records_by_content(benchmark)

    pairs: list[EvalPair] = []
    agent_only = 0

    for text_id in workspace.list_coded_ids():
        coding = workspace.load_coding(text_id)
        if coding is None:
            continue
        content = coding.content.strip()
        normalized = normalize_content_key(content)
        if normalized not in human_by_content:
            agent_only += 1
            continue
        pairs.append(
            EvalPair(
                text_id=text_id,
                content=content,
                human_items=human_by_content[normalized],
                human_record=human_records_by_content.get(normalized, {}),
                agent_items_raw=[item.model_dump() for item in coding.items],
            )
        )

    pairs.sort(key=lambda pair: pair.text_id)
    return pairs, agent_only
