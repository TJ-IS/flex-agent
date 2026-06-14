from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any, Literal

from flex_agent.config import build_llm, load_model_config
from flex_agent.eval.aggregate import aggregate_eval_results
from flex_agent.eval.async_utils import run_async
from flex_agent.eval.batch_semantic import batch_semantic_judge
from flex_agent.eval.core import ALL_HUMAN_DIMENSIONS, extract_agent_items
from flex_agent.eval.judge import judge_keyword
from flex_agent.eval.pairs import load_eval_pairs
from flex_agent.eval.report import format_open_coding_report
from flex_agent.eval.semantic import apply_semantic_alignment, build_dimension_name_alignment
from flex_agent.workspace import Workspace

ProgressCallback = Callable[[str], None]


def _emit_progress(on_progress: ProgressCallback | None, message: str) -> None:
    if on_progress is not None:
        on_progress(message)


def _default_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)

def aggregate_workspace_eval(
    workspace: Workspace,
    *,
    mode: Literal["keyword", "semantic", "both"] = "both",
    save_json: bool = True,
    on_progress: ProgressCallback | None = _default_progress,
) -> str:
    """Recompute CPR from eval/open/{id}.json on disk (no LLM)."""
    if not workspace.eval_open_dir.exists():
        raise RuntimeError("尚无评测结果。请先运行 /eval:open。")

    agg = aggregate_eval_results(workspace.eval_open_dir)
    item_keyword = agg.get("item_level_keyword")
    item_semantic = agg.get("item_level_semantic")

    if mode == "keyword":
        item_semantic = None
    elif mode == "semantic":
        item_keyword = None

    summary = workspace.load_eval_summary("open") or {}
    coded_count = summary.get("coded_count", len(workspace.list_coded_ids()))
    benchmark_path = summary.get("benchmark_path", str(workspace.human_benchmark_path))

    report = format_open_coding_report(
        item_keyword=item_keyword,
        item_semantic=item_semantic,
        coded_count=coded_count,
        benchmark_path=benchmark_path,
    )

    if save_json:
        payload: dict[str, Any] = {
            "mode": mode,
            "align": summary.get("align", False),
            "status": "complete",
            "coded_count": coded_count,
            "benchmark_path": benchmark_path,
        }
        if item_keyword is not None:
            payload["item_level_keyword"] = item_keyword
        if item_semantic is not None:
            payload["item_level_semantic"] = item_semantic

        output_path = workspace.save_eval_summary(
            "open",
            payload=payload,
            report=report,
            meta={
                "mode": mode,
                "align": summary.get("align", False),
                "status": "complete",
                "coded_count": coded_count,
                "benchmark_path": benchmark_path,
                "keyword_complete": agg["keyword_complete"],
                "semantic_complete": agg["semantic_complete"],
            },
        )
        rel_summary = output_path.relative_to(workspace.root).as_posix()
        rel_report = workspace.eval_report_path("open").relative_to(workspace.root).as_posix()
        per_text_count = len(workspace.list_eval_text_ids("open"))
        _emit_progress(on_progress, f"[eval] 聚合完成: {rel_summary}")
        report += f"\n汇总已保存: {rel_summary}"
        report += f"\n报告文本已保存: {rel_report}"
        report += f"\n已聚合 {per_text_count} 条 per-text 结果"

    return report


