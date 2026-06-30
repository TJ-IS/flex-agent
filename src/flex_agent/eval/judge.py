"""Per-text semantic judging for open coding evaluation."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from flex_agent.eval.core import normalize_dimension
from flex_agent.eval.pairs import EvalPair
from flex_agent.eval.semantic_metrics import (
    build_semantic_row,
    prefetch_semantic_alignment,
)
from flex_agent.eval.text_alignment import (
    _agent_items_for_prompt,
    _human_items_for_prompt,
    build_semantic_alignment_for_texts,
)


def _agent_dims_from_raw(agent_items_raw: list[dict[str, Any]]) -> set[str]:
    return {item["dimension"] for item in _agent_items_for_prompt(agent_items_raw)}


def _human_dims_from_pair(pair: EvalPair) -> set[str]:
    return {normalize_dimension(dim) for dim in pair.human_items}


def _counts_to_row(
    text_id: int,
    human_dims: set[str],
    agent_dims: set[str],
    matched_agent: set[str],
    matched_human: set[str],
) -> dict[str, Any]:
    llm_only = agent_dims - matched_agent
    human_only = human_dims - matched_human
    union_count = len(matched_agent) + len(llm_only) + len(human_only)
    consistency = len(matched_agent) / union_count if union_count else 0.0
    precision = (
        len(matched_agent) / (len(matched_agent) + len(llm_only))
        if (len(matched_agent) + len(llm_only))
        else 0.0
    )
    recall = (
        len(matched_agent) / (len(matched_agent) + len(human_only))
        if (len(matched_agent) + len(human_only))
        else 0.0
    )
    return {
        "text_id": text_id,
        "human_items": sorted(human_dims),
        "agent_items": sorted(agent_dims),
        "both": sorted(matched_agent),
        "llm_only": sorted(llm_only),
        "human_only": sorted(human_only),
        "nums_both": len(matched_agent),
        "nums_llm_only": len(llm_only),
        "nums_human_only": len(human_only),
        "consistency": round(consistency, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "status": "complete",
    }


def judge_semantic(pair: EvalPair, llm: BaseChatModel) -> dict[str, Any]:
    """Judge one text using heuristic prefetch + LLM semantic alignment (one-to-many)."""
    human_dims = _human_dims_from_pair(pair)
    agent_dims = _agent_dims_from_raw(pair.agent_items_raw)
    heuristic = prefetch_semantic_alignment(agent_dims, human_dims)

    alignment: dict[str, list[str] | None] = {
        agent: ([human] if human else None) for agent, human in heuristic.items()
    }

    pending = [agent for agent, humans in alignment.items() if not humans]
    if pending:
        entry = {
            "text_id": pair.text_id,
            "content": pair.content,
            "human_items": _human_items_for_prompt(pair.human_record, pair.human_items),
            "agent_items": _agent_items_for_prompt(pair.agent_items_raw),
        }
        try:
            llm_alignment = build_semantic_alignment_for_texts([entry], llm)
            override = llm_alignment.get(pair.text_id, {})
            for agent, humans in override.items():
                if humans:
                    alignment[agent] = humans
                elif agent in alignment:
                    alignment[agent] = alignment[agent] or None
        except Exception as exc:
            if any(alignment.values()):
                return build_semantic_row(pair.text_id, human_dims, agent_dims, alignment)
            return build_semantic_row(
                pair.text_id,
                human_dims,
                agent_dims,
                alignment,
                status="failed",
                error=repr(exc),
            )

    return build_semantic_row(pair.text_id, human_dims, agent_dims, alignment)


def build_eval_text_payload(
    pair: EvalPair,
    *,
    semantic: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"text_id": pair.text_id}
    if semantic is not None:
        payload["semantic"] = semantic
    return payload
