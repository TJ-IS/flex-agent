"""Semantic alignment helpers and per-text metric rows."""

from __future__ import annotations

from typing import Any

from flex_agent.eval.core import EvalMetrics, normalize_dimension

_MIN_SUBSTRING_LEN = 2
_MIN_CHAR_OVERLAP = 0.34


def _bigrams(text: str) -> set[str]:
    if len(text) < 2:
        return set()
    return {text[index : index + 2] for index in range(len(text) - 1)}


def _char_overlap_ratio(left: str, right: str) -> float:
    left_chars = set(left)
    right_chars = set(right)
    if not left_chars or not right_chars:
        return 0.0
    return len(left_chars & right_chars) / min(len(left_chars), len(right_chars))


def _semantic_proximity_score(agent_dim: str, human_dim: str) -> int:
    """Score semantic closeness; higher means stronger match. Zero means no match."""
    canonical = normalize_dimension(agent_dim)
    if canonical == human_dim:
        return 100 + len(human_dim)

    if len(human_dim) >= _MIN_SUBSTRING_LEN and human_dim in agent_dim:
        return 90 + len(human_dim)
    if len(human_dim) >= _MIN_SUBSTRING_LEN and human_dim in canonical:
        return 85 + len(human_dim)
    if len(canonical) >= _MIN_SUBSTRING_LEN and canonical in human_dim:
        return 80 + len(canonical)
    if len(agent_dim) >= _MIN_SUBSTRING_LEN and agent_dim in human_dim:
        return 75 + len(agent_dim)

    if _bigrams(agent_dim) & _bigrams(human_dim):
        overlap = _char_overlap_ratio(agent_dim, human_dim)
        if overlap >= _MIN_CHAR_OVERLAP:
            return 50 + int(overlap * 20) + min(len(human_dim), len(agent_dim))

    if _bigrams(canonical) & _bigrams(human_dim):
        overlap = _char_overlap_ratio(canonical, human_dim)
        if overlap >= _MIN_CHAR_OVERLAP:
            return 40 + int(overlap * 20) + min(len(human_dim), len(canonical))

    return 0


def _heuristic_human_match(
    agent_dim: str,
    human_dims: set[str],
) -> str | None:
    """Match agent dimension to human via normalize, containment, and loose semantic proximity."""
    best_score = 0
    best_human: str | None = None
    for human_dim in human_dims:
        score = _semantic_proximity_score(agent_dim, human_dim)
        if score > best_score:
            best_score = score
            best_human = human_dim
    return best_human


def prefetch_semantic_alignment(
    agent_dims: set[str],
    human_dims: set[str],
) -> dict[str, str | None]:
    """Match agent dimensions to human via heuristic semantic proximity."""
    return apply_heuristic_semantic_alignment(agent_dims, human_dims, {})


def apply_heuristic_semantic_alignment(
    agent_dims: set[str],
    human_dims: set[str],
    base: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    """Fill unmatched agent dimensions using loose semantic heuristics."""
    merged: dict[str, str | None] = {agent: None for agent in agent_dims}
    if base:
        merged.update(base)

    for agent_dim in sorted(agent_dims):
        if merged.get(agent_dim):
            continue
        merged[agent_dim] = _heuristic_human_match(agent_dim, human_dims)
    return merged


def merge_semantic_alignments(
    base: dict[str, str | None],
    override: dict[str, str | None],
) -> dict[str, str | None]:
    """Merge alignments; keep base matches, fill gaps from override without reusing human dims."""
    merged = dict(base)
    for agent_dim, human_dim in override.items():
        if merged.get(agent_dim):
            continue
        if not human_dim:
            merged[agent_dim] = None
            continue
        merged[agent_dim] = human_dim
    return merged


def build_semantic_row(
    text_id: int,
    human_dims: set[str],
    agent_dims: set[str],
    alignment: dict[str, str | None],
    *,
    status: str = "complete",
    error: str | None = None,
) -> dict[str, Any]:
    """Build a consistent semantic result row from an alignment map."""
    matched_agent = {agent for agent, human in alignment.items() if human}
    matched_human = {human for human in alignment.values() if human}
    llm_only = agent_dims - matched_agent
    human_only = human_dims - matched_human
    nums_both = len(matched_agent)
    nums_llm_only = len(llm_only)
    nums_human_only = len(human_only)
    union_count = nums_both + nums_llm_only + nums_human_only

    metrics = EvalMetrics(
        consistency=nums_both / union_count if union_count else 0.0,
        precision=nums_both / (nums_both + nums_llm_only) if (nums_both + nums_llm_only) else 0.0,
        recall=nums_both / (nums_both + nums_human_only) if (nums_both + nums_human_only) else 0.0,
        n_human=nums_both + nums_human_only,
        n_agent=nums_both + nums_llm_only,
        n_intersection=nums_both,
        n_union=union_count,
    )
    row: dict[str, Any] = {
        "text_id": text_id,
        "human_items": sorted(human_dims),
        "agent_items": sorted(agent_dims),
        "both": sorted(matched_agent),
        "llm_only": sorted(llm_only),
        "human_only": sorted(human_only),
        "nums_both": nums_both,
        "nums_llm_only": nums_llm_only,
        "nums_human_only": nums_human_only,
        "alignment": alignment,
        "status": status,
        **metrics.as_dict(),
    }
    if error:
        row["error"] = error
    return row
