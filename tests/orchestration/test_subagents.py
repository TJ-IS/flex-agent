from __future__ import annotations

import unittest

from flex_agent.coding.agents import PromptContext
from flex_agent.orchestration.subagents import (
    AXIAL_CODING_SUBAGENT,
    INDUCTION_SUBAGENT,
    OPEN_CODING_SUBAGENT,
    build_subagents,
)


def _prompt_ctx(language: str = "zh") -> PromptContext:
    return PromptContext(
        grounded_theory_background="gt",
        task_background="task",
        open_coding_template="open-coding-template",
        induction_template="induction-template",
        axial_refinement_template="axial-coding-template",
        language=language,  # type: ignore[arg-type]
    )


class SubagentPromptTests(unittest.TestCase):
    def test_subagent_prompts_keep_workspace_schema_constraints(self) -> None:
        subagents = {item["name"]: item for item in build_subagents(_prompt_ctx())}
        prompt_text = "\n".join(item["system_prompt"] for item in subagents.values())

        self.assertNotIn("只返回简洁结论", prompt_text)
        self.assertIn("聊天回复可以简洁", prompt_text)
        self.assertIn("禁止访问 `private/`", prompt_text)
        self.assertIn("禁止访问 `private/` 与 `eval/`", prompt_text)

        open_coding_prompt = subagents[OPEN_CODING_SUBAGENT]["system_prompt"]
        self.assertIn("`coding/{id}.json`", open_coding_prompt)
        self.assertIn("单个 JSON 对象", open_coding_prompt)
        self.assertIn("content_with_labels", open_coding_prompt)
        self.assertIn("normalized_label", open_coding_prompt)

        for name in (INDUCTION_SUBAGENT, AXIAL_CODING_SUBAGENT):
            codebook_prompt = subagents[name]["system_prompt"]
            self.assertIn("`codebook/dimensions.json`", codebook_prompt)
            self.assertIn("维度对象数组", codebook_prompt)
            self.assertIn("不要写成带 `dimensions` 包装层的对象", codebook_prompt)

    def test_subagent_prompts_switch_to_english(self) -> None:
        subagents = {item["name"]: item for item in build_subagents(_prompt_ctx("en"), language="en")}
        prompt_text = "\n".join(item["system_prompt"] for item in subagents.values())

        self.assertIn("Do not access the `private/` or `eval/`", prompt_text)
        self.assertIn("one JSON object", subagents[OPEN_CODING_SUBAGENT]["system_prompt"])
        self.assertIn("array of dimension objects", subagents[INDUCTION_SUBAGENT]["system_prompt"])
        self.assertIn("do not wrap it in a top-level `dimensions` object", prompt_text)
        self.assertNotIn("禁止访问", prompt_text)
        self.assertNotIn("维度对象数组", prompt_text)


if __name__ == "__main__":
    unittest.main()
