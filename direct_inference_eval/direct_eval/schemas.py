from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HumanRecord:
    text_id: int
    content: str
    human_dimensions: dict[str, int]
    human_categories: set[str]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PredictionItem:
    evidence: str
    dimension: str
    category: str
    value: int = 1
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence,
            "dimension": self.dimension,
            "category": self.category,
            "value": self.value,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PredictionRecord:
    text_id: int
    items: list[PredictionItem] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "text_id": self.text_id,
            "items": [item.as_dict() for item in self.items],
        }
