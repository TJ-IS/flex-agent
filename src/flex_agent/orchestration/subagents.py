from __future__ import annotations

from deepagents.middleware.filesystem import FilesystemPermission

from flex_agent.coding.agents import PromptContext
from flex_agent.i18n import get_bundle

SUBAGENT_DENY_PRIVATE = [
    FilesystemPermission(
        operations=["read", "write"],
        paths=["/private/**", "/eval/**"],
        mode="deny",
    ),
]

OPEN_CODING_SUBAGENT = "open-coding"
INDUCTION_SUBAGENT = "construct-induction"
AXIAL_CODING_SUBAGENT = "axial-coding"


def build_subagents(prompt_ctx: PromptContext | None = None, *, language: str | None = None) -> list[dict]:
    ctx = prompt_ctx or PromptContext.load()
    bundle = get_bundle(language or ctx.language).llm
    return [
        {
            "name": OPEN_CODING_SUBAGENT,
            "description": bundle.subagent_descriptions[OPEN_CODING_SUBAGENT],
            "system_prompt": (
                ctx.open_coding_template
                + bundle.subagent_addenda[OPEN_CODING_SUBAGENT]
                + bundle.open_coding_workspace_schema_note
                + bundle.private_access_note
            ),
            "permissions": SUBAGENT_DENY_PRIVATE,
        },
        {
            "name": INDUCTION_SUBAGENT,
            "description": bundle.subagent_descriptions[INDUCTION_SUBAGENT],
            "system_prompt": (
                ctx.induction_template
                + bundle.subagent_addenda[INDUCTION_SUBAGENT]
                + bundle.codebook_workspace_schema_note
                + bundle.private_access_note
            ),
            "permissions": SUBAGENT_DENY_PRIVATE,
        },
        {
            "name": AXIAL_CODING_SUBAGENT,
            "description": bundle.subagent_descriptions[AXIAL_CODING_SUBAGENT],
            "system_prompt": (
                ctx.axial_refinement_template
                + bundle.subagent_addenda[AXIAL_CODING_SUBAGENT]
                + bundle.codebook_workspace_schema_note
                + bundle.private_access_note
            ),
            "permissions": SUBAGENT_DENY_PRIVATE,
        },
    ]
