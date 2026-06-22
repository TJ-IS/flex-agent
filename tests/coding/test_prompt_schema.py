from __future__ import annotations

import json
import unittest

from flex_agent.coding.agents import (
    AliceDimensionDetail,
    AxialCodingDimensionDetail,
    BobItemDetail,
    BobOutput,
    InductionDimensionDetail,
    KevinDimensionDetail,
    OpenCodingItemDetail,
    OpenCodingOutput,
    get_agent_schema_models,
)


class AgentStructuredOutputSchemaTests(unittest.TestCase):
    def test_open_coding_schema_uses_baseline_fragment_terms(self) -> None:
        schema_text = json.dumps(
            {
                "open_coding_item": OpenCodingItemDetail.model_json_schema(),
                "open_coding_output": OpenCodingOutput.model_json_schema(),
            },
            ensure_ascii=False,
        )

        self.assertNotIn("ReAct", schema_text)
        self.assertNotIn("对提取短语", schema_text)
        self.assertIn("对提取片段", schema_text)
        self.assertIn("<p>...</p>", schema_text)
        self.assertIn("不改写原句", schema_text)

    def test_dimension_item_schema_matches_baseline_inputs(self) -> None:
        induction_dimension_items = InductionDimensionDetail.model_fields["items"].description or ""
        axial_coding_dimension_items = AxialCodingDimensionDetail.model_fields["items"].description or ""

        self.assertIn("items_details.label", induction_dimension_items)
        self.assertIn("items_pool", induction_dimension_items)
        self.assertNotIn("必须来自 items_pool。", induction_dimension_items)

        self.assertIn("已有代码本条目", axial_coding_dimension_items)
        self.assertIn("当前批次输入", axial_coding_dimension_items)
        self.assertNotIn("传入的 items_pool 或已有维度", axial_coding_dimension_items)

    def test_legacy_schema_aliases_remain_available(self) -> None:
        self.assertIs(BobItemDetail, OpenCodingItemDetail)
        self.assertIs(BobOutput, OpenCodingOutput)
        self.assertIs(AliceDimensionDetail, InductionDimensionDetail)
        self.assertIs(KevinDimensionDetail, AxialCodingDimensionDetail)

    def test_english_runtime_schema_uses_english_descriptions(self) -> None:
        schemas = get_agent_schema_models("en")
        schema_text = json.dumps(
            {
                "open_coding_item": schemas.open_coding_item.model_json_schema(),
                "open_coding_output": schemas.open_coding_output.model_json_schema(),
                "induction_dimension": schemas.induction_dimension.model_json_schema(),
                "axial_coding_dimension": schemas.axial_coding_dimension.model_json_schema(),
            },
            ensure_ascii=False,
        )

        self.assertIn("concise English summary", schema_text)
        self.assertIn("English dimension", schema_text)
        self.assertIn("<p>...</p>", schema_text)
        self.assertNotIn("中文", schema_text)
        self.assertNotIn("维度名称", schema_text)


if __name__ == "__main__":
    unittest.main()
