"""Aggregate workspace-level axial eval results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flex_agent.eval.aggregate import _aggregate_rows

AXIAL_GLOBAL_RESULT_NAME = "global.json"
AXIAL_GLOBAL_TEXT_ID = 0


def axial_global_result_path(eval_dir: Path) -> Path:
    return eval_dir / AXIAL_GLOBAL_RESULT_NAME


def _section_complete(section: dict[str, Any] | None) -> bool:
    if not isinstance(section, dict):
        return False
    status = section.get("status")
    if status is None:
        return "nums_both" in section
    return status == "complete"


def load_axial_global_payload(eval_dir: Path) -> dict[str, Any] | None:
    path = axial_global_result_path(eval_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def aggregate_axial_global_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Build keyword/semantic summary blocks from a workspace-level global.json."""
    keyword = payload.get("keyword")
    semantic = payload.get("semantic")
    keyword_rows = [keyword] if _section_complete(keyword) else []
    semantic_rows = [semantic] if _section_complete(semantic) else []
    return {
        "item_level_keyword": _aggregate_rows(keyword_rows) if keyword_rows else None,
        "item_level_semantic": _aggregate_rows(semantic_rows) if semantic_rows else None,
        "keyword_complete": len(keyword_rows),
        "semantic_complete": len(semantic_rows),
    }
