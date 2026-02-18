"""
LLM provider abstraction.
Switch between Ollama and Anthropic via .env config.
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()


class LLMProvider:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "ollama")
        
        if self.provider == "ollama":
            self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            self.model = os.getenv("OLLAMA_MODEL", "llama3.2")
        elif self.provider == "anthropic":
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not set in .env")
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {self.provider}")

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Send prompt to LLM, return text response."""
        if self.provider == "ollama":
            return self._ollama_generate(prompt, system_prompt)
        else:
            return self._anthropic_generate(prompt, system_prompt)

    def _ollama_generate(self, prompt: str, system_prompt: str) -> str:
        """Call Ollama local API."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
        }
        try:
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json()["response"].strip()
        except requests.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running: 'ollama serve'"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}")

    def _anthropic_generate(self, prompt: str, system_prompt: str) -> str:
        """Call Anthropic Messages API."""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"].strip()
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}")

    def is_available(self) -> bool:
        """Check if the LLM is reachable."""
        try:
            if self.provider == "ollama":
                resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
                return resp.status_code == 200
            else:
                # Anthropic — just check key exists
                return bool(self.api_key)
        except Exception:
            return False