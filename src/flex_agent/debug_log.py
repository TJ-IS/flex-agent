from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from time import time
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEBUG_LOG_DIR = PROJECT_ROOT / ".cursor"
DEFAULT_DEBUG_LOG_PATH = DEFAULT_DEBUG_LOG_DIR / "flex-agent-debug.ndjson"
_ENV_DEBUG_LOG_PATH = os.getenv("FLEX_AGENT_DEBUG_LOG")
_DEBUG_LOG_PATH = Path(_ENV_DEBUG_LOG_PATH) if _ENV_DEBUG_LOG_PATH else DEFAULT_DEBUG_LOG_PATH
_DEBUG_SESSION_ID = os.getenv("FLEX_AGENT_DEBUG_SESSION_ID", "local")
_DEBUG_RUN_ID = os.getenv("FLEX_AGENT_DEBUG_RUN_ID", "manual")
_DEBUG_ENABLED = os.getenv("FLEX_AGENT_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _timestamped_debug_log_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_DEBUG_LOG_DIR / f"flex-agent-debug-{timestamp}.ndjson"


def configure_debug_logging(
    *,
    enabled: bool,
    log_path: str | Path | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
) -> Path:
    global _DEBUG_ENABLED, _DEBUG_LOG_PATH, _DEBUG_SESSION_ID, _DEBUG_RUN_ID
    _DEBUG_ENABLED = enabled
    if log_path is not None:
        _DEBUG_LOG_PATH = Path(log_path)
    elif enabled and _ENV_DEBUG_LOG_PATH is None:
        _DEBUG_LOG_PATH = _timestamped_debug_log_path()
    if session_id is not None:
        _DEBUG_SESSION_ID = session_id
    if run_id is not None:
        _DEBUG_RUN_ID = run_id
    return _DEBUG_LOG_PATH


def debug_logging_enabled() -> bool:
    return _DEBUG_ENABLED


def debug_log_path() -> Path:
    return _DEBUG_LOG_PATH


def agent_debug_log(
    *,
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any],
) -> None:
    if not _DEBUG_ENABLED:
        return
    payload = {
        "sessionId": _DEBUG_SESSION_ID,
        "runId": _DEBUG_RUN_ID,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time() * 1000),
    }
    try:
        _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass
