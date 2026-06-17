from __future__ import annotations

import json
import re
from typing import Any

from .io import prediction_from_dict
from .schemas import PredictionRecord


def extract_json_payload(raw_text: str) -> Any:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    object_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if object_match:
        return json.loads(object_match.group(0))
    array_match = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
    if array_match:
        return json.loads(array_match.group(0))
    raise ValueError("Model response does not contain valid JSON.")


def parse_prediction_response(raw_text: str, *, expected_ids: set[int] | None = None) -> list[PredictionRecord]:
    payload = extract_json_payload(raw_text)
    if isinstance(payload, dict):
        rows = payload.get("records") or payload.get("texts") or payload.get("rows")
        if rows is None and "text_id" in payload:
            rows = [payload]
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = None
    if not isinstance(rows, list):
        raise ValueError("Prediction JSON must contain a records/texts/rows array.")

    predictions: list[PredictionRecord] = []
    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, dict) or "text_id" not in row:
            continue
        record = prediction_from_dict(row)
        if expected_ids is not None and record.text_id not in expected_ids:
            continue
        if record.text_id in seen:
            continue
        predictions.append(record)
        seen.add(record.text_id)
    return predictions
