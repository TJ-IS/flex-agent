from __future__ import annotations

from typing import Any


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def format_open_report(
    *,
    item_keyword: dict[str, Any] | None,
    item_semantic: dict[str, Any] | None,
    input_path: str,
    predicted_count: int,
) -> str:
    sep = "=" * 72
    lines = [
        sep,
        "Direct Inference Open Coding 质量评估",
        "指标: JMIS Consistency / Precision / Recall",
        f"输入: {input_path}  Direct 预测文本: {predicted_count}",
        sep,
    ]
    if item_keyword is not None:
        lines.extend(_format_section("一、条目层级 — 维度名匹配", item_keyword))
        lines.append("")
    if item_semantic is not None:
        lines.extend(_format_section("二、条目层级 — LLM 语义对齐", item_semantic))
        lines.append("")
    if item_keyword is None and item_semantic is None:
        lines.append("未生成任何评测结果。")
    lines.append(sep)
    return "\n".join(lines)


def format_axial_report(
    *,
    item_keyword: dict[str, Any] | None,
    item_semantic: dict[str, Any] | None,
    input_path: str,
    predicted_count: int,
    human_category_count: int,
    agent_category_count: int,
) -> str:
    sep = "=" * 72
    lines = [
        sep,
        "Direct Inference Axial Coding 质量评估",
        "指标: JMIS Consistency / Precision / Recall",
        (
            "评测粒度: workspace "
            f"(direct category {agent_category_count} 类 vs human {human_category_count} 类，严格一对一)"
        ),
        f"输入: {input_path}  Direct 预测文本: {predicted_count}",
        sep,
    ]
    if item_keyword is not None:
        lines.extend(_format_section("一、维度层级 — category 名匹配", item_keyword))
        lines.append("")
    if item_semantic is not None:
        lines.extend(_format_section("二、维度层级 — LLM 语义对齐", item_semantic))
        lines.append("")
    if item_keyword is None and item_semantic is None:
        lines.append("未生成任何评测结果。")
    lines.append(sep)
    return "\n".join(lines)


def _format_section(title: str, item_result: dict[str, Any]) -> list[str]:
    macro = item_result["macro"]
    lines = [
        title,
        "-" * 60,
        f"共同评估文本数: {item_result['common_texts']}",
        "",
        f"{'指标':<14} {'Macro-Avg':>10}",
        f"Consistency    {pct(macro['consistency']):>10}",
        f"Precision      {pct(macro['precision']):>10}",
        f"Recall         {pct(macro['recall']):>10}",
        "",
        (
            f"计数: Human={macro['n_human']} Agent={macro['n_agent']} "
            f"∩={macro['n_intersection']} ∪={macro['n_union']}"
        ),
    ]
    if "nums_both" in item_result:
        lines.append(
            f"三分类: both={item_result['nums_both']} "
            f"llm_only={item_result['nums_llm_only']} human_only={item_result['nums_human_only']}"
        )
    return lines
