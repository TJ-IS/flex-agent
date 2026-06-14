from __future__ import annotations

from typing import Any


def _pct(val: float) -> str:
    return f"{val * 100:.1f}%"


def _format_item_section(title: str, item_result: dict[str, Any]) -> list[str]:
    micro = item_result["micro"]
    macro = item_result["macro"]
    lines = [
        title,
        "-" * 60,
        f"共同评估文本数: {item_result['common_texts']}",
        f"仅人工: {item_result.get('skipped_human_only', 0)}  仅 Agent: {item_result.get('skipped_agent_only', 0)}",
        "",
        f"{'指标':<14} {'Macro-Avg':>10}  {'Micro-Avg':>10}",
        f"Consistency    {_pct(macro['consistency']):>10}  {_pct(micro['consistency']):>10}",
        f"Precision      {_pct(macro['precision']):>10}  {_pct(micro['precision']):>10}",
        f"Recall         {_pct(macro['recall']):>10}  {_pct(micro['recall']):>10}",
        "",
        (
            f"Micro 计数: Human={micro['n_human']} Agent={micro['n_agent']} "
            f"∩={micro['n_intersection']} ∪={micro['n_union']}"
        ),
    ]
    if "nums_both" in item_result:
        lines.append(
            f"三分类: both={item_result['nums_both']} "
            f"llm_only={item_result['nums_llm_only']} human_only={item_result['nums_human_only']}"
        )
    return lines


def format_open_coding_report(
    *,
    item_keyword: dict[str, Any] | None,
    item_semantic: dict[str, Any] | None,
    coded_count: int,
    benchmark_path: str,
) -> str:
    sep = "=" * 72
    lines = [
        sep,
        "flex-agent Open Coding 质量评估",
        "指标: JMIS Consistency / Precision / Recall",
        f"已编码文本: {coded_count}  人工 benchmark: {benchmark_path}",
        sep,
    ]

    if item_keyword is not None:
        lines.extend(_format_item_section("一、条目层级 — 维度名匹配", item_keyword))
        lines.append("")

    if item_semantic is not None:
        lines.extend(_format_item_section("二、条目层级 — 逐文本证据对齐 (LLM)", item_semantic))
        lines.append("")

    if item_keyword is None and item_semantic is None:
        lines.append("未生成任何评测结果。")

    lines.append(sep)
    return "\n".join(lines)
