"""LLM client for grounded generation via OpenAI-compatible API."""
from openai import OpenAI
from app import config


_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=config.LLM_BASE_URL,
            api_key=config.LLM_API_KEY,
        )
    return _client


def generate(prompt: str, system: str = "You are a precise code analysis assistant. Answer only from provided evidence. If evidence is insufficient, say 'insufficient evidence'.", max_tokens: int = 2048, temperature: float = 0.1) -> str:
    """Generate a response using the configured LLM."""
    client = get_client()
    response = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""
