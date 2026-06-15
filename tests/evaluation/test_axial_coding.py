from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flex_agent.eval.axial_aggregate import (
    aggregate_axial_global_payload,
    axial_global_result_path,
)
from flex_agent.eval.axial_alignment import BatchAxialSemanticAlignment, build_axial_semantic_alignment_for_texts
from flex_agent.eval.axial_core import (
    agent_axial_dims_for_coding,
    build_codebook_item_index,
    codebook_axial_dims,
    enforce_one_to_one_alignment,
    human_categories_from_record,
    human_category_taxonomy,
    keyword_alignment,
    keyword_match_agent_to_category,
    normalize_category,
)
from flex_agent.eval.axial_judge import judge_axial_global_keyword, judge_axial_global_semantic
from flex_agent.eval.axial_pairs import load_axial_eval_pairs, load_axial_global_eval
from flex_agent.eval.prompts import axial_category_alignment_prompt
from flex_agent.models import DimensionDetail, FinishedItemDetail, FinishedTextItem
from flex_agent.workspace import Workspace


class NormalizeCategoryTests(unittest.TestCase):
    def test_canonical_category(self) -> None:
        self.assertEqual(normalize_category("interactive service"), "interactive service")
        self.assertEqual(normalize_category("Installation"), "Installation")
        self.assertEqual(normalize_category("installation"), "Installation")


class HumanCategoriesFromRecordTests(unittest.TestCase):
    def test_extracts_active_categories_from_human_items(self) -> None:
        record = {
            "human_items": [
                {"category": "interactive service", "dimension": "态度", "value": 1},
                {"category": "sensory appeal", "dimension": "画面", "value": 0},
                {"category": "playfulness", "dimension": "趣味性", "value": -1},
            ]
        }
        categories = human_categories_from_record(record)
        self.assertEqual(categories, {"interactive service", "playfulness"})


class GlobalContextTests(unittest.TestCase):
    def test_load_axial_global_eval_uses_full_codebook_and_taxonomy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Workspace(Path(tmpdir))
            workspace.ensure_layout()
            workspace.save_dimensions([
                DimensionDetail(name="服务体验", items=["态度"]),
                DimensionDetail(name="沉浸体验", items=["画面"]),
            ])
            ctx = load_axial_global_eval(workspace)
            self.assertEqual(ctx.agent_axial_dims, {"服务体验", "沉浸体验"})
            self.assertEqual(ctx.human_categories, human_category_taxonomy())
            self.assertEqual(len(ctx.agent_dimensions_detail), 2)


class CodebookLookupTests(unittest.TestCase):
    def test_maps_open_label_to_axial_dimension(self) -> None:
        dimensions = [
            DimensionDetail(name="服务体验", items=["态度", "服务专业"]),
            DimensionDetail(name="沉浸体验", items=["画面", "沉浸感"]),
        ]
        index = build_codebook_item_index(dimensions)
        coding = FinishedTextItem(
            id=1,
            content="服务很好，画面清晰",
            content_with_labels="服务很好，画面清晰",
            items=[
                FinishedItemDetail(name="态度好", normalized_label="态度", evidence="服务很好"),
                FinishedItemDetail(name="画面好", normalized_label="画面", evidence="画面清晰"),
            ],
        )
        dims = agent_axial_dims_for_coding(coding, index)
        self.assertEqual(dims, {"服务体验", "沉浸体验"})
        self.assertEqual(codebook_axial_dims(dimensions), {"服务体验", "沉浸体验"})


