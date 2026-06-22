from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Type, TypeVar, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from flex_agent.config import trace_invoke_config

ModelT = TypeVar("ModelT", bound=BaseModel)

STRUCTURED_OUTPUT_METHODS = ("json_schema", "json_mode", "function_calling")


def extract_json_object(raw_text: str) -> str:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        return match.group(0)
    raise ValueError("Model response does not contain a JSON object.")


def raw_result_to_content(result: Any) -> tuple[str, BaseMessage | None]:
    if isinstance(result, BaseMessage):
        content = result.content
        if isinstance(content, str):
            return content, result
        return json.dumps(content, ensure_ascii=False, default=str), result
    if isinstance(result, str):
        return result, None
    return str(result), None


def coerce_structured_result(result: Any, schema: Type[ModelT]) -> ModelT:
    if isinstance(result, schema):
        return cast(ModelT, result)
    if isinstance(result, BaseModel):
        return cast(ModelT, schema.model_validate(result.model_dump()))
    return cast(ModelT, schema.model_validate(result))


async def _ainvoke_chain(chain: Any, payload: dict, invoke_config: dict[str, object]) -> Any:
    ainvoke = getattr(chain, "ainvoke", None)
    if callable(ainvoke):
        if invoke_config:
            try:
                return await ainvoke(payload, config=invoke_config)
            except TypeError as exc:
                if "config" not in str(exc):
                    raise
                return await ainvoke(payload)
        return await ainvoke(payload)
    if invoke_config:
        try:
            return await asyncio.to_thread(lambda: chain.invoke(payload, config=invoke_config))
        except TypeError as exc:
            if "config" not in str(exc):
                raise
            return await asyncio.to_thread(chain.invoke, payload)
    return await asyncio.to_thread(chain.invoke, payload)


async def ainvoke_structured(
    llm: BaseChatModel,
    prompt: ChatPromptTemplate,
    schema: Type[ModelT],
    payload: dict,
    *,
    component: str | None = None,
) -> ModelT:
    invoke_config = trace_invoke_config(component)
    last_exc: Exception | None = None

    for method in STRUCTURED_OUTPUT_METHODS:
        try:
            structured_llm = llm.with_structured_output(schema, method=method)
            chain = prompt | structured_llm
            result = await _ainvoke_chain(chain, payload, invoke_config)
            return coerce_structured_result(result, schema)
        except Exception as exc:
            last_exc = exc
            continue

    fallback_chain = prompt | llm
    try:
        raw_result = await _ainvoke_chain(fallback_chain, payload, invoke_config)
        raw_content, _ = raw_result_to_content(raw_result)
        json_str = extract_json_object(raw_content)
        return schema.model_validate(json.loads(json_str))
    except Exception as fallback_exc:
        raise RuntimeError(
            f"Structured output parsing failed for {schema.__name__}: {last_exc}; "
            f"fallback: {fallback_exc}"
        ) from fallback_exc
