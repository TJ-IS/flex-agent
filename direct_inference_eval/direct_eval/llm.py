from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        ...


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class OpenAIChatClient:
    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 300.0,
        max_retries: int = 5,
        seed: int | None = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is required for direct inference.") from exc

        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.seed = seed if seed is not None else _env_seed()
        self.client = OpenAI(
            api_key=resolved_api_key,
            base_url=base_url or os.getenv("OPENAI_BASE_URL") or None,
            timeout=timeout,
            max_retries=max_retries,
        )

    def complete(self, prompt: str) -> str:
        kwargs = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "You are a careful qualitative coding assistant."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        if self.seed is not None:
            kwargs["seed"] = self.seed
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("LLM returned empty content.")
        return content


def _env_seed() -> int | None:
    raw = os.getenv("OPENAI_SEED", "42").strip()
    return int(raw) if raw else None
