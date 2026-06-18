# CODE: COnstruct Development Engine

## Quick start

```bash
cd flex-agent
uv sync
cp env.example .env
uv run flex-agent
```

Switch language, prompt set, or workspace category:

```bash
uv run flex-agent --language en
uv run flex-agent --prompts-dir baseline
uv run flex-agent --workspace exp-v2
uv run flex-agent --prompts-dir exp-v2 --workspace exp-v2
```