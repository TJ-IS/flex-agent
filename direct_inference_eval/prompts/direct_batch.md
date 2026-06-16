# Direct Inference Batch Coding

你正在分析中文用户关于沉浸式元宇宙/VR 游戏体验价值的评论。

请对下面一批评论直接做开放式编码，并输出一个表格式 JSON。只提取直接描述体验价值的片段，例如服务、设备、画面、声音、互动、玩法、价格、位置、环境、舒适度、情绪感受、推荐或再访意愿。

要求：

1. 每条评论可以有 0 个或多个 `items`。
2. 每个 item 只分配一个简洁中文 `dimension`，并给出一个更高层级的 `category`。
3. `dimension` 和 `category` 都应可跨评论复用，不要机械复制原句。
4. `value` 只能是 `1` 或 `-1`，分别表示正向或负向体验价值。
5. 只输出 JSON，不要输出 Markdown、解释或额外文字。

输出 JSON schema：

```json
{
  "records": [
    {
      "text_id": 1,
      "items": [
        {
          "evidence": "原文片段",
          "dimension": "简洁中文维度",
          "category": "更高层级类别",
          "value": 1,
          "reason": "一句简短判断依据"
        }
      ]
    }
  ]
}
```

输入评论 JSON：

{records_json}
