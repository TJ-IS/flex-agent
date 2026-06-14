from __future__ import annotations

from flex_agent.config import PROJECT_ROOT

PROMPTS_DIR = PROJECT_ROOT / "prompts"


def _read_prompt_file(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def text_alignment_prompt() -> str:
    return _read_prompt_file("eval_text_alignment.md")


def dimension_name_alignment_prompt(*, human_list: str, agent_list: str) -> str:
    return _read_prompt_file("eval_dimension_name_alignment.md").format(
        human_list=human_list,
        agent_list=agent_list,
    )
