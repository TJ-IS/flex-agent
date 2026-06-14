from __future__ import annotations

import unittest

from flex_agent.coding.agents import PromptContext
from flex_agent.orchestration.subagents import build_subagents


def _prompt_ctx() -> PromptContext:
    return PromptContext(
        grounded_theory_background="gt",
        task_background="task",
        bob_template="bob-template",
        alice_template="alice-template",
        kevin_template="kevin-template",
    )


class SubagentPromptTests(unittest.TestCase):
    def test_subagent_prompts_keep_workspace_schema_constraints(self) -> None:
        subagents = {item["name"]: item for item in build_subagents(_prompt_ctx())}
        prompt_text = "\n".join(item["system_prompt"] for item in subagents.values())

        self.assertNotIn("只返回简洁结论", prompt_text)
        self.assertIn("聊天回复可以简洁", prompt_text)
        self.assertIn("禁止访问 `private/`", prompt_text)
        self.assertIn("禁止访问 `private/` 与 `eval/`", prompt_text)

        bob_prompt = subagents["bob-coder"]["system_prompt"]
        self.assertIn("`coding/{id}.json`", bob_prompt)
        self.assertIn("单个 JSON 对象", bob_prompt)
        self.assertIn("content_with_labels", bob_prompt)
        self.assertIn("normalized_label", bob_prompt)

        for name in ("alice-codebook", "kevin-updater"):
            codebook_prompt = subagents[name]["system_prompt"]
            self.assertIn("`codebook/dimensions.json`", codebook_prompt)
            self.assertIn("维度对象数组", codebook_prompt)
            self.assertIn("不要写成带 `dimensions` 包装层的对象", codebook_prompt)


if __name__ == "__main__":
    unittest.main()
