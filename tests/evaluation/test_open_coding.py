from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flex_agent.eval.core import (
    extract_agent_items,
    extract_agent_items_raw,
    load_human_benchmark,
    normalize_dimension,
)
from flex_agent.eval.prompts import dimension_name_alignment_prompt, text_alignment_prompt
from flex_agent.eval.text_alignment import BatchSemanticAlignment, build_semantic_alignment_for_texts
from flex_agent.models import FinishedItemDetail, FinishedTextItem
from flex_agent.workspace import Workspace


class NormalizeDimensionTests(unittest.TestCase):
    def test_alias_normalization(self) -> None:
        self.assertEqual(normalize_dimension("服务态度"), "态度")
        self.assertEqual(normalize_dimension("地理位置"), "位置")
        self.assertEqual(normalize_dimension("性价比"), "价格")
        self.assertEqual(normalize_dimension("坏境"), "环境")

    def test_english_translation(self) -> None:
        self.assertEqual(normalize_dimension("staff_patience"), "专业度")
        self.assertEqual(normalize_dimension("visual_quality"), "画面")
        self.assertEqual(normalize_dimension("revisit_intention"), "二刷意愿")


class LoadHumanBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8")
        records = [
            {"comments": "画面好", "codes": {"4.2": {"dimension": "画面", "value": 1}}},
            {"comments": "态度差", "codes": {"2.1": {"dimension": "态度", "value": -1}}},
        ]
        for record in records:
            self.tmp.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.tmp.close()

    def tearDown(self) -> None:
        Path(self.tmp.name).unlink(missing_ok=True)

    def test_loads_nonzero_codes_only(self) -> None:
        result = load_human_benchmark(Path(self.tmp.name))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1], {"画面"})
        self.assertEqual(result[2], {"态度"})


class ExtractAgentItemsTests(unittest.TestCase):
    def test_collects_dimension_set_dropping_polarity(self) -> None:
        finished = [
            {
                "id": 1,
                "items": [
                    {"normalized_label": "画面", "name": "画面清晰"},
                    {"normalized_label": "态度", "name": "服务好"},
                ],
            }
        ]
        result = extract_agent_items(finished)
        self.assertEqual(result, {1: {"画面", "态度"}})

    def test_legacy_labels_without_polarity_are_collected(self) -> None:
        finished = [
            {
                "id": 2,
                "items": [
                    {"labels": "画面;态度", "name": "x"},
                ],
            }
        ]
        result = extract_agent_items(finished)
        self.assertEqual(result, {2: {"画面", "态度"}})


class EvalPromptTests(unittest.TestCase):
    def test_text_alignment_prompt_has_placeholder_and_one_to_many(self) -> None:
        prompt = text_alignment_prompt()
        self.assertIn("{texts_json}", prompt)
        self.assertNotIn("ReAct", prompt)
        self.assertIn("允许多对一", prompt)
        self.assertIn("一对多", prompt)
        self.assertIn("matched_human_dimensions", prompt)
        self.assertIn("只输出 JSON", prompt)

    def test_dimension_name_alignment_prompt_formats_lists(self) -> None:
        prompt = dimension_name_alignment_prompt(human_list="- 画面", agent_list="- 视觉质量")
        self.assertIn("- 画面", prompt)
        self.assertIn("- 视觉质量", prompt)
        self.assertNotIn("ReAct", prompt)
        self.assertIn("允许多对一", prompt)
        self.assertIn("只输出 JSON", prompt)
        self.assertNotIn("例如", prompt)

    def test_semantic_alignment_schema_uses_list_match_field(self) -> None:
        schema_text = json.dumps(BatchSemanticAlignment.model_json_schema(), ensure_ascii=False)
        self.assertNotIn("ReAct", schema_text)
        self.assertIn("matched_human_dimensions", schema_text)
        self.assertIn("可选的简短判断依据", schema_text)
        self.assertNotIn("\"matched_human_dimension\"", schema_text)


