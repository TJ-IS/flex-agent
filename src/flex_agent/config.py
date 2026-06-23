from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from langchain_openai import ChatOpenAI

from flex_agent.i18n import Language, default_prompts_name


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_ROOT = PROJECT_ROOT / "prompts"
WORKSPACES_ROOT = PROJECT_ROOT / "workspaces"
DEFAULT_PROMPTS_DIR = PROMPTS_ROOT / "baseline"
DEFAULT_WORKSPACE = WORKSPACES_ROOT / "baseline"

REQUIRED_PROMPT_FILE_GROUPS = (
    ("construct_induction.md", "agent_alice.md"),
    ("open_coding.md", "agent_bob.md"),
    ("axial_refinement.md", "agent_kevin.md"),
    "grounded_theory_background.md",
    "task_background.md",
    "eval_text_alignment.md",
    "eval_dimension_name_alignment.md",
)
REQUIRED_PROMPT_FILES = tuple(
    requirement[0] if isinstance(requirement, tuple) else requirement
    for requirement in REQUIRED_PROMPT_FILE_GROUPS
)

_active_prompts_dir: Path = DEFAULT_PROMPTS_DIR
_active_workspace_dir: Path = DEFAULT_WORKSPACE


def path_label(path: Path, *, root: Path = PROJECT_ROOT) -> str:
    resolved = path.resolve()
    root_resolved = root.resolve()
    try:
        return resolved.relative_to(root_resolved).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_under_root(spec: str | Path, *, root: Path, prefix: str) -> Path:
    raw = Path(spec)
    if raw.is_absolute():
        return raw.resolve()

    text = str(spec).strip()
    if not text:
        raise ValueError("Path spec must not be empty.")

    candidate = (PROJECT_ROOT / text).resolve()
    if candidate.exists() or "/" in text or text.startswith(prefix):
        return candidate

    return (root / text).resolve()


def _validate_prompts_dir(path: Path) -> Path:
    if not path.is_dir():
        raise FileNotFoundError(f"Prompts directory not found: {path}")
    missing: list[str] = []
    for requirement in REQUIRED_PROMPT_FILE_GROUPS:
        if isinstance(requirement, tuple):
            if not any((path / name).is_file() for name in requirement):
                missing.append(" or ".join(requirement))
            continue
        if not (path / requirement).is_file():
            missing.append(requirement)
    if missing:
        raise FileNotFoundError(
            f"Prompts directory {path} is missing required files: {', '.join(missing)}"
        )
    return path


def default_prompts_dir(language: Language | str | None = None) -> Path:
    return (PROMPTS_ROOT / default_prompts_name(language)).resolve()


def resolve_prompts_dir(spec: str | Path | None = "baseline", *, language: Language | str | None = None) -> Path:
    if spec is None:
        return _validate_prompts_dir(default_prompts_dir(language))
    return _validate_prompts_dir(_resolve_under_root(spec, root=PROMPTS_ROOT, prefix="prompts/"))


def resolve_workspace_dir(spec: str | Path = "baseline") -> Path:
    return _resolve_under_root(spec, root=WORKSPACES_ROOT, prefix="workspaces/")


def set_prompts_dir(spec: str | Path | None, *, language: Language | str | None = None) -> Path:
    global _active_prompts_dir
    _active_prompts_dir = resolve_prompts_dir(spec, language=language)
    return _active_prompts_dir


def get_prompts_dir() -> Path:
    return _active_prompts_dir


def set_workspace_dir(spec: str | Path) -> Path:
    global _active_workspace_dir
    _active_workspace_dir = resolve_workspace_dir(spec)
    return _active_workspace_dir


def get_workspace_dir() -> Path:
    return _active_workspace_dir


def load_env_file(path: Path | None = None) -> None:
    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def warn_langsmith_tracing() -> None:
    """Hint when LangSmith credentials exist but tracing is off."""
    api_key = os.getenv("LANGSMITH_API_KEY", "").strip()
    if not api_key or api_key.startswith("<"):
        return
    tracing = os.getenv("LANGSMITH_TRACING", "").strip().lower()
    if tracing in {"true", "1", "yes", "on"}:
        return
    print(
        "Note: LANGSMITH_API_KEY is set but LANGSMITH_TRACING is not enabled. "
        "Set LANGSMITH_TRACING=true to send traces to LangSmith.",
        file=sys.stderr,
    )


