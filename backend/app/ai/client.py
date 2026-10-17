"""Shared Gemini client and a structured-output call that returns a validated Pydantic model."""

import time
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.ai import usage
from app.config import get_settings

T = TypeVar("T", bound=BaseModel)

_client: genai.Client | None = None


class AIError(RuntimeError):
    """The model returned nothing usable (blocked, truncated, or not matching the schema)."""


def client() -> genai.Client:
    global _client
    if _client is None:
        key = get_settings().gemini_api_key
        _client = genai.Client(api_key=key.get_secret_value() if key else None)
    return _client


async def generate(
    *,
    purpose: str,
    model: str,
    system: str,
    parts: list[types.Part],
    schema: type[T],
    thinking: str,
) -> T:
    started = time.perf_counter()
    response = None
    error = None
    try:
        response = await client().aio.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                thinking_config=types.ThinkingConfig(thinking_level=thinking),
                max_output_tokens=get_settings().max_output_tokens,
            ),
        )
        return _parse(model, schema, response)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        raise
    finally:
        await usage.record(
            purpose=purpose,
            model=model,
            duration_ms=round((time.perf_counter() - started) * 1000),
            usage=response.usage_metadata if response is not None else None,
            error=error,
        )


def _parse(model: str, schema: type[T], response: types.GenerateContentResponse) -> T:
    if not response.candidates:
        raise AIError(f"no response from {model} (prompt feedback: {response.prompt_feedback})")
    reason = response.candidates[0].finish_reason
    if reason == types.FinishReason.MAX_TOKENS:
        raise AIError(f"{model} hit max_output_tokens; output would be truncated")
    if reason not in (None, types.FinishReason.STOP):
        raise AIError(f"{model} stopped early: {reason}")

    if isinstance(response.parsed, schema):
        return response.parsed
    try:
        return schema.model_validate_json(response.text or "")
    except ValueError as e:
        raise AIError(f"{model} output does not match {schema.__name__}: {e}") from e
