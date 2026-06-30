from __future__ import annotations

import json
from typing import Literal


FileKind = Literal["corpus", "corpus_with_labels"]


def _parse_jsonl_lines(content: str) -> list[tuple[int, dict]]:
    records: list[tuple[int, dict]] = []
    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Line {line_no}: invalid JSON ({exc.msg}).") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Line {line_no}: each row must be a JSON object.")
        records.append((line_no, record))
    if not records:
        raise ValueError("File must contain at least one non-empty JSONL row.")
    return records


def validate_corpus_jsonl(content: str) -> None:
    records = _parse_jsonl_lines(content)
    for line_no, record in records:
        if record.get("id") is None:
            raise ValueError(f"Line {line_no}: missing required field 'id'.")
        text = record.get("comments") or record.get("content") or record.get("text")
        if not str(text or "").strip():
            raise ValueError(
                f"Line {line_no}: missing text field ('comments', 'content', or 'text')."
            )


def validate_corpus_with_labels_jsonl(content: str) -> None:
    records = _parse_jsonl_lines(content)
    for line_no, record in records:
        if record.get("id") is None:
            raise ValueError(f"Line {line_no}: missing required field 'id'.")
        text = record.get("comments") or record.get("content") or record.get("text")
        if not str(text or "").strip():
            raise ValueError(
                f"Line {line_no}: missing text field ('comments', 'content', or 'text')."
            )
        if "human_items" not in record and "codes" not in record:
            raise ValueError(
                f"Line {line_no}: missing human annotation field ('human_items' or 'codes')."
            )


def validate_jsonl(content: str, kind: FileKind) -> None:
    if kind == "corpus":
        validate_corpus_jsonl(content)
        return
    validate_corpus_with_labels_jsonl(content)
