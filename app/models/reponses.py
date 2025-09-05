import os
from typing import Optional
from openai import OpenAI

# Optional: set via env to change models without code changes
# e.g. OPENAI_MODEL=gpt-4o-mini
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_client: Optional[OpenAI] = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        # Uses OPENAI_API_KEY from environment
        _client = OpenAI()
    return _client

def get_ai_response(prompt: str) -> str:
    """
    Get an assistant reply using OpenAI's v1 Chat Completions API.
    Requires OPENAI_API_KEY to be set in your environment.
    """
    client = _get_client()
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful AI character."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # Return a friendly message instead of crashing the app
        return f"Sorry, I couldn't get a response right now. ({e.__class__.__name__})"