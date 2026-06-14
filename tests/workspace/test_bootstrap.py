from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from flex_agent.config import PROJECT_ROOT
from flex_agent.models import FinishedItemDetail, FinishedTextItem
from flex_agent.workspace import Workspace


class BootstrapSeedFilesTests(unittest.TestCase):
    def test_copies_seed_files_into_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Workspace(Path(tmpdir))
            actions = workspace.bootstrap_seed_files()

            self.assertTrue(workspace.corpus_seed_path.exists())
            self.assertTrue(workspace.human_benchmark_path.exists())
            self.assertEqual(actions[str(workspace.corpus_seed_path)], "copied")
            self.assertEqual(actions[str(workspace.human_benchmark_path)], "copied")
            self.assertTrue(workspace.benchmark_ready())

    def test_keeps_existing_when_source_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Workspace(Path(tmpdir))
            workspace.ensure_layout()
            workspace.human_benchmark_path.write_text('{"marker": true}\n', encoding="utf-8")
            source = PROJECT_ROOT / "data" / "codebook_done_human.jsonl"
            if not source.exists():
                actions = workspace.bootstrap_seed_files()
                self.assertEqual(actions[str(workspace.human_benchmark_path)], "kept")
                self.assertEqual(
                    workspace.human_benchmark_path.read_text(encoding="utf-8"),
                    '{"marker": true}\n',
                )

    def test_benchmark_ready_false_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Workspace(Path(tmpdir))
            self.assertFalse(workspace.benchmark_ready())


class ClearArtifactsTests(unittest.TestCase):
    def test_preserves_corpus_and_private(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Workspace(Path(tmpdir))
            workspace.bootstrap_seed_files()
            workspace.save_coding(
                FinishedTextItem(
                    id=1,
                    content="test",
                    content_with_labels="test",
                    items=[FinishedItemDetail(name="x")],
                )
            )
            self.assertTrue((workspace.coding_dir / "1.json").exists())

            workspace.clear_artifacts()

            self.assertTrue(workspace.corpus_seed_path.exists())
            self.assertTrue(workspace.human_benchmark_path.exists())
            self.assertFalse((workspace.coding_dir / "1.json").exists())


if __name__ == "__main__":
    unittest.main()