class KeywordAlignmentTests(unittest.TestCase):
    def test_alias_match(self) -> None:
        self.assertTrue(keyword_match_agent_to_category("服务体验", "interactive service"))
        self.assertTrue(keyword_match_agent_to_category("沉浸体验", "sensory appeal"))

    def test_partial_overlap_counts(self) -> None:
        matched_agent, matched_human = keyword_alignment(
            {"服务体验", "价格感知"},
            {"interactive service", "sensory appeal"},
        )
        self.assertIn("服务体验", matched_agent)
        self.assertIn("interactive service", matched_human)
        self.assertEqual(len(matched_agent), len(matched_human))

    def test_one_to_one_rejects_many_to_one(self) -> None:
        matched_agent, matched_human = keyword_alignment(
            {"服务体验", "态度", "服务专业"},
            {"interactive service"},
        )
        self.assertEqual(len(matched_agent), 1)
        self.assertEqual(len(matched_human), 1)

    def test_enforce_one_to_one_alignment(self) -> None:
        strict = enforce_one_to_one_alignment(
            {
                "服务体验": "interactive service",
                "态度": "interactive service",
            },
            agent_dims={"服务体验", "态度"},
            human_categories={"interactive service"},
        )
        matched = [agent for agent, category in strict.items() if category]
        self.assertEqual(len(matched), 1)


class AxialPromptTests(unittest.TestCase):
    def test_axial_category_alignment_prompt_has_placeholder(self) -> None:
        prompt = axial_category_alignment_prompt()
        self.assertIn("{texts_json}", prompt)
        self.assertIn("matched_human_category", prompt)
        self.assertIn("一对一", prompt)