def evaluate_workspace(
    workspace: Workspace,
    *,
    mode: Literal["keyword", "semantic", "both", "metrics"] = "both",
    align: bool = False,
    concurrency_limit: int = 10,
    resume: bool = True,
    save_json: bool = True,
    on_progress: ProgressCallback | None = _default_progress,
) -> str:
    """Evaluate workspace open coding: align → judge per-text → aggregate CPR."""
    if mode == "metrics":
        return aggregate_workspace_eval(
            workspace,
            mode="both",
            save_json=save_json,
            on_progress=on_progress,
        )

    if not workspace.benchmark_ready():
        raise RuntimeError(
            "人工 benchmark 未就绪。请确认 flex-agent/data/ 下种子文件存在，并重新启动 CLI。"
        )

    coded_count = len(workspace.list_coded_ids())
    if coded_count == 0:
        raise RuntimeError("尚无已编码文本。请先运行 Bob 编码（batch_bob_code）后再评测。")

    _emit_progress(on_progress, f"[eval] 开始评测 mode={mode}，已编码 {coded_count} 条文本")

    benchmark_path = workspace.human_benchmark_path
    _emit_progress(on_progress, f"[eval] 加载人工 benchmark: {benchmark_path}")
    pairs, agent_only = load_eval_pairs(workspace, benchmark_path=benchmark_path)
    _emit_progress(
        on_progress,
        (
            f"[eval] 对齐 {len(pairs)} 对 "
            f"(agent={coded_count}, human={len(pairs)}, agent_only={agent_only})"
        ),
    )

    if not pairs:
        raise RuntimeError("无可用对齐文本。请确认 coding/ 与 private/ benchmark 正文一致。")

    agent_items = extract_agent_items([
        {"id": pair.text_id, "items": pair.agent_items_raw} for pair in pairs
    ])

    if align:
        all_agent_dims = sorted({dim for items in agent_items.values() for dim in items})
        unmatched = [d for d in all_agent_dims if d not in ALL_HUMAN_DIMENSIONS]
        if unmatched:
            _emit_progress(
                on_progress,
                f"[eval] LLM 维度名映射: {len(unmatched)} 个未匹配维度",
            )
            model_cfg = load_model_config()
            llm = build_llm(
                model_cfg.default_model,
                timeout=120.0,
                max_retries=model_cfg.max_retries,
                seed=model_cfg.seed,
            )
            alignment = build_dimension_name_alignment(unmatched, ALL_HUMAN_DIMENSIONS, llm)
            agent_items = apply_semantic_alignment(agent_items, alignment)

    workspace.eval_open_dir.mkdir(parents=True, exist_ok=True)

    if mode in {"keyword", "both"}:
        _emit_progress(on_progress, "[eval] keyword 逐条评测...")
        for pair in pairs:
            keyword = judge_keyword(pair, agent_items=agent_items.get(pair.text_id))
            existing = workspace.load_eval_text("open", pair.text_id) or {"text_id": pair.text_id}
            existing["keyword"] = keyword
            workspace.save_eval_text("open", pair.text_id, existing)
        _emit_progress(
            on_progress,
            f"[eval] keyword 全量完成 → 写入 eval/open/*.json ({len(pairs)} 条)",
        )
        agg = aggregate_eval_results(workspace.eval_open_dir)
        if agg.get("item_level_keyword"):
            micro = agg["item_level_keyword"]["micro"]
            _emit_progress(
                on_progress,
                (
                    f"[eval] keyword 聚合: C={micro['consistency']:.1%} "
                    f"P={micro['precision']:.1%} R={micro['recall']:.1%}"
                ),
            )

    if mode in {"semantic", "both"}:
        model_cfg = load_model_config()
        align_llm = build_llm(
            model_cfg.default_model,
            timeout=180.0,
            max_retries=model_cfg.max_retries,
            seed=model_cfg.seed,
        )
        run_async(
            batch_semantic_judge(
                workspace,
                pairs,
                align_llm,
                resume=resume,
                concurrency_limit=concurrency_limit,
                on_progress=lambda msg: _emit_progress(on_progress, msg),
            )
        )
        agg = aggregate_eval_results(workspace.eval_open_dir)
        if agg.get("item_level_semantic"):
            micro = agg["item_level_semantic"]["micro"]
            _emit_progress(
                on_progress,
                (
                    f"[eval] semantic 聚合: C={micro['consistency']:.1%} "
                    f"P={micro['precision']:.1%} R={micro['recall']:.1%} "
                    f"(complete {agg['semantic_complete']}/{len(pairs)})"
                ),
            )

    _emit_progress(on_progress, "[eval] 生成报告...")
    agg = aggregate_eval_results(workspace.eval_open_dir)
    item_keyword = agg.get("item_level_keyword") if mode in {"keyword", "both"} else None
    item_semantic = agg.get("item_level_semantic") if mode in {"semantic", "both"} else None

    report = format_open_coding_report(
        item_keyword=item_keyword,
        item_semantic=item_semantic,
        coded_count=coded_count,
        benchmark_path=str(benchmark_path),
    )

    if save_json:
        payload: dict[str, Any] = {
            "mode": mode,
            "align": align,
            "status": "complete",
            "coded_count": coded_count,
            "benchmark_path": str(benchmark_path),
        }
        if item_keyword is not None:
            payload["item_level_keyword"] = item_keyword
        if item_semantic is not None:
            payload["item_level_semantic"] = item_semantic

        output_path = workspace.save_eval_summary(
            "open",
            payload=payload,
            report=report,
            meta={
                "mode": mode,
                "align": align,
                "status": "complete",
                "coded_count": coded_count,
                "benchmark_path": str(benchmark_path),
                "keyword_complete": agg["keyword_complete"],
                "semantic_complete": agg["semantic_complete"],
            },
        )
        rel_summary = output_path.relative_to(workspace.root).as_posix()
        rel_report = workspace.eval_report_path("open").relative_to(workspace.root).as_posix()
        per_text_count = len(workspace.list_eval_text_ids("open"))
        _emit_progress(on_progress, f"[eval] 保存结果: {rel_summary}")
        report += f"\n汇总已保存: {rel_summary}"
        report += f"\n报告文本已保存: {rel_report}"
        report += f"\n已写入 {per_text_count} 条 per-text 结果"

    _emit_progress(on_progress, "[eval] 评测完成")
    return report
