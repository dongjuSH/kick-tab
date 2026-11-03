"""Gemini API (google-genai SDK) for the AI weekly TOP 5 (chat 04).

- The key is passed straight to the client from SecretStr when a request is made; the
  SDK's environment lookup (GEMINI_API_KEY/GOOGLE_API_KEY) is not relied on, and the key
  is never logged or included in an error.
- Structured output: the answer must match a Pydantic model's JSON schema
  (`response_json_schema`), then it is validated again here.
- One request per call: SDK retries are turned off because the selection has its own
  fixed retry slot (00:05 KST); the request timeout is in milliseconds.
- Free tier: inputs may be used to improve Google products, so callers send public match
  data only. Quota errors (429) and refusals are failures like any other.
"""

import logging

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, SecretStr, ValidationError

logger = logging.getLogger(__name__)


class LlmError(Exception):
    """Safe to store: codes and types only, never the key or the raw answer."""


def generate_structured[ModelT: BaseModel](
    prompt: str,
    schema: type[ModelT],
    *,
    model: str,
    api_key: SecretStr,
    timeout_seconds: float,
    temperature: float = 0.2,
) -> tuple[ModelT, dict]:
    """Return the validated answer and its raw JSON (kept with the attempt for review)."""
    key = api_key.get_secret_value()
    if not key:
        raise LlmError("GEMINI_API_KEY is not configured")
    options = types.HttpOptions(
        timeout=max(1_000, int(timeout_seconds * 1000)),
        retry_options=types.HttpRetryOptions(attempts=1),
    )
    try:
        with genai.Client(api_key=key, http_options=options) as client:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=schema.model_json_schema(),
                    temperature=temperature,
                ),
            )
    except errors.APIError as exc:
        raise LlmError(f"Gemini API error {exc.code} {exc.status or ''}".strip()) from None
    except Exception as exc:  # noqa: BLE001 - network/timeout errors from the SDK's transport
        raise LlmError(f"Gemini request failed: {type(exc).__name__}") from None
    text = response.text
    if not text:
        reason = None
        if response.candidates:
            reason = response.candidates[0].finish_reason
        raise LlmError(f"Gemini returned no answer (finish reason: {reason})")
    try:
        parsed = schema.model_validate_json(text)
    except ValidationError:
        raise LlmError("Gemini answer does not match the selection schema") from None
    logger.info("Gemini %s answered (%d chars)", model, len(text))
    return parsed, parsed.model_dump(mode="json")
