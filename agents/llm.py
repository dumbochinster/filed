"""One small interface over the model providers: send a prompt, get JSON back.

python -m agents.llm --list     show the models your key can use
python -m agents.llm --ping     make one real call to check the setup
"""

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv

RETRY_WAITS = [2, 5, 10, 20, 40]
DEFAULT_MODELS = {"gemini": "gemini-2.5-flash", "anthropic": "claude-sonnet-5-5"}


class LLMError(Exception):
    pass


def parse_json(text: str) -> dict:
    """Parse a model reply, tolerating a markdown code fence around it."""
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    return json.loads(fenced.group(1) if fenced else text)


class Client:
    """Shared behaviour: retry on rate limits, retry once on bad JSON, count tokens."""

    def __init__(self, model: str):
        self.model = model
        self.calls = 0
        self.tokens_in = 0
        self.tokens_out = 0

    def generate(self, system: str, prompt: str) -> tuple[str, int, int]:
        """Provider call. Returns (text, input tokens, output tokens)."""
        raise NotImplementedError

    def is_retryable(self, error: Exception) -> bool:
        return False

    def complete_json(self, system: str, prompt: str) -> dict:
        for attempt in range(2):
            text = self._generate_with_backoff(system, prompt)
            try:
                return parse_json(text)
            except ValueError as error:
                prompt += (
                    f"\n\nYour previous reply was not valid JSON ({error}). Reply with JSON only."
                )
        raise LLMError("the model did not return valid JSON twice in a row")

    def _generate_with_backoff(self, system: str, prompt: str) -> str:
        for wait in RETRY_WAITS + [None]:
            try:
                text, tokens_in, tokens_out = self.generate(system, prompt)
            except Exception as error:
                if wait is None or not self.is_retryable(error):
                    raise
                time.sleep(wait)
                continue
            self.calls += 1
            self.tokens_in += tokens_in
            self.tokens_out += tokens_out
            return text


class GeminiClient(Client):
    def __init__(self, model: str, api_key: str):
        from google import genai

        super().__init__(model)
        self.client = genai.Client(api_key=api_key)

    def generate(self, system, prompt):
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system, response_mime_type="application/json", temperature=0
        )
        reply = self.client.models.generate_content(
            model=self.model, contents=prompt, config=config
        )
        usage = reply.usage_metadata
        return reply.text or "", usage.prompt_token_count or 0, usage.candidates_token_count or 0

    def is_retryable(self, error):
        return getattr(error, "code", None) in (429, 500, 503)


class AnthropicClient(Client):
    def __init__(self, model: str, api_key: str):
        import anthropic

        super().__init__(model)
        self.client = anthropic.Anthropic(api_key=api_key)
        self.retryable = (
            anthropic.RateLimitError,
            anthropic.APIConnectionError,
            anthropic.InternalServerError,
        )

    def generate(self, system, prompt):
        reply = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return reply.content[0].text, reply.usage.input_tokens, reply.usage.output_tokens

    def is_retryable(self, error):
        return isinstance(error, self.retryable)


class CachedClient:
    """Remembers answers on disk, so a re-run of the same prompt costs nothing."""

    def __init__(self, inner: Client, cache_dir: str | Path):
        self.inner = inner
        self.dir = Path(cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.model = inner.model
        self.calls = 0
        self.tokens_in = 0
        self.tokens_out = 0

    def complete_json(self, system: str, prompt: str) -> dict:
        key = hashlib.sha256(f"{self.model}\n{system}\n{prompt}".encode()).hexdigest()
        path = self.dir / f"{key}.json"
        if path.exists():
            entry = json.loads(path.read_text(encoding="utf-8"))
        else:
            before = (self.inner.tokens_in, self.inner.tokens_out)
            data = self.inner.complete_json(system, prompt)
            entry = {
                "data": data,
                "tokens_in": self.inner.tokens_in - before[0],
                "tokens_out": self.inner.tokens_out - before[1],
            }
            path.write_text(json.dumps(entry), encoding="utf-8")
        self.calls += 1
        self.tokens_in += entry["tokens_in"]
        self.tokens_out += entry["tokens_out"]
        return entry["data"]


def make_client(provider: str | None = None, model: str | None = None, cache_dir=None):
    """Build a client from the environment (.env is read if present)."""
    load_dotenv()
    provider = provider or os.getenv("FILED_PROVIDER", "gemini")
    model = model or os.getenv("FILED_MODEL") or DEFAULT_MODELS[provider]
    key_name = {"gemini": "GEMINI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}[provider]
    key = os.getenv(key_name)
    if not key:
        raise LLMError(f"{key_name} is not set; put it in the .env file")
    cls = GeminiClient if provider == "gemini" else AnthropicClient
    client = cls(model, key)
    return CachedClient(client, cache_dir) if cache_dir else client


def list_models():
    load_dotenv()
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    for model in client.models.list():
        print(model.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--ping", action="store_true")
    args = parser.parse_args()
    if args.list:
        list_models()
    if args.ping:
        client = make_client()
        reply = client.complete_json("Reply with JSON only.", 'Return {"ok": true}')
        print(client.model, reply, f"tokens in/out: {client.tokens_in}/{client.tokens_out}")


if __name__ == "__main__":
    main()
