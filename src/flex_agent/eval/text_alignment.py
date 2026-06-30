"""LLM semantic alignment for human-vs-agent open coding item evaluation."""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, create_model

from flex_agent.eval.async_utils import run_async
from flex_agent.eval.core import normalize_dimension
from flex_agent.eval.prompts import text_alignment_prompt
from flex_agent.i18n import Language, get_bundle, get_language, resolve_language
from flex_agent.llm.structured_output import ainvoke_structured

_DEFAULT_SCHEMA_DESCRIPTIONS = get_bundle("zh").llm.schema_descriptions


class SemanticMatch(BaseModel):
    agent_dimension: str
    matched_human_dimensions: list[str] = Field(
        default_factory=list,
        description=_DEFAULT_SCHEMA_DESCRIPTIONS["semantic_match_matched_human_dimensions"],
    )
    thought: str = Field(default="", description=_DEFAULT_SCHEMA_DESCRIPTIONS["semantic_match_thought"])


class TextSemanticAlignment(BaseModel):
    text_id: str
    reasoning_trace: str = Field(
        default="",
        description=_DEFAULT_SCHEMA_DESCRIPTIONS["semantic_text_reasoning_trace"],
    )
    matches: list[SemanticMatch] = Field(default_factory=list)


class BatchSemanticAlignment(BaseModel):
    texts: list[TextSemanticAlignment] = Field(default_factory=list)


def get_batch_semantic_alignment_model(language: str | None = None) -> type[BaseModel]:
    active_language = resolve_language(language) if language is not None else get_language()
    return _get_batch_semantic_alignment_model(active_language)


@lru_cache(maxsize=2)
def _get_batch_semantic_alignment_model(active_language: Language) -> type[BaseModel]:
    descriptions = get_bundle(active_language).llm.schema_descriptions
    suffix = "Zh" if active_language == "zh" else "En"
    semantic_match = create_model(
        f"SemanticMatch{suffix}",
        agent_dimension=(str, ...),
        matched_human_dimensions=(
            list[str],
            Field(
                default_factory=list,
                description=descriptions["semantic_match_matched_human_dimensions"],
            ),
        ),
        thought=(str, Field(default="", description=descriptions["semantic_match_thought"])),
    )
    text_alignment = create_model(
        f"TextSemanticAlignment{suffix}",
        text_id=(str, ...),
        reasoning_trace=(
            str,
            Field(default="", description=descriptions["semantic_text_reasoning_trace"]),
        ),
        matches=(list[semantic_match], Field(default_factory=list)),  # type: ignore[valid-type]
    )
    return create_model(
        f"BatchSemanticAlignment{suffix}",
        texts=(list[text_alignment], Field(default_factory=list)),  # type: ignore[valid-type]
    )


def _human_items_for_prompt(record: dict[str, Any], fallback_items: set[str]) -> list[dict[str, Any]]:
    if isinstance(record.get("human_items"), list):
        return [
            {
                "dimension": normalize_dimension(str(item.get("dimension", ""))),
                "evidences": item.get("evidences", []),
            }
            for item in record["human_items"]
            if item.get("dimension")
        ]
    return [
        {
            "dimension": normalize_dimension(dim),
            "evidences": record.get("human_spans", []),
        }
        for dim in fallback_items
    ]


def _agent_items_for_prompt(agent_items_raw: list[dict]) -> list[dict[str, Any]]:
    dims: dict[str, dict[str, Any]] = {}
    for item in agent_items_raw:
        label_dims: list[str] = []
        normalized = str(item.get("normalized_label") or "").strip()
        if normalized:
            dim = normalize_dimension(re.split(r"[:：]", normalized, maxsplit=1)[0].strip())
            if dim:
                label_dims.append(dim)
        if not label_dims:
            labels = str(item.get("labels", ""))
            for raw in labels.replace("；", ";").split(";"):
                if ":" not in raw and "：" not in raw:
                    continue
                dim = normalize_dimension(re.split(r"[:：]", raw, maxsplit=1)[0].strip())
                if dim:
                    label_dims.append(dim)
        if not label_dims:
            dim = normalize_dimension(str(item.get("name") or ""))
            if dim:
                label_dims.append(dim)
        for dim in label_dims:
            if not dim:
                continue
            entry = dims.setdefault(dim, {"dimension": dim, "evidences": [], "reasons": []})
            evidence = item.get("evidence") or item.get("name")
            if evidence and evidence not in entry["evidences"]:
                entry["evidences"].append(evidence)
            reason = item.get("reason")
            if reason and reason not in entry["reasons"]:
                entry["reasons"].append(reason)
    return list(dims.values())


async def abuild_semantic_alignment_for_texts(
    text_batch: list[dict[str, Any]],
    llm: BaseChatModel,
    *,
    language: str | None = None,
) -> dict[int, dict[str, list[str] | None]]:
    if not text_batch:
        return {}
    prompt_rows = []
    for entry in text_batch:
        prompt_rows.append({
            "text_id": str(entry["text_id"]),
            "content": entry["content"],
            "human_items": entry["human_items"],
            "agent_items": entry["agent_items"],
        })
    try:
        prompt = ChatPromptTemplate.from_messages([("human", text_alignment_prompt())])
        schema = get_batch_semantic_alignment_model(language)
        result = await ainvoke_structured(
            llm,
            prompt,
            schema,
            {"texts_json": json.dumps(prompt_rows, ensure_ascii=False)},
            component="eval-semantic",
        )
    except Exception as exc:
        print(get_bundle(language).llm.eval_semantic_warning.format(error=exc), file=sys.stderr)
        return {}

    expected = {str(entry["text_id"]): entry for entry in text_batch}
    validated: dict[int, dict[str, list[str] | None]] = {}
    for text in result.texts:
        if text.text_id not in expected:
            continue
        entry = expected[text.text_id]
        agent_dims = {item["dimension"] for item in entry["agent_items"]}
        human_dims = {item["dimension"] for item in entry["human_items"]}
        matches: dict[str, list[str] | None] = {}
        for match in text.matches:
            agent_dim = normalize_dimension(match.agent_dimension)
            if agent_dim not in agent_dims:
                continue
            human_set = {
                normalize_dimension(h) for h in match.matched_human_dimensions
                if normalize_dimension(h) in human_dims
            }
            matches[agent_dim] = sorted(human_set) if human_set else None
        validated[int(text.text_id)] = matches
    return validated


def build_semantic_alignment_for_texts(
    text_batch: list[dict[str, Any]],
    llm: BaseChatModel,
    *,
    language: str | None = None,
) -> dict[int, dict[str, list[str] | None]]:
    return run_async(
        abuild_semantic_alignment_for_texts(text_batch, llm, language=language)
    )
