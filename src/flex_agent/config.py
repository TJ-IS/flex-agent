from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from langchain_openai import ChatOpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKSPACE = PROJECT_ROOT / "workspace"


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


def build_llm(
    model_name: str,
    *,
    timeout: float = 300.0,
    max_retries: int = 5,
    seed: int | None = None,
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
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)
