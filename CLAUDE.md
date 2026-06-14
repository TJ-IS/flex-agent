# CLAUDE.md

flex-agent 是基于 deepagents 的开放式编码 Agent。编码状态持久化在 workspace 文件，不用 LangGraph State 存编码内容。

## Commands

```bash
uv sync
uv run flex-agent
uv run python -m unittest discover -s tests -v
```

## Architecture

```text
src/flex_agent/
├── cli.py, config.py          # 入口与配置
├── models/                    # Pydantic 数据结构
├── workspace/                 # 文件持久化（corpus/coding/codebook）
├── coding/                    # 开放式编码业务逻辑
│   ├── agents.py              # Bob / Alice / Kevin LLM 调用
│   ├── quality.py             # 编码结果规范化与 construct 审查
│   └── export.py              # gt-agent 兼容导出
├── orchestration/             # DeepAgent 编排层
│   ├── factory.py             # create_flex_agent() + CompositeBackend
│   ├── prompt.py              # 主编排器 system prompt
│   ├── subagents.py           # Bob/Alice/Kevin 子 Agent 定义
│   └── tools.py               # init/bob/alice/kevin/export 工具
└── ui/                        # 交互式 CLI 与事件解析
prompts/                       # Bob/Alice/Kevin prompt 模板
```

## Workflow SOP

1. `init_open_coding_run`
2. `batch_bob_code`
3. `run_alice_codebook`
4. `run_kevin_batches`
5. `export_result`

Legacy reference: `../gt-agent/`
