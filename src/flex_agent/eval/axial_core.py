"""Shared utilities for axial (codebook) coding evaluation."""

from __future__ import annotations

import re
from typing import Any

from flex_agent.eval.core import normalize_dimension
from flex_agent.models import DimensionDetail, FinishedTextItem

HUMAN_CATEGORIES = (
    "Installation",
    "facility service",
    "interactive service",
    "patronage intent",
    "perceived value",
    "playfulness",
    "sensory appeal",
)

_CATEGORY_CANONICAL = {category.lower(): category for category in HUMAN_CATEGORIES}

# Keyword aliases: human category -> agent axial dimension names / keywords
CATEGORY_KEYWORD_ALIASES: dict[str, set[str]] = {
    "Installation": {"环境价值", "便利性", "环境", "空间", "位置", "场地"},
    "facility service": {"设备体验", "设备", "设施", "流畅", "可靠", "维护", "舒适"},
    "interactive service": {"服务体验", "服务", "态度", "专业", "增值"},
    "patronage intent": {"整体满意度", "满意度", "推荐", "二刷", "再访", "惠顾"},
    "perceived value": {"价格感知", "价格", "价值", "情绪价值", "时间感知", "社交"},
    "playfulness": {"互动体验", "娱乐价值", "内容价值", "趣味", "游戏", "玩法", "创新"},
    "sensory appeal": {"沉浸体验", "沉浸", "感官", "画面", "声音", "视觉", "听觉"},
}


def normalize_category(category: str) -> str:
    """Normalize a human benchmark category to its canonical form."""
    cleaned = str(category or "").strip()
    if not cleaned:
        return cleaned
    return _CATEGORY_CANONICAL.get(cleaned.lower(), cleaned)


def human_categories_from_record(record: dict[str, Any]) -> set[str]:
    """Extract active human categories (value != 0) from a benchmark record."""
    categories: set[str] = set()
    if isinstance(record.get("human_items"), list):
        for item in record["human_items"]:
            value = item.get("value", 1)
            if value == 0:
                continue
            category = normalize_category(str(item.get("category", "")).strip())
            if category:
                categories.add(category)
        if categories:
            return categories

    for code_val in record.get("codes", {}).values():
        value = code_val.get("value", 0)
        if value != 0:
            category = normalize_category(str(code_val.get("category", "")).strip())
            if category:
                categories.add(category)
    return categories


def build_codebook_item_index(dimensions: list[DimensionDetail]) -> dict[str, str]:
    """Map normalized open-coding labels to axial dimension names."""
    index: dict[str, str] = {}
    for dimension in dimensions:
        for item in dimension.items:
            label = normalize_dimension(str(item).strip())
            if label and label not in index:
                index[label] = dimension.name
            raw = str(item).strip()
            if raw and raw not in index:
                index[raw] = dimension.name
    return index


def _label_from_coding_item(item: dict[str, Any]) -> str | None:
    normalized = str(item.get("normalized_label") or "").strip()
    if normalized:
        return normalize_dimension(re.split(r"[:：]", normalized, maxsplit=1)[0].strip())
    labels = str(item.get("labels") or "")
    for raw in labels.replace("；", ";").split(";"):
        if ":" not in raw and "：" not in raw:
            continue
        dim = normalize_dimension(re.split(r"[:：]", raw, maxsplit=1)[0].strip())
        if dim:
            return dim
    name = str(item.get("name") or "").strip()
    return normalize_dimension(name) if name else None


def agent_axial_dims_for_coding(
    coding: FinishedTextItem,
    item_index: dict[str, str],
) -> set[str]:
    """Resolve axial dimension names covering this text's open-coding items."""
    dims: set[str] = set()
    for item in coding.items:
        label = _label_from_coding_item(item.model_dump())
        if not label:
            continue
        dimension_name = item_index.get(label)
        if dimension_name:
            dims.add(dimension_name)
    return dims


def codebook_axial_dims(dimensions: list[DimensionDetail]) -> set[str]:
    """All axial dimension names from the codebook."""
    return {dimension.name for dimension in dimensions if dimension.name}


def human_category_taxonomy() -> set[str]:
    """Fixed human benchmark category taxonomy for workspace-level axial eval."""
    return set(HUMAN_CATEGORIES)


def agent_dimensions_detail(
    dimensions: list[DimensionDetail],
    active_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Serialize codebook dimensions for semantic prompts."""
    names = active_names if active_names is not None else codebook_axial_dims(dimensions)
    detail: list[dict[str, Any]] = []
    for dimension in dimensions:
        if dimension.name not in names:
            continue
        detail.append({
            "name": dimension.name,
            "definition": dimension.definition or "",
            "items": list(dimension.items[:12]),
        })
    return detail


def keyword_match_score(agent_dim: str, human_category: str) -> int:
    """Score keyword fit; higher is a stronger one-to-one candidate."""
    category = normalize_category(human_category)
    if agent_dim == category:
        return 1000 + len(agent_dim)
    aliases = CATEGORY_KEYWORD_ALIASES.get(category, set())
    if agent_dim in aliases:
        return 900 + len(agent_dim)
    best = 0
    for alias in aliases:
        if len(alias) >= 2 and alias in agent_dim:
            best = max(best, 500 + len(alias))
        if len(alias) >= 2 and agent_dim in alias:
            best = max(best, 400 + len(agent_dim))
    return best


def keyword_match_agent_to_category(agent_dim: str, human_category: str) -> bool:
    """Return True when agent axial dim keyword-matches a human category."""
    return keyword_match_score(agent_dim, human_category) > 0


def keyword_alignment(
    agent_dims: set[str],
    human_categories: set[str],
) -> tuple[set[str], set[str]]:
    """Greedy one-to-one keyword matching between agent dims and human categories."""
    candidates: list[tuple[int, str, str]] = []
    for agent in agent_dims:
        for category in human_categories:
            score = keyword_match_score(agent, category)
            if score > 0:
                candidates.append((score, agent, normalize_category(category)))
    candidates.sort(key=lambda row: (-row[0], row[1], row[2]))

    matched_agent: set[str] = set()
    matched_human: set[str] = set()
    for _score, agent, category in candidates:
        if agent in matched_agent or category in matched_human:
            continue
        matched_agent.add(agent)
        matched_human.add(category)
    return matched_agent, matched_human


def enforce_one_to_one_alignment(
    alignment: dict[str, str | None],
    *,
    agent_dims: set[str],
    human_categories: set[str],
) -> dict[str, str | None]:
    """Keep at most one agent per human category (strict one-to-one)."""
    normalized_human = {normalize_category(category) for category in human_categories}
    candidates: list[tuple[int, str, str]] = []
    for agent in agent_dims:
        human = alignment.get(agent)
        if not human:
            continue
        category = normalize_category(human)
        if category not in normalized_human:
            continue
        candidates.append((keyword_match_score(agent, category), agent, category))
    candidates.sort(key=lambda row: (-row[0], row[1], row[2]))

    strict: dict[str, str | None] = {agent: None for agent in agent_dims}
    used_human: set[str] = set()
    for _score, agent, category in candidates:
        if category in used_human:
            continue
        strict[agent] = category
        used_human.add(category)
    return strict