class SemanticAlignmentLLMTests(unittest.TestCase):
    def test_validates_fake_llm_structured_output_one_to_many(self) -> None:
        class FakeChain:
            def invoke(self, payload):
                from flex_agent.eval.text_alignment import (
                    BatchSemanticAlignment,
                    SemanticMatch,
                    TextSemanticAlignment,
                )

                return BatchSemanticAlignment(
                    texts=[
                        TextSemanticAlignment(
                            text_id="1",
                            matches=[
                                SemanticMatch(
                                    agent_dimension="场景真实感",
                                    matched_human_dimensions=["画面", "声音"],
                                ),
                                SemanticMatch(agent_dimension="价格", matched_human_dimensions=[]),
                            ],
                        )
                    ]
                )

        class FakePrompt:
            def __or__(self, other):
                return FakeChain()

        class FakeLLM:
            def with_structured_output(self, schema, method="json_schema"):
                return self

        entries = [
            {
                "text_id": 1,
                "content": "画面和声音都很棒",
                "human_items": [{"dimension": "画面", "evidences": []}, {"dimension": "声音", "evidences": []}],
                "agent_items": [
                    {"dimension": "场景真实感", "evidences": ["画面和声音都很棒"]},
                    {"dimension": "价格", "evidences": ["便宜"]},
                ],
            }
        ]
        with patch(
            "flex_agent.eval.text_alignment.ChatPromptTemplate.from_messages",
            return_value=FakePrompt(),
        ):
            result = build_semantic_alignment_for_texts(entries, FakeLLM())
        self.assertEqual(set(result[1]["场景真实感"]), {"画面", "声音"})
        self.assertIsNone(result[1]["价格"])


