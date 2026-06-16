from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from direct_eval.io import prediction_from_dict, write_json
from direct_eval.llm import LLMClient
from direct_eval.parser import parse_prediction_response
from direct_eval.schemas import HumanRecord, PredictionRecord


def chunked(records: list[HumanRecord], size: int) -> list[list[HumanRecord]]:
    chunk_size = max(1, size)
    return [records[index : index + chunk_size] for index in range(0, len(records), chunk_size)]


def render_direct_prompt(prompt_template: str, records: list[HumanRecord]) -> str:
    prompt_records = [
        {
            "text_id": record.text_id,
            "content": record.content,
        }
        for record in records
    ]
    return prompt_template.replace(
        "{records_json}",
        json.dumps(prompt_records, ensure_ascii=False, indent=2),
    )


def run_direct_batches(
    records: list[HumanRecord],
    *,
    output_dir: Path,
    prompt_template: str,
    client: LLMClient,
    batch_size: int = 50,
    resume: bool = False,
) -> tuple[dict[int, PredictionRecord], list[dict[str, Any]]]:
    predictions: dict[int, PredictionRecord] = {}
    batch_reports: list[dict[str, Any]] = []
    prediction_dir = output_dir / "predictions"
    prediction_dir.mkdir(parents=True, exist_ok=True)

    for batch_index, batch in enumerate(chunked(records, batch_size), start=1):
        batch_path = prediction_dir / f"batch_{batch_index:04d}.json"
        if resume and batch_path.exists():
            saved = json.loads(batch_path.read_text(encoding="utf-8"))
            if saved.get("status") == "complete":
                parsed = parse_saved_records(saved.get("records") or [])
                for prediction in parsed:
                    predictions[prediction.text_id] = prediction
                batch_reports.append(_batch_report(batch_index, batch, "complete", parsed=len(parsed), skipped=True))
                continue

        expected_ids = {record.text_id for record in batch}
        prompt = render_direct_prompt(prompt_template, batch)
        try:
            raw_response = client.complete(prompt)
            parsed = parse_prediction_response(raw_response, expected_ids=expected_ids)
            payload = {
                "batch_index": batch_index,
                "status": "complete",
                "text_ids": sorted(expected_ids),
                "raw_response": raw_response,
                "records": [record.as_dict() for record in parsed],
            }
            write_json(batch_path, payload)
            for prediction in parsed:
                predictions[prediction.text_id] = prediction
            batch_reports.append(_batch_report(batch_index, batch, "complete", parsed=len(parsed)))
        except Exception as exc:
            payload = {
                "batch_index": batch_index,
                "status": "failed",
                "text_ids": sorted(expected_ids),
                "error": repr(exc),
            }
            write_json(batch_path, payload)
            batch_reports.append(_batch_report(batch_index, batch, "failed", error=repr(exc)))
            continue
    return predictions, batch_reports


def parse_saved_records(rows: list[dict[str, Any]]) -> list[PredictionRecord]:
    parsed: list[PredictionRecord] = []
    for row in rows:
        if isinstance(row, dict) and "text_id" in row:
            parsed.append(prediction_from_dict(row))
    return parsed


def _batch_report(
    batch_index: int,
    batch: list[HumanRecord],
    status: str,
    *,
    parsed: int = 0,
    skipped: bool = False,
    error: str | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "batch_index": batch_index,
        "status": status,
        "size": len(batch),
        "parsed": parsed,
        "skipped": skipped,
    }
    if error:
        report["error"] = error
    return report
