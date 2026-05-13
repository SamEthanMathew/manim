"""LLM client wrapper.

Routes calls to OpenAI or Anthropic based on the user's preferred_model.
All calls use the user's BYOK key — never our server-side keys for user jobs.

Two public functions:
  - text_completion: returns raw string output (for codegen)
  - structured_completion: validates response against a Pydantic schema,
    retries with validation errors echoed back into the prompt
"""
from __future__ import annotations

import json
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from workers.lib.errors import LLMRateLimitError, PipelineError

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


async def text_completion(*, ctx, system: str, user: str, stop: list[str] | None = None) -> str:
    """Returns plain text. Used for codegen where output is a code string."""
    model = ctx.user_keys.preferred_model
    if model.startswith("gpt"):
        return await _openai_text(ctx.user_keys.openai, model, system, user, stop)
    if model.startswith("claude"):
        return await _anthropic_text(ctx.user_keys.anthropic, model, system, user, stop)
    raise PipelineError(f"Unknown model: {model}")


async def structured_completion(
    *,
    ctx,
    system: str,
    user: str,
    schema: type[T],
    max_attempts: int = 3,
) -> T:
    """Returns a validated Pydantic object. Retries with validation feedback on failure."""
    last_error: str | None = None

    for attempt in range(1, max_attempts + 1):
        # On retry, append the prior validation error to the prompt.
        full_user = user if attempt == 1 else (
            f"{user}\n\n--- PRIOR VALIDATION ERROR ---\n{last_error}\n\n"
            "Return ONLY valid JSON matching the required schema."
        )

        text = await text_completion(ctx=ctx, system=system + "\n\nRespond ONLY with JSON.",
                                     user=full_user, stop=None)
        text = _strip_code_fences(text)

        try:
            data = json.loads(text)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = str(e)[:1500]
            log.warning("structured_completion attempt %d failed: %s", attempt, last_error)

    raise PipelineError(
        f"structured_completion failed after {max_attempts} attempts: {last_error}",
    )


# ─── Provider implementations ────────────────────────────────────────────────


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
async def _openai_text(api_key: str | None, model: str, system: str,
                       user: str, stop: list[str] | None) -> str:
    if not api_key:
        raise PipelineError("OpenAI API key missing")
    from openai import AsyncOpenAI, RateLimitError

    client = AsyncOpenAI(api_key=api_key)
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.5,
            max_tokens=4000,
            stop=stop,
        )
    except RateLimitError as e:
        raise LLMRateLimitError(f"OpenAI rate limit: {e}") from e

    return resp.choices[0].message.content or ""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
async def _anthropic_text(api_key: str | None, model: str, system: str,
                          user: str, stop: list[str] | None) -> str:
    if not api_key:
        raise PipelineError("Anthropic API key missing")
    from anthropic import AsyncAnthropic, RateLimitError

    client = AsyncAnthropic(api_key=api_key)
    try:
        resp = await client.messages.create(
            model=model,
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=4000,
            temperature=0.5,
            stop_sequences=stop,
        )
    except RateLimitError as e:
        raise LLMRateLimitError(f"Anthropic rate limit: {e}") from e

    parts = [b.text for b in resp.content if hasattr(b, "text")]
    return "".join(parts)


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = "\n".join(s.splitlines()[1:])
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()