class EvaluateWorkspaceMetricsTests(unittest.TestCase):
    def _setup_workspace(self, tmpdir: str) -> Workspace:
        root = Path(tmpdir)
        workspace = Workspace(root)
        workspace.ensure_layout()
        workspace.human_benchmark_path.parent.mkdir(parents=True, exist_ok=True)
        workspace.human_benchmark_path.write_text(
            json.dumps(
                {
                    "comments": "画面很好",
                    "human_items": [{"dimension": "画面", "value": 1, "evidences": []}],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        workspace.corpus_seed_path.write_text(
            json.dumps({"id": 1, "comments": "画面很好"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        workspace.save_coding(
            FinishedTextItem(
                id=1,
                content="画面很好",
                content_with_labels="画面很好",
                items=[FinishedItemDetail(name="画面清晰", normalized_label="画面")],
            )
        )
        return workspace

    def test_evaluate_workspace_metrics_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self._setup_workspace(tmpdir)
            workspace.save_eval_text(
                "open",
                1,
                {
                    "text_id": 1,
                    "semantic": {
                        "text_id": 1,
                        "human_items": ["画面"],
                        "agent_items": ["画面"],
                        "both": ["画面"],
                        "llm_only": [],
                        "human_only": [],
                        "nums_both": 1,
                        "nums_llm_only": 0,
                        "nums_human_only": 0,
                        "consistency": 1.0,
                        "precision": 1.0,
                        "recall": 1.0,
                        "status": "complete",
                        "alignment": {"画面": "画面"},
                    },
                },
            )
            from flex_agent.eval.runner import evaluate_workspace

            report = evaluate_workspace(workspace, mode="metrics", save_json=False, on_progress=None)
            self.assertIn("100.0%", report)

    def test_evaluate_workspace_persists_under_eval_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self._setup_workspace(tmpdir)
            workspace.save_eval_text(
                "open",
                1,
                {
                    "text_id": 1,
                    "semantic": {
                        "text_id": 1,
                        "human_items": ["画面"],
                        "agent_items": ["画面"],
                        "both": ["画面"],
                        "llm_only": [],
                        "human_only": [],
                        "nums_both": 1,
                        "nums_llm_only": 0,
                        "nums_human_only": 0,
                        "consistency": 1.0,
                        "precision": 1.0,
                        "recall": 1.0,
                        "status": "complete",
                        "alignment": {"画面": "画面"},
                    },
                },
            )
            from flex_agent.eval.runner import evaluate_workspace

            report = evaluate_workspace(workspace, mode="metrics", save_json=True, on_progress=None)
            self.assertIn("eval/open/summary.json", report)
            self.assertFalse(any(workspace.exports_dir.glob("eval_open_*.json")))
            self.assertTrue(workspace.eval_summary_path("open").exists())
            self.assertEqual(workspace.list_eval_text_ids("open"), [1])
            self.assertIsNotNone(workspace.load_eval_summary("open"))


class AggregateEvalResultsTests(unittest.TestCase):
    def test_aggregate_from_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            eval_dir = Path(tmpdir)
            eval_dir.joinpath("1.json").write_text(
                json.dumps(
                    {
                        "text_id": 1,
                        "semantic": {
                            "text_id": 1,
                            "human_items": ["画面"],
                            "agent_items": ["画面"],
                            "both": ["画面"],
                            "llm_only": [],
                            "human_only": [],
                            "nums_both": 1,
                            "nums_llm_only": 0,
                            "nums_human_only": 0,
                            "consistency": 1.0,
                            "precision": 1.0,
                            "recall": 1.0,
                            "status": "complete",
                            "alignment": {"画面": "画面"},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            from flex_agent.eval.aggregate import aggregate_eval_results

            agg = aggregate_eval_results(eval_dir)
            self.assertEqual(agg["semantic_complete"], 1)
            self.assertEqual(agg["item_level_semantic"]["macro"]["consistency"], 1.0)
            self.assertNotIn("item_level_keyword", agg)


class JudgeSemanticTests(unittest.TestCase):
    def test_llm_failure_marks_failed_without_crash(self) -> None:
        from flex_agent.eval.judge import judge_semantic
        from flex_agent.eval.pairs import EvalPair

        pair = EvalPair(
            text_id=1,
            content="画面很好",
            human_items={"画面"},
            human_record={"human_items": [{"dimension": "画面", "value": 1}]},
            agent_items_raw=[{"normalized_label": "完全无关", "name": "无关"}],
        )

        class BrokenLLM:
            def with_structured_output(self, schema, method="json_schema"):
                return self

        with patch(
            "flex_agent.eval.judge.build_semantic_alignment_for_texts",
            return_value={},
        ):
            result = judge_semantic(pair, BrokenLLM())
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["nums_both"], 0)

    def test_falls_back_to_heuristic_when_llm_returns_empty(self) -> None:
        from flex_agent.eval.judge import judge_semantic
        from flex_agent.eval.pairs import EvalPair

        pair = EvalPair(
            text_id=1,
            content="很好玩",
            human_items={"趣味性"},
            human_record={"human_items": [{"dimension": "趣味性", "value": 1}]},
            agent_items_raw=[
                {"normalized_label": "游戏趣味性", "name": "游戏有趣", "evidence": "很好玩"},
                {"normalized_label": "环境", "name": "环境好"},
            ],
        )

        class EmptyLLM:
            def with_structured_output(self, schema, method="json_schema"):
                return self

        with patch(
            "flex_agent.eval.judge.build_semantic_alignment_for_texts",
            return_value={1: {"游戏趣味性": None, "环境": None}},
        ):
            result = judge_semantic(pair, EmptyLLM())
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["alignment"]["游戏趣味性"], ["趣味性"])

    def test_one_to_many_alignment_counts_multiple_human(self) -> None:
        from flex_agent.eval.judge import judge_semantic
        from flex_agent.eval.pairs import EvalPair

        pair = EvalPair(
            text_id=1,
            content="画面声音都很棒",
            human_items={"画面", "声音", "其他感官"},
            human_record={"human_items": [{"dimension": "画面", "value": 1}]},
            agent_items_raw=[{"normalized_label": "场景真实感", "name": "沉浸"}],
        )

        class FakeLLM:
            def with_structured_output(self, schema, method="json_schema"):
                return self

        with patch(
            "flex_agent.eval.judge.build_semantic_alignment_for_texts",
            return_value={1: {"场景真实感": ["画面", "声音", "其他感官"]}},
        ):
            result = judge_semantic(pair, FakeLLM())
        self.assertEqual(result["nums_both"], 1)
        self.assertEqual(result["human_only"], [])
        self.assertEqual(result["recall"], 1.0)


class SemanticMetricsTests(unittest.TestCase):
    def test_human_only_not_inflated_when_aligned(self) -> None:
        from flex_agent.eval.semantic_metrics import build_semantic_row

        row = build_semantic_row(
            36,
            {"体验探索", "生理舒适度"},
            {"晕动症", "游戏趣味性"},
            {"晕动症": "生理舒适度", "游戏趣味性": "体验探索"},
        )
        self.assertEqual(row["human_only"], [])
        self.assertEqual(row["nums_both"], 2)
        self.assertEqual(row["recall"], 1.0)

    def test_one_to_many_alignment(self) -> None:
        from flex_agent.eval.semantic_metrics import build_semantic_row

        row = build_semantic_row(
            1,
            {"画面", "声音", "其他感官", "态度"},
            {"场景真实感", "服务周到"},
            {"场景真实感": ["画面", "声音", "其他感官"], "服务周到": ["态度"]},
        )
        self.assertEqual(row["nums_both"], 2)
        self.assertEqual(row["human_only"], [])
        self.assertEqual(row["llm_only"], [])
        self.assertEqual(row["recall"], 1.0)
        self.assertEqual(row["precision"], 1.0)

    def test_prefetch_normalize_alias(self) -> None:
        from flex_agent.eval.semantic_metrics import prefetch_semantic_alignment

        matches = prefetch_semantic_alignment(
            {"服务态度", "画面"},
            {"态度", "画面"},
        )
        self.assertEqual(matches["服务态度"], "态度")
        self.assertEqual(matches["画面"], "画面")

    def test_heuristic_substring_match(self) -> None:
        from flex_agent.eval.semantic_metrics import apply_heuristic_semantic_alignment

        matches = apply_heuristic_semantic_alignment(
            {"游戏趣味性", "价格优惠", "环境"},
            {"趣味性"},
        )
        self.assertEqual(matches["游戏趣味性"], "趣味性")
        self.assertIsNone(matches["环境"])
        self.assertIsNone(matches["价格优惠"])

    def test_heuristic_bigram_overlap_match(self) -> None:
        from flex_agent.eval.semantic_metrics import apply_heuristic_semantic_alignment

        matches = apply_heuristic_semantic_alignment(
            {"沉浸体验"},
            {"体验探索"},
        )
        self.assertEqual(matches["沉浸体验"], "体验探索")

    def test_heuristic_allows_many_to_one(self) -> None:
        from flex_agent.eval.semantic_metrics import apply_heuristic_semantic_alignment

        matches = apply_heuristic_semantic_alignment(
            {"游戏趣味性", "趣味性体验"},
            {"趣味性"},
        )
        self.assertEqual(matches["游戏趣味性"], "趣味性")
        self.assertEqual(matches["趣味性体验"], "趣味性")

    def test_aggregate_recomputes_from_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            eval_dir = Path(tmpdir)
            eval_dir.joinpath("1.json").write_text(
                json.dumps(
                    {
                        "text_id": 1,
                        "semantic": {
                            "text_id": 1,
                            "human_items": ["趣味性"],
                            "agent_items": ["游戏趣味性", "环境", "价格优惠"],
                            "both": ["游戏趣味性"],
                            "llm_only": ["环境", "价格优惠"],
                            "human_only": ["趣味性"],
                            "nums_both": 1,
                            "nums_llm_only": 2,
                            "nums_human_only": 1,
                            "status": "complete",
                            "alignment": {
                                "游戏趣味性": "趣味性",
                                "环境": None,
                                "价格优惠": None,
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            from flex_agent.eval.aggregate import aggregate_eval_results

            agg = aggregate_eval_results(eval_dir)
            macro = agg["item_level_semantic"]["macro"]
            self.assertEqual(macro["n_intersection"], 1)
            self.assertEqual(macro["recall"], 1.0)
            self.assertAlmostEqual(macro["consistency"], 1 / 3, places=3)


class SemanticResumeTests(unittest.TestCase):
    def test_resume_skips_complete_semantic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Workspace(Path(tmpdir))
            workspace.ensure_layout()
            workspace.human_benchmark_path.parent.mkdir(parents=True, exist_ok=True)
            workspace.human_benchmark_path.write_text(
                json.dumps(
                    {
                        "comments": "画面很好",
                        "human_items": [{"dimension": "画面", "value": 1, "evidences": []}],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            workspace.save_coding(
                FinishedTextItem(
                    id=1,
                    content="画面很好",
                    content_with_labels="画面很好",
                    items=[FinishedItemDetail(name="画面清晰", normalized_label="画面")],
                )
            )
            workspace.save_eval_text(
                "open",
                1,
                {
                    "text_id": 1,
                    "semantic": {
                        "text_id": 1,
                        "status": "complete",
                        "both": ["画面"],
                        "human_items": ["画面"],
                        "agent_items": ["画面"],
                        "llm_only": [],
                        "human_only": [],
                        "nums_both": 1,
                        "nums_llm_only": 0,
                        "nums_human_only": 0,
                        "consistency": 1.0,
                        "precision": 1.0,
                        "recall": 1.0,
                        "alignment": {"画面": "画面"},
                    },
                },
            )

            from flex_agent.eval.batch_semantic import batch_semantic_judge
            from flex_agent.eval.pairs import load_eval_pairs

            pairs, _ = load_eval_pairs(workspace)
            call_count = 0

            class SpyLLM:
                def with_structured_output(self, schema, method="json_schema"):
                    nonlocal call_count
                    call_count += 1
                    raise AssertionError("should not call LLM for complete semantic")

            import asyncio

            stats = asyncio.run(
                batch_semantic_judge(workspace, pairs, SpyLLM(), resume=True, on_progress=None)
            )
            self.assertEqual(stats["skipped"], 1)
            self.assertEqual(stats["judged"], 0)
            self.assertEqual(call_count, 0)


class RunAsyncTests(unittest.TestCase):
    def test_run_async_from_running_loop(self) -> None:
        import asyncio

        from flex_agent.eval.async_utils import run_async

        async def _sample() -> str:
            await asyncio.sleep(0)
            return "ok"

        async def _nested() -> str:
            return run_async(_sample())

        result = asyncio.run(_nested())
        self.assertEqual(result, "ok")


if __name__ == "__main__":
    unittest.main()
