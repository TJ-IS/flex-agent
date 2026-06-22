from __future__ import annotations

from collections.abc import Iterable

from flex_agent.coding.quality import QualityWarnings, review_dimensions
from flex_agent.models import DimensionDetail, FinishedTextItem
from flex_agent.workspace import Workspace


def _chunked(ids: list[int], size: int) -> list[list[int]]:
    chunk_size = max(1, size)
    return [ids[idx : idx + chunk_size] for idx in range(0, len(ids), chunk_size)]


def decode_workspace_status(workspace: Workspace) -> dict:
    return workspace.status()


def monitor_update_batches(
    update_text_ids: Iterable[int],
    finished_text_ids: set[int],
    batch_size: int,
) -> list[list[int]]:
    source_ids = [text_id for text_id in update_text_ids if text_id in finished_text_ids]
    return _chunked(source_ids, batch_size)


def encode_coding_result(workspace: Workspace, finished: FinishedTextItem) -> None:
    workspace.save_coding(finished)


def encode_dimensions(workspace: Workspace, dimensions: list[DimensionDetail]) -> None:
    workspace.save_dimensions(dimensions)


def encode_codebook_batch(
    workspace: Workspace,
    batch_index: int,
    dimensions: list[DimensionDetail],
) -> None:
    workspace.save_codebook_batch(batch_index, dimensions)


def verify_dimensions(
    dimensions: list[DimensionDetail],
    finished_texts: list[FinishedTextItem] | None,
) -> tuple[list[DimensionDetail], QualityWarnings]:
    return review_dimensions(dimensions, finished_texts)
