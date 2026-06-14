from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flex_agent.workspace import Workspace


class EvalStoreTests(unittest.TestCase):
    def test_save_eval_result_writes_summary_report_and_per_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Workspace(Path(tmpdir))
            workspace.ensure_layout()

            summary_path = workspace.save_eval_result(
                "open",
                payload={
                    "mode": "both",
                    "item_level_keyword": {
                        "micro": {"consistency": 1.0},
                        "per_text": [
                            {"text_id": 1, "consistency": 1.0},
                            {"text_id": 2, "consistency": 0.5},
                        ],
                    },
                    "item_level_semantic": {
                        "micro": {"consistency": 0.8},
                        "per_text": [{"text_id": 1, "consistency": 0.8}],
                    },
                },
                report="report body",
                meta={
                    "mode": "both",
                    "align": False,
                    "coded_count": 2,
                    "benchmark_path": str(workspace.human_benchmark_path),
                },
            )

            self.assertEqual(summary_path, workspace.eval_summary_path("open"))
            self.assertTrue(summary_path.exists())
            self.assertEqual(
                workspace.eval_report_path("open").read_text(encoding="utf-8"),
                "report body",
            )
            self.assertEqual(workspace.list_eval_text_ids("open"), [1, 2])

            text_one = json.loads(workspace.eval_text_path("open", 1).read_text(encoding="utf-8"))
            self.assertEqual(text_one["text_id"], 1)
            self.assertIsNotNone(text_one["keyword"])
            self.assertIsNotNone(text_one["semantic"])

            text_two = json.loads(workspace.eval_text_path("open", 2).read_text(encoding="utf-8"))
            self.assertEqual(text_two["text_id"], 2)
            self.assertIsNotNone(text_two["keyword"])
            self.assertIsNone(text_two["semantic"])

            summary = workspace.load_eval_summary("open")
            assert summary is not None
            self.assertEqual(summary["mode"], "both")
            self.assertEqual(summary["coded_count"], 2)
            keyword = summary["item_level_keyword"]
            assert keyword is not None
            self.assertNotIn("per_text", keyword)
            semantic = summary["item_level_semantic"]
            assert semantic is not None
            self.assertNotIn("per_text", semantic)

    def test_save_eval_result_removes_stale_per_text_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Workspace(Path(tmpdir))
            workspace.ensure_layout()

            workspace.save_eval_result(
                "open",
                payload={
                    "mode": "keyword",
                    "item_level_keyword": {
                        "per_text": [
                            {"text_id": 1, "consistency": 1.0},
                            {"text_id": 2, "consistency": 0.5},
                        ],
                    },
                },
                report="first",
                meta={"mode": "keyword", "align": False, "coded_count": 2, "benchmark_path": "x"},
            )
            self.assertEqual(workspace.list_eval_text_ids("open"), [1, 2])

            workspace.save_eval_result(
                "open",
                payload={
                    "mode": "keyword",
                    "item_level_keyword": {
                        "per_text": [{"text_id": 3, "consistency": 0.9}],
                    },
                },
                report="second",
                meta={"mode": "keyword", "align": False, "coded_count": 1, "benchmark_path": "x"},
            )

            self.assertEqual(workspace.list_eval_text_ids("open"), [3])
            self.assertFalse(workspace.eval_text_path("open", 1).exists())
            self.assertFalse(workspace.eval_text_path("open", 2).exists())

    def test_status_includes_eval_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Workspace(Path(tmpdir))
            workspace.ensure_layout()
            workspace.save_eval_result(
                "open",
                payload={
                    "mode": "keyword",
                    "item_level_keyword": {"per_text": [{"text_id": 7, "consistency": 1.0}]},
                },
                report="ok",
                meta={"mode": "keyword", "align": False, "coded_count": 1, "benchmark_path": "x"},
            )
            status = workspace.status()
            self.assertEqual(status["eval_open_count"], 1)
            self.assertEqual(status["eval_axial_count"], 0)
            self.assertIsNotNone(status["latest_eval_open"])

    def test_clear_artifacts_removes_eval_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Workspace(Path(tmpdir))
            workspace.ensure_layout()
            workspace.save_eval_result(
                "open",
                payload={
                    "mode": "keyword",
                    "item_level_keyword": {"per_text": [{"text_id": 1, "consistency": 1.0}]},
                },
                report="ok",
                meta={"mode": "keyword", "align": False, "coded_count": 1, "benchmark_path": "x"},
            )
            self.assertTrue(workspace.eval_open_dir.exists())

            workspace.clear_artifacts()

            self.assertTrue(workspace.eval_open_dir.exists())
            self.assertEqual(workspace.list_eval_text_ids("open"), [])
            self.assertIsNone(workspace.load_eval_summary("open"))


if __name__ == "__main__":
    unittest.main()