def load_recursion_limit(default: int = 50) -> int:
    raw = os.getenv("FLEX_AGENT_RECURSION_LIMIT", str(default)).strip()
    try:
        limit = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"FLEX_AGENT_RECURSION_LIMIT must be an integer, got {raw!r}."
        ) from exc
    if limit < 1:
        raise ValueError("FLEX_AGENT_RECURSION_LIMIT must be at least 1.")
    return limit


@dataclass(frozen=True)
class ModelConfig:
    default_model: str
    pro_model: str
    timeout: float
    max_retries: int
    seed: int | None


def load_model_config(
    *,
    timeout: float = 300.0,
    max_retries: int = 5,
) -> ModelConfig:
    seed_raw = os.getenv("OPENAI_SEED", "42").strip()
    seed = int(seed_raw) if seed_raw else None
    return ModelConfig(
        default_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        pro_model=os.getenv("OPENAI_MODEL_PRO", "gpt-4o"),
        timeout=timeout,
        max_retries=max_retries,
        seed=seed,
    )


@lru_cache(maxsize=16)
def _build_llm_cached(
    model_name: str,
    timeout: float,
    max_retries: int,
    seed: int | None,
    base_url: str | None,
) -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    kwargs: dict = {
        "model": model_name,
        "temperature": 0,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "api_key": api_key,
        "timeout": timeout,
        "max_retries": max_retries,
    }
    if seed is not None:
        kwargs["seed"] = seed
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def build_llm(
    model_name: str,
    *,
    timeout: float = 300.0,
    max_retries: int = 5,
    seed: int | None = None,
) -> ChatOpenAI:
    if seed is None:
        seed_raw = os.getenv("OPENAI_SEED", "42").strip()
        seed = int(seed_raw) if seed_raw else None
    base_url = os.getenv("OPENAI_BASE_URL") or None
    if base_url:
        base_url = base_url.strip()
        # Automatically append '/v1' to OPENAI_BASE_URL if it's a custom proxy/endpoint
        # and doesn't end with '/v1' (ignoring trailing slashes).
        # This prevents the common 'AttributeError: str object has no attribute model_dump'
        # error caused by proxies returning HTML error/welcome pages (strings) instead of JSON.
        normalized = base_url.rstrip("/")
        if normalized and not normalized.endswith("/v1") and not normalized.endswith("/v1/"):
            # Check if it's a standard web URL (http/https)
            if normalized.startswith("http://") or normalized.startswith("https://"):
                old_base_url = base_url
                base_url = f"{normalized}/v1"
                print(
                    f"⚠️  [Warning] OPENAI_BASE_URL '{old_base_url}' does not end with '/v1'. "
                    f"Automatically appended '/v1' -> '{base_url}' to prevent LangChain parsing errors.",
                    file=sys.stderr,
                    flush=True,
                )
    return _build_llm_cached(model_name, timeout, max_retries, seed, base_url)


def trace_invoke_config(component: str | None = None) -> dict[str, object]:
    """LangSmith tags/metadata for LLM invocations (not for create_deep_agent model arg)."""
    if not component:
        return {}
    tracing = os.getenv("LANGSMITH_TRACING", "").strip().lower()
    if tracing not in {"true", "1", "yes", "on"}:
        return {}
    return {"tags": [component], "metadata": {"component": component}}


def merge_invoke_config(*configs: dict[str, object] | None) -> dict[str, object]:
    merged: dict[str, object] = {}
    for config in configs:
        if not config:
            continue
        for key, value in config.items():
            if key == "tags" and key in merged:
                merged[key] = [*merged[key], *value]  # type: ignore[list-item]
            elif key == "metadata" and key in merged:
                merged[key] = {**merged[key], **value}  # type: ignore[dict-item]
            else:
                merged[key] = value
    return merged
