# CODE: COnstruct Development Engine

CODE is a Deep Agents based construct-development harness. The implementation uses
OpenCoding, Inducing, and AxialCoding roles over a persistent workspace while keeping
`agent` as the local entrypoint.

## Quick start

```bash
cd flex-agent
uv sync
cp env.example .env
uv run agent
```

Switch language, prompt set, or workspace category:

```bash
uv run agent --language en
uv run agent --prompts-dir baseline
uv run agent --workspace exp-v2
uv run agent --prompts-dir exp-v2 --workspace exp-v2
uv run agent --debug
```
