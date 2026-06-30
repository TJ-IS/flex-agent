from __future__ import annotations

import sys

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from flex_agent.eval.prompts import dimension_name_alignment_prompt
from flex_agent.eval.async_utils import run_async
from flex_agent.i18n import get_bundle
from flex_agent.llm.structured_output import ainvoke_structured


async def abuild_dimension_name_alignment(
    agent_dimensions: list[str],
    human_dimensions: list[str],
    llm: BaseChatModel,
) -> dict[str, str | None]:
    """Use LLM to map agent dimension names to human dimension names."""
    if not agent_dimensions:
        return {}

    agent_list = "\n".join(f"- {d}" for d in agent_dimensions)
    human_list = "\n".join(f"- {d}" for d in human_dimensions)

    prompt = dimension_name_alignment_prompt(human_list=human_list, agent_list=agent_list)
    bundle = get_bundle()

    class AlignmentResult(BaseModel):
        mapping: dict[str, str | None] = Field(
            description=bundle.llm.schema_descriptions["dimension_alignment_mapping"]
        )

    chat_prompt = ChatPromptTemplate.from_messages([("human", prompt)])

    try:
        result = await ainvoke_structured(
            llm,
            chat_prompt,
            AlignmentResult,
            {},
            component="eval-dimension-alignment",
        )
        validated: dict[str, str | None] = {}
        for agent_dim, human_dim in result.mapping.items():
            if agent_dim not in agent_dimensions:
                continue
            if human_dim is None:
                validated[agent_dim] = None
            elif human_dim in human_dimensions:
                validated[agent_dim] = human_dim
            else:
                validated[agent_dim] = None
        return validated
    except Exception as exc:
        print(
            bundle.llm.eval_dimension_warning.format(error=exc),
            file=sys.stderr,
        )
        return {}


def build_dimension_name_alignment(
    agent_dimensions: list[str],
    human_dimensions: list[str],
    llm: BaseChatModel,
) -> dict[str, str | None]:
    return run_async(
        abuild_dimension_name_alignment(agent_dimensions, human_dimensions, llm)
    )
