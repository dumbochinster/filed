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
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

RETRY_WAITS = [2, 5, 10, 20, 40]
REQUEST_TIMEOUT_MS = 90_000
LOCAL_TIMEOUT_S = 300
DEFAULT_MODELS = {"gemini": "gemini-2.5-flash"}


class LLMError(Exception):
    pass


class QuotaExhausted(Exception):
    """The provider's daily limit is used up. Retrying today is pointless."""


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
        # Seconds to leave between calls, to stay under a provider's per-minute limit.
        self.min_interval = float(os.getenv("FILED_MIN_INTERVAL", "0"))
        self._last_call = 0.0

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
            pause = self._last_call + self.min_interval - time.time()
            if pause > 0:
                time.sleep(pause)
            self._last_call = time.time()
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
        from google.genai import types

        super().__init__(model)
        self.client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS)
        )

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
        if getattr(error, "code", None) in (429, 500, 503, 504):
            return True
        # A request that hung and hit our timeout is worth another try.
        return isinstance(error, TimeoutError) or type(error).__module__.startswith("httpx")


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


# Providers that speak the OpenAI chat-completions format: (base URL, key variable, default model)
OPENAI_COMPATIBLE = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "llama-3.3-70b-versatile"),
    "cerebras": ("https://api.cerebras.ai/v1", "CEREBRAS_API_KEY", "llama-3.3-70b"),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY", "mistral-small-latest"),
}


class OpenAICompatibleClient(Client):
    def __init__(self, model: str, api_key: str, base_url: str):
        super().__init__(model)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def generate(self, system, prompt):
        body = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode()
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "filed/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_MS / 1000) as reply:
            data = json.load(reply)
        usage = data.get("usage", {})
        text = data["choices"][0]["message"]["content"] or ""
        return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

    def is_retryable(self, error):
        if isinstance(error, urllib.error.HTTPError):
            return error.code in (429, 500, 502, 503, 504)
        return isinstance(error, (TimeoutError, urllib.error.URLError))


class OllamaClient(Client):
    """A model running on this computer through Ollama. Free, private, no daily limit."""

    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        super().__init__(model)
        self.base_url = base_url.rstrip("/")

    def generate(self, system, prompt):
        body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": "json",
                "think": False,  # skip the long reasoning preamble; we only need the JSON answer
                "options": {"temperature": 0, "num_ctx": 4096},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode()
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=LOCAL_TIMEOUT_S) as reply:
            data = json.load(reply)
        return (
            data["message"]["content"],
            data.get("prompt_eval_count", 0),
            data.get("eval_count", 0),
        )

    def is_retryable(self, error):
        return isinstance(error, (TimeoutError, urllib.error.URLError))


class NoModel:
    """Stands in for a provider when replaying from the cache: any call is a cache miss."""

    def __init__(self, model: str):
        self.model = model
        self.calls = self.tokens_in = self.tokens_out = 0

    def complete_json(self, system: str, prompt: str) -> dict:
        raise LookupError("this prompt is not in the cache and replay mode never calls a model")


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
    if provider == "ollama":
        client = OllamaClient(model or os.getenv("FILED_MODEL") or "qwen3.5:9b-q4_K_M")
        return CachedClient(client, cache_dir) if cache_dir else client
    if provider in OPENAI_COMPATIBLE:
        base_url, key_name, default_model = OPENAI_COMPATIBLE[provider]
    else:
        key_name = {"gemini": "GEMINI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}[provider]
        default_model = DEFAULT_MODELS.get(provider)
    model = model or os.getenv("FILED_MODEL") or default_model
    if not model:
        raise LLMError(f"set FILED_MODEL in .env: {provider} has no default model")
    key = os.getenv(key_name)
    if not key:
        raise LLMError(f"{key_name} is not set; put it in the .env file")
    if provider in OPENAI_COMPATIBLE:
        client = OpenAICompatibleClient(model, key, base_url)
    else:
        client = (GeminiClient if provider == "gemini" else AnthropicClient)(model, key)
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
