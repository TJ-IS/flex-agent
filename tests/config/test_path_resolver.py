from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flex_agent.config import (
    DEFAULT_PROMPTS_DIR,
    DEFAULT_WORKSPACE,
    PROJECT_ROOT,
    REQUIRED_PROMPT_FILES,
    default_prompts_dir,
    get_prompts_dir,
    path_label,
    resolve_prompts_dir,
    resolve_workspace_dir,
    set_prompts_dir,
)
from flex_agent.coding.agents import PromptContext
from flex_agent.i18n import resolve_language


class PathResolverTests(unittest.TestCase):
    def test_resolve_prompts_dir_shorthand(self) -> None:
        resolved = resolve_prompts_dir("baseline")
        self.assertEqual(resolved, DEFAULT_PROMPTS_DIR.resolve())
        for name in REQUIRED_PROMPT_FILES:
            self.assertTrue((resolved / name).is_file())

    def test_resolve_prompts_dir_relative(self) -> None:
        resolved = resolve_prompts_dir("prompts/baseline")
        self.assertEqual(resolved, DEFAULT_PROMPTS_DIR.resolve())

    def test_resolve_prompts_dir_defaults_by_language(self) -> None:
        resolved = resolve_prompts_dir(None, language="en")
        self.assertEqual(resolved, default_prompts_dir("en"))
        self.assertEqual(resolved.name, "baseline_en")

    def test_resolve_language_default_and_invalid(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(resolve_language(None), "zh")
        with self.assertRaises(ValueError):
            resolve_language("fr")

    def test_explicit_prompts_dir_overrides_language_default(self) -> None:
        resolved = resolve_prompts_dir("baseline", language="en")
        self.assertEqual(resolved, DEFAULT_PROMPTS_DIR.resolve())

    def test_resolve_workspace_dir_shorthand(self) -> None:
        resolved = resolve_workspace_dir("baseline")
        self.assertEqual(resolved, DEFAULT_WORKSPACE.resolve())

    def test_resolve_workspace_dir_relative(self) -> None:
        resolved = resolve_workspace_dir("workspaces/baseline")
        self.assertEqual(resolved, DEFAULT_WORKSPACE.resolve())

    def test_resolve_workspace_dir_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            resolved = resolve_workspace_dir(tmp)
            self.assertEqual(resolved, Path(tmp).resolve())

    def test_path_label_relative(self) -> None:
        label = path_label(DEFAULT_PROMPTS_DIR)
        self.assertEqual(label, "prompts/baseline")

    def test_resolve_prompts_dir_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty"
            empty.mkdir()
            with self.assertRaises(FileNotFoundError):
                resolve_prompts_dir(empty)

    def test_legacy_prompt_filenames_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompts = Path(tmp) / "legacy_prompts"
            prompts.mkdir()
            (prompts / "grounded_theory_background.md").write_text("GT", encoding="utf-8")
            (prompts / "task_background.md").write_text("TASK", encoding="utf-8")
            for name in ("agent_bob.md", "agent_alice.md", "agent_kevin.md"):
                (prompts / name).write_text(
                    "legacy {grounded_theory_background} {task_background}",
                    encoding="utf-8",
                )
            for name in ("eval_text_alignment.md", "eval_dimension_name_alignment.md"):
                (prompts / name).write_text("eval", encoding="utf-8")

            resolved = resolve_prompts_dir(prompts)
            ctx = PromptContext.load(resolved)

            self.assertEqual(resolved, prompts.resolve())
            self.assertEqual(ctx.open_coding_template, "legacy GT TASK")

    def test_set_prompts_dir_updates_session(self) -> None:
        set_prompts_dir("baseline")
        self.assertEqual(get_prompts_dir(), DEFAULT_PROMPTS_DIR.resolve())


if __name__ == "__main__":
    unittest.main()
