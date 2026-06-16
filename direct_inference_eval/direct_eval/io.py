from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from direct_eval.constants import normalize_category, normalize_dimension
from direct_eval.schemas import HumanRecord, PredictionItem, PredictionRecord


def _active_human_items(record: dict[str, Any]) -> tuple[dict[str, int], set[str]]:
    dimensions: dict[str, int] = {}
    categories: set[str] = set()

    if isinstance(record.get("human_items"), list):
        for item in record["human_items"]:
            value = int(item.get("value", 1) or 0)
            if value == 0:
                continue
            dim = normalize_dimension(str(item.get("dimension", "")).strip())
            category = normalize_category(str(item.get("category", "")).strip())
            if dim:
                dimensions[dim] = value
            if category:
                categories.add(category)
        return dimensions, categories

    for code_val in record.get("codes", {}).values():
        value = int(code_val.get("value", 0) or 0)
        if value == 0:
            continue
        dim = normalize_dimension(str(code_val.get("dimension", "")).strip())
        category = normalize_category(str(code_val.get("category", "")).strip())
        if dim:
            dimensions[dim] = value
        if category:
            categories.add(category)
    return dimensions, categories


def load_human_records(path: Path, *, limit: int | None = None) -> list[HumanRecord]:
    records: list[HumanRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            text_id = int(raw.get("id") or len(records) + 1)
            content = str(raw.get("comments") or raw.get("content") or "").strip()
            if not content:
                continue
            human_dimensions, human_categories = _active_human_items(raw)
            records.append(
                HumanRecord(
                    text_id=text_id,
                    content=content,
                    human_dimensions=human_dimensions,
                    human_categories=human_categories,
                    raw=raw,
                )
            )
            if limit is not None and len(records) >= limit:
                break
    return records


def prediction_from_dict(payload: dict[str, Any]) -> PredictionRecord:
    items: list[PredictionItem] = []
    seen: set[tuple[str, str, str]] = set()
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        value = _parse_value(item.get("value", 1))
        if value == 0:
            continue
        dimension = normalize_dimension(str(item.get("dimension") or "").strip())
        category = normalize_category(str(item.get("category") or "").strip())
        if not dimension and not category:
            continue
        evidence = str(item.get("evidence") or "").strip()
        key = (dimension, category, evidence)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            PredictionItem(
                evidence=evidence,
                dimension=dimension,
                category=category,
                value=value,
                reason=str(item.get("reason") or "").strip(),
            )
        )
    return PredictionRecord(text_id=int(payload["text_id"]), items=items)


def write_predictions_jsonl(path: Path, predictions: dict[int, PredictionRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for text_id in sorted(predictions):
            handle.write(json.dumps(predictions[text_id].as_dict(), ensure_ascii=False) + "
")


def load_predictions_jsonl(path: Path) -> dict[int, PredictionRecord]:
    predictions: dict[int, PredictionRecord] = {}
    if not path.exists():
        return predictions
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = prediction_from_dict(json.loads(line))
            predictions[record.text_id] = record
    return predictions


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_value(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return value if value in {-1, 0, 1} else 1
    text = str(value or "").strip()
    if text in {"-1", "negative", "负面", "消极"}:
        return -1
    if text in {"0", "neutral", "中性", "无"}:
        return 0
    return 1