class AxialSemanticAlignmentLLMTests(unittest.TestCase):
    def test_validates_fake_llm_structured_output(self) -> None:
        class FakeChain:
            def invoke(self, payload):
                from flex_agent.eval.axial_alignment import (
                    AxialSemanticMatch,
                    AxialTextSemanticAlignment,
                )

                return BatchAxialSemanticAlignment(
                    texts=[
                        AxialTextSemanticAlignment(
                            text_id="0",
                            matches=[
                                AxialSemanticMatch(
                                    agent_dimension="服务体验",
                                    matched_human_category="interactive service",
                                ),
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
                "text_id": 0,
                "content": "workspace",
                "human_categories": list(human_category_taxonomy()),
                "agent_dimensions": [
                    {"name": "服务体验", "definition": "服务相关", "items": ["态度"]},
                ],
            }
        ]
        with patch(
            "flex_agent.eval.axial_alignment.ChatPromptTemplate.from_messages",
            return_value=FakePrompt(),
        ):
            result = build_axial_semantic_alignment_for_texts(entries, FakeLLM())
        self.assertEqual(result[0]["服务体验"], "interactive service")


class EvaluateAxialWorkspaceTests(unittest.TestCase):
    def _seed_workspace(self, root: Path) -> Workspace:
        workspace = Workspace(root)
        workspace.ensure_layout()
        workspace.human_benchmark_path.parent.mkdir(parents=True, exist_ok=True)
        workspace.human_benchmark_path.write_text(
            json.dumps({"comments": "服务很好", "human_items": []}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        workspace.corpus_seed_path.parent.mkdir(parents=True, exist_ok=True)
        workspace.corpus_seed_path.write_text(
            json.dumps({"id": 1, "comments": "服务很好"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        workspace.save_dimensions([
            DimensionDetail(name="服务体验", items=["态度", "服务专业"], definition="服务"),
            DimensionDetail(name="沉浸体验", items=["画面", "沉浸感"], definition="感官"),
        ])
        return workspace

    def test_evaluate_axial_workspace_keyword_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self._seed_workspace(Path(tmpdir))
            from flex_agent.eval.axial_runner import evaluate_axial_workspace

            report = evaluate_axial_workspace(
                workspace,
                mode="keyword",
                save_json=False,
                on_progress=None,
            )
            self.assertIn("workspace", report)
            self.assertIn("category 名匹配", report)

    def test_evaluate_axial_workspace_persists_global_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self._seed_workspace(Path(tmpdir))
            from flex_agent.eval.axial_runner import evaluate_axial_workspace

            evaluate_axial_workspace(workspace, mode="keyword", on_progress=None)
            global_path = axial_global_result_path(workspace.eval_axial_dir)
            self.assertTrue(global_path.exists())
            payload = json.loads(global_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["scope"], "workspace")
            self.assertIn("keyword", payload)
            self.assertFalse(workspace.eval_text_path("axial", 1).exists())

    def test_evaluate_axial_workspace_metrics_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self._seed_workspace(Path(tmpdir))
            from flex_agent.eval.axial_runner import evaluate_axial_workspace

            evaluate_axial_workspace(workspace, mode="keyword", on_progress=None)
            report = evaluate_axial_workspace(workspace, mode="metrics", on_progress=None)
            self.assertIn("workspace", report)

    def test_raises_when_codebook_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self._seed_workspace(Path(tmpdir))
            workspace.save_dimensions([])
            from flex_agent.eval.axial_runner import evaluate_axial_workspace

            with self.assertRaises(RuntimeError):
                evaluate_axial_workspace(workspace, mode="keyword", on_progress=None)

    def test_aggregate_global_payload_single_row(self) -> None:
        payload = {
            "scope": "workspace",
            "keyword": {
                "text_id": 0,
                "human_items": ["interactive service"],
                "agent_items": ["服务体验"],
                "both": ["服务体验"],
                "llm_only": [],
                "human_only": [],
                "nums_both": 1,
                "nums_llm_only": 0,
                "nums_human_only": 0,
                "consistency": 1.0,
                "precision": 1.0,
                "recall": 1.0,
                "status": "complete",
            },
        }
        agg = aggregate_axial_global_payload(payload)
        self.assertEqual(agg["keyword_complete"], 1)
        self.assertEqual(agg["item_level_keyword"]["micro"]["consistency"], 1.0)

    def test_load_axial_eval_pairs_still_available_for_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Workspace(Path(tmpdir))
            workspace.ensure_layout()
            workspace.human_benchmark_path.parent.mkdir(parents=True, exist_ok=True)
            workspace.human_benchmark_path.write_text(
                json.dumps(
                    {
                        "comments": "服务很好，画面清晰",
                        "human_items": [
                            {"category": "interactive service", "dimension": "态度", "value": 1},
                            {"category": "sensory appeal", "dimension": "画面", "value": 1},
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            workspace.save_coding(
                FinishedTextItem(
                    id=1,
                    content="服务很好，画面清晰",
                    content_with_labels="服务很好，画面清晰",
                    items=[
                        FinishedItemDetail(name="态度好", normalized_label="态度", evidence="服务很好"),
                        FinishedItemDetail(name="画面好", normalized_label="画面", evidence="画面清晰"),
                    ],
                )
            )
            workspace.save_dimensions([
                DimensionDetail(name="服务体验", items=["态度"]),
                DimensionDetail(name="沉浸体验", items=["画面"]),
            ])
            pairs, _ = load_axial_eval_pairs(workspace)
            self.assertEqual(len(pairs), 1)


class JudgeAxialGlobalTests(unittest.TestCase):
    def test_global_keyword_and_semantic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Workspace(Path(tmpdir))
            workspace.ensure_layout()
            workspace.save_dimensions([
                DimensionDetail(name="服务体验", items=["态度"], definition="服务"),
            ])
            ctx = load_axial_global_eval(workspace)

            keyword = judge_axial_global_keyword(ctx)
            self.assertGreater(keyword["nums_both"], 0)

            class FakeChain:
                def invoke(self, payload):
                    from flex_agent.eval.axial_alignment import (
                        AxialSemanticMatch,
                        AxialTextSemanticAlignment,
                    )

                    return BatchAxialSemanticAlignment(
                        texts=[
                            AxialTextSemanticAlignment(
                                text_id="0",
                                matches=[
                                    AxialSemanticMatch(
                                        agent_dimension="服务体验",
                                        matched_human_category="interactive service",
                                    )
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

            with patch(
                "flex_agent.eval.axial_alignment.ChatPromptTemplate.from_messages",
                return_value=FakePrompt(),
            ):
                semantic = judge_axial_global_semantic(ctx, FakeLLM())
            self.assertEqual(semantic["status"], "complete")
            self.assertEqual(semantic["nums_both"], 1)


if __name__ == "__main__":
    unittest.main()
