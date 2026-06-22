from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flex_agent.coding.agents import OpenCodingItemDetail, OpenCodingOutput, PromptContext
from flex_agent.orchestration.tools import CodingToolContext, build_coding_tools
from flex_agent.workspace import Workspace


def _minimal_prompt_ctx() -> PromptContext:
    return PromptContext(
        grounded_theory_background="gt",
        task_background="task",
        open_coding_template="open-coding",
        induction_template="induction",
        axial_refinement_template="axial-coding",
    )


def _setup_workspace(root: Path, *, count: int = 3) -> Workspace:
    data_path = root / "data.jsonl"
    data_path.write_text(
        "\n".join(
            json.dumps({"comments": f"comment {idx}"}, ensure_ascii=False)
            for idx in range(1, count + 1)
        ),
        encoding="utf-8",
    )
    ws = Workspace(root / "workspace")
    ws.init_run(
        data_path=data_path,
        max_nums=count,
        codebook_nums=1,
        kevin_batch_size=1,
    )
    return ws


def _batch_open_coding_tool(ctx: CodingToolContext):
    tools = build_coding_tools(ctx)
    return next(tool for tool in tools if tool.name == "batch_open_coding")


def _legacy_batch_open_coding_tool(ctx: CodingToolContext):
    tools = build_coding_tools(ctx)
    return next(tool for tool in tools if tool.name == "batch_bob_code")


class BatchOpenCodingProgressTests(unittest.TestCase):
    def test_batch_open_coding_emits_start_and_completion_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _setup_workspace(Path(tmp))
            messages: list[str] = []
            ctx = CodingToolContext(
                workspace=ws,
                llm=object(),
                llm_pro=object(),
                prompt_ctx=_minimal_prompt_ctx(),
                prompts_dir_label="prompts/test",
                workspace_dir_label="workspaces/test",
                on_progress=messages.append,
            )

            async def mock_arun_open_coding(_llm, _prompt_ctx, text):
                return OpenCodingOutput(
                    content_with_labels=text.content,
                    items=[
                        OpenCodingItemDetail(
                            name="条目",
                            normalized_label="维度",
                            evidence=text.content,
                        )
                    ],
                )

            with patch("flex_agent.orchestration.tools.arun_open_coding", side_effect=mock_arun_open_coding):
                result = asyncio.run(_batch_open_coding_tool(ctx).coroutine())

            self.assertIn("OpenCoding processed 3/3 texts", result)
            self.assertEqual(messages[0], "[OpenCoding] 开始编码 3 条 (concurrency=10)")
            completion_lines = [line for line in messages if line.startswith("[OpenCoding] 完成")]
            self.assertEqual(len(completion_lines), 3)
            for line in completion_lines:
                self.assertIn("· items=1", line)
            done_counts = sorted(
                int(line.split("(")[1].split("/")[0]) for line in completion_lines
            )
            self.assertEqual(done_counts, [1, 2, 3])

    def test_batch_open_coding_emits_skip_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _setup_workspace(Path(tmp), count=2)
            messages: list[str] = []
            ctx = CodingToolContext(
                workspace=ws,
                llm=object(),
                llm_pro=object(),
                prompt_ctx=_minimal_prompt_ctx(),
                prompts_dir_label="prompts/test",
                workspace_dir_label="workspaces/test",
                on_progress=messages.append,
            )

            async def mock_arun_open_coding(_llm, _prompt_ctx, text):
                if text.id == 1:
                    raise RuntimeError("boom")
                return OpenCodingOutput(
                    content_with_labels=text.content,
                    items=[
                        OpenCodingItemDetail(
                            name="条目",
                            normalized_label="维度",
                        )
                    ],
                )

            with patch("flex_agent.orchestration.tools.arun_open_coding", side_effect=mock_arun_open_coding):
                result = asyncio.run(
                    _batch_open_coding_tool(ctx).coroutine(text_ids=[1, 2], concurrency_limit=1)
                )

            self.assertIn("OpenCoding processed 1/2 texts", result)
            skip_lines = [line for line in messages if line.startswith("[OpenCoding] 跳过")]
            self.assertEqual(len(skip_lines), 1)
            self.assertIn("text_id=1", skip_lines[0])
            complete_lines = [line for line in messages if line.startswith("[OpenCoding] 完成")]
            self.assertEqual(len(complete_lines), 1)
            self.assertIn("text_id=2", complete_lines[0])

    def test_batch_open_coding_allows_none_on_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _setup_workspace(Path(tmp), count=1)
            ctx = CodingToolContext(
                workspace=ws,
                llm=object(),
                llm_pro=object(),
                prompt_ctx=_minimal_prompt_ctx(),
                prompts_dir_label="prompts/test",
                workspace_dir_label="workspaces/test",
                on_progress=None,
            )

            async def mock_arun_open_coding(_llm, _prompt_ctx, text):
                return OpenCodingOutput(
                    content_with_labels=text.content,
                    items=[
                        OpenCodingItemDetail(
                            name="条目",
                            normalized_label="维度",
                        )
                    ],
                )

            with patch("flex_agent.orchestration.tools.arun_open_coding", side_effect=mock_arun_open_coding):
                result = asyncio.run(_batch_open_coding_tool(ctx).coroutine())

            self.assertIn("OpenCoding processed 1/1 texts", result)

    def test_legacy_batch_tool_alias_calls_open_coding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _setup_workspace(Path(tmp), count=1)
            ctx = CodingToolContext(
                workspace=ws,
                llm=object(),
                llm_pro=object(),
                prompt_ctx=_minimal_prompt_ctx(),
                prompts_dir_label="prompts/test",
                workspace_dir_label="workspaces/test",
                on_progress=None,
            )

            async def mock_arun_open_coding(_llm, _prompt_ctx, text):
                return OpenCodingOutput(
                    content_with_labels=text.content,
                    items=[OpenCodingItemDetail(name="条目", normalized_label="维度")],
                )

            with patch("flex_agent.orchestration.tools.arun_open_coding", side_effect=mock_arun_open_coding):
                result = asyncio.run(_legacy_batch_open_coding_tool(ctx).coroutine())

            self.assertIn("OpenCoding processed 1/1 texts", result)


if __name__ == "__main__":
    unittest.main()
