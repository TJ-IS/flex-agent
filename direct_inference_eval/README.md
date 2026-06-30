# Direct Inference Eval Baseline

这个目录是独立的 direct inference baseline：不接入 `Workspace`、TUI slash command，也不 import `flex_agent` 主包。它直接读取人工 benchmark JSONL，把大 batch 评论交给 LLM 一次性输出表格式 JSON，然后用同一类 C/P/R 指标评测 open 与 axial 结果。

## Run

```bash
uv run python direct_inference_eval/run.py \
  --input data/corpus_with_labels.jsonl \
  --output direct_inference_eval/runs/default \
  --batch-size 50 \
  --mode both \
  --resume
```

可选参数：

- `--mode open|axial|both`
- `--batch-size 50`
- `--limit 100`
- `--model <model-name>`
- `--resume`
- `--no-llm-semantic`

默认读取 `.env` 中的 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL` 和 `OPENAI_SEED`。

## Outputs

- `predictions/batch_*.json`：每个 direct inference batch 的原始响应和解析结果。
- `predictions/records.jsonl`：规范化后的逐文本 direct 预测。
- `eval/open/{id}.json`、`eval/open/summary.json`、`eval/open/report.txt`：open coding C/P/R。
- `eval/axial/global.json`、`eval/axial/summary.json`、`eval/axial/report.txt`：workspace 级 axial C/P/R。

## Metrics

- `Consistency = intersection / union`
- `Precision = intersection / agent`
- `Recall = intersection / human`

Open eval 比较逐文本 human active dimensions 与 direct predicted dimensions。Axial eval 汇总 direct predicted categories，在 workspace 级别与固定 human category taxonomy 做严格一对一比较。
