from __future__ import annotations

import json
import logging
import re

from openai import AsyncOpenAI
from pydantic import BaseModel

from open_paxel.config import Settings

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = _JSON_FENCE.sub("", cleaned).strip()
    return cleaned


def _json_schema_messages(messages: list[dict[str, str]], response_model: type[BaseModel]) -> list[dict[str, str]]:
    schema = json.dumps(response_model.model_json_schema(), indent=2)
    schema_hint = (
        "Respond with valid JSON only (no markdown fences) matching this schema:\n"
        f"{schema}"
    )
    out = [dict(m) for m in messages]
    if out and out[0].get("role") == "system":
        out[0] = {
            "role": "system",
            "content": f"{out[0]['content']}\n\n{schema_hint}",
        }
    else:
        out.insert(0, {"role": "system", "content": schema_hint})
    return out


async def _parse_with_json_fallback(
    client: AsyncOpenAI,
    *,
    model: str,
    messages: list[dict[str, str]],
    response_model: type[BaseModel],
    max_tokens: int | None = None,
) -> BaseModel | None:
    schema_messages = _json_schema_messages(messages, response_model)
    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=schema_messages,
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
        )
    except Exception:
        completion = await client.chat.completions.create(
            model=model,
            messages=schema_messages,
            max_tokens=max_tokens,
        )

    content = completion.choices[0].message.content or ""
    if not content.strip():
        return None
    return response_model.model_validate_json(_strip_json_fence(content))


async def parse_structured_completion(
    client: AsyncOpenAI,
    *,
    settings: Settings,
    model: str,
    messages: list[dict[str, str]],
    response_model: type[BaseModel],
) -> BaseModel | None:
    """Structured LLM output via OpenAI parse API or JSON fallback."""
    provider = settings.llm_provider.lower()
    max_tokens = settings.max_output_tokens

    if provider == "openai":
        completion = await client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=response_model,
            max_tokens=max_tokens,
        )
        return completion.choices[0].message.parsed

    if provider == "openrouter":
        try:
            completion = await client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=response_model,
                max_tokens=max_tokens,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is not None:
                return parsed
        except Exception:
            logger.debug("OpenRouter structured parse failed; falling back to JSON", exc_info=True)
        return await _parse_with_json_fallback(
            client,
            model=model,
            messages=messages,
            response_model=response_model,
            max_tokens=max_tokens,
        )

    return await _parse_with_json_fallback(
        client,
        model=model,
        messages=messages,
        response_model=response_model,
        max_tokens=max_tokens,
    )
