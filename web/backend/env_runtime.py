from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from flex_agent.config import _build_llm_cached
from flex_agent.workspace import Workspace

EnvMode = Literal["env", "byok"]

ENV_KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "OPENAI_MODEL_PRO",
)

VALID_PROMPT_SETS = frozenset(
    {
        "baseline",
        "baseline_en",
        "baseline_oneshot",
        "baseline_fewshot",
        "baseline_oneshot_en",
        "baseline_fewshot_en",
    }
)

DEFAULT_ENV_JSON: dict[str, Any] = {"mode": "env", "overrides": {}}


def env_json_path(workspace: Workspace) -> Path:
    return workspace.meta_dir / "env.json"


def workspace_prompts_dir(workspace: Workspace) -> Path:
    return workspace.root / "prompts"


def task_background_path(workspace: Workspace) -> Path:
    return workspace_prompts_dir(workspace) / "task_background.md"


def load_env_json(workspace: Workspace) -> dict[str, Any]:
    path = env_json_path(workspace)
    if not path.exists():
        return dict(DEFAULT_ENV_JSON)
    raw = json.loads(path.read_text(encoding="utf-8"))
    mode = raw.get("mode", "env")
    if mode not in {"env", "byok"}:
        mode = "env"
    overrides = raw.get("overrides") or {}
    if not isinstance(overrides, dict):
        overrides = {}
    return {
        "mode": mode,
        "overrides": {k: str(v) for k, v in overrides.items() if k in ENV_KEYS and v},
    }


def save_env_json(workspace: Workspace, env_json: dict[str, Any]) -> None:
    workspace.ensure_layout()
    payload = {
        "mode": env_json.get("mode", "env"),
        "overrides": {
            k: str(v)
            for k, v in (env_json.get("overrides") or {}).items()
            if k in ENV_KEYS and v
        },
    }
    env_json_path(workspace).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def infer_prompt_set(workspace: Workspace, meta_prompts_dir: str | None = None) -> str:
    prompts = workspace_prompts_dir(workspace)
    if prompts.exists():
        marker = prompts / ".prompt_set"
        if marker.exists():
            name = marker.read_text(encoding="utf-8").strip()
            if name in VALID_PROMPT_SETS:
                return name
    if meta_prompts_dir:
        label = meta_prompts_dir.replace("\\", "/").strip("/")
        for candidate in VALID_PROMPT_SETS:
            if label.endswith(candidate) or label == candidate:
                return candidate
    return "baseline"


def apply_workspace_env(env_json: dict[str, Any]) -> dict[str, Any]:
    """Apply workspace env overrides; return snapshot for restore_env."""
    snapshot: dict[str, Any] = {}
    for key in ENV_KEYS:
        if key in os.environ:
            snapshot[key] = os.environ[key]
        else:
            snapshot[key] = None

    mode = env_json.get("mode", "env")
    overrides = env_json.get("overrides") or {}
    if mode == "byok" and isinstance(overrides, dict):
        for key, value in overrides.items():
            if key in ENV_KEYS and value:
                os.environ[key] = str(value)

    return snapshot


def restore_env(snapshot: dict[str, Any]) -> None:
    for key in ENV_KEYS:
        original = snapshot.get(key)
        if original is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = str(original)


def clear_llm_cache() -> None:
    _build_llm_cached.cache_clear()


def effective_env_overrides(env_json: dict[str, Any]) -> dict[str, str]:
    """Return env vars to apply when building runtime for a workspace."""
    mode = env_json.get("mode", "env")
    if mode != "byok":
        return {}
    overrides = env_json.get("overrides") or {}
    if not isinstance(overrides, dict):
        return {}
    return {k: str(v) for k, v in overrides.items() if k in ENV_KEYS and v}


def validate_create_params(
    *,
    prompt_set: str,
    mode: str,
    overrides: dict[str, str],
) -> None:
    if prompt_set not in VALID_PROMPT_SETS:
        allowed = ", ".join(sorted(VALID_PROMPT_SETS))
        raise ValueError(f"Invalid prompt_set {prompt_set!r}; expected one of: {allowed}")
    if mode not in {"env", "byok"}:
        raise ValueError(f"Invalid mode {mode!r}; expected 'env' or 'byok'.")
    if mode == "byok" and not str(overrides.get("OPENAI_API_KEY", "")).strip():
        raise ValueError("BYOK mode requires OPENAI_API_KEY.")
