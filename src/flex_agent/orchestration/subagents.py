from __future__ import annotations

from deepagents.middleware.filesystem import FilesystemPermission

from flex_agent.coding.agents import PromptContext

SUBAGENT_DENY_PRIVATE = [
    FilesystemPermission(
        operations=["read", "write"],
        paths=["/private/**", "/eval/**"],
        mode="deny",
    ),
]

PRIVATE_ACCESS_NOTE = (
    "\n\n禁止访问 `private/` 与 `eval/` 目录及其内容；这些目录仅用于主编排器离线评测，"
    "不得读取、引用或向其他 Agent 传递其中数据。"
)

BOB_WORKSPACE_SCHEMA_NOTE = (
    "\n\n聊天回复可以简洁；如需写入 `coding/{id}.json`，内容必须是单个 JSON 对象，字段为 "
    "`id`、`content`、`content_with_labels`、`items`，其中 `items` 的元素包含 "
    "`name`、`evidence`、`normalized_label`、`reason`。"
)

CODEBOOK_WORKSPACE_SCHEMA_NOTE = (
    "\n\n聊天回复可以简洁；如需写入 `codebook/dimensions.json` 或批次快照，文件内容必须是"
    "维度对象数组，每个对象包含 `name`、`items`、`definition`；不要写成带 `dimensions` 包装层的对象。"
)


def build_subagents(prompt_ctx: PromptContext | None = None) -> list[dict]:
    ctx = prompt_ctx or PromptContext.load()
    return [
        {
            "name": "bob-coder",
            "description": (
                "对单条中文评论做开放式编码，提取体验维度并写入 coding/{id}.json。"
                "适合检查单条编码质量或补编码。"
            ),
            "system_prompt": (
                ctx.bob_template
                + "\n\n你是子 Agent。读取 corpus/raw.jsonl 与 coding/ 文件，"
                "必要时用 write_file 写入 coding/{id}.json。"
                + BOB_WORKSPACE_SCHEMA_NOTE
                + PRIVATE_ACCESS_NOTE
            ),
            "permissions": SUBAGENT_DENY_PRIVATE,
        },
        {
            "name": "alice-codebook",
            "description": (
                "基于 codebook 样本的 Bob 结果归纳初始 dimensions，写入 codebook/dimensions.json。"
            ),
            "system_prompt": (
                ctx.alice_template
                + "\n\n你是子 Agent。从 coding/ 中读取 partition.codebook_text_ids 对应文件，"
                "归纳后写入 codebook/dimensions.json。"
                + CODEBOOK_WORKSPACE_SCHEMA_NOTE
                + PRIVATE_ACCESS_NOTE
            ),
            "permissions": SUBAGENT_DENY_PRIVATE,
        },
        {
            "name": "kevin-updater",
            "description": (
                "在现有 codebook/dimensions.json 基础上做保守增量更新，并写 batch 快照。"
            ),
            "system_prompt": (
                ctx.kevin_template
                + "\n\n你是子 Agent。读取 codebook/dimensions.json 与 Kevin 批次对应 coding 文件，"
                "输出完整更新版 dimensions。"
                + CODEBOOK_WORKSPACE_SCHEMA_NOTE
                + PRIVATE_ACCESS_NOTE
            ),
            "permissions": SUBAGENT_DENY_PRIVATE,
        },
    ]
