"""
LLM Engine with automatic fallback across free providers.
Fallback order: Groq -> Gemini -> OpenRouter.
"""

import os
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


class FreeLLMEngine:
    """
    Intelligent fallback system for free LLM providers.
    """

    def __init__(self, primary_model: Optional[str] = None):
        self.keys = {
            "groq": os.getenv("GROQ_API_KEY"),
            "google": os.getenv("GOOGLE_API_KEY"),
            "openrouter": os.getenv("OPENROUTER_API_KEY"),
        }

        self.models = {
            "groq": primary_model or "llama-3.3-70b-versatile",
            "google": "gemini-2.5-flash",
            "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
        }

        self.last_provider = None
        self.provider_errors = {}

    def _mark_failure(self, provider: str, error: str):
        self.provider_errors[provider] = error
        print(f"{provider} failed: {error[:160]}")

    def _try_groq(self, messages: List[Dict], temperature: float = 0.7) -> Optional[str]:
        if not self.keys["groq"]:
            self._mark_failure("Groq", "GROQ_API_KEY is not configured")
            return None

        try:
            from groq import Groq

            client = Groq(api_key=self.keys["groq"])
            response = client.chat.completions.create(
                model=self.models["groq"],
                messages=messages,
                temperature=temperature,
                max_tokens=4096,
            )

            self.last_provider = "groq"
            return response.choices[0].message.content

        except Exception as e:
            self._mark_failure("Groq", str(e))
            return None

    def _try_gemini(self, messages: List[Dict], temperature: float = 0.7) -> Optional[str]:
        if not self.keys["google"]:
            self._mark_failure("Gemini", "GOOGLE_API_KEY is not configured")
            return None

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.keys["google"])
            model = genai.GenerativeModel(self.models["google"])

            system_msg = ""
            user_msgs = []

            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                elif msg["role"] == "user":
                    user_msgs.append(msg["content"])
                elif msg["role"] == "assistant":
                    user_msgs.append(f"Assistant: {msg['content']}")

            prompt = f"{system_msg}\n\n" if system_msg else ""
            prompt += "\n".join(user_msgs) if user_msgs else messages[-1]["content"]

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=4096,
                ),
            )

            text = getattr(response, "text", None)
            if not text:
                self._mark_failure("Gemini", "empty response")
                return None

            self.last_provider = "google"
            return text

        except Exception as e:
            self._mark_failure("Gemini", str(e))
            return None

    def _try_openrouter(self, messages: List[Dict], temperature: float = 0.7) -> Optional[str]:
        if not self.keys["openrouter"]:
            self._mark_failure("OpenRouter", "OPENROUTER_API_KEY is not configured")
            return None

        try:
            from openai import OpenAI

            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.keys["openrouter"],
            )

            response = client.chat.completions.create(
                model=self.models["openrouter"],
                messages=messages,
                temperature=temperature,
                max_tokens=4096,
                extra_headers={
                    "HTTP-Referer": "https://github.com/your-repo",
                    "X-Title": "Talent Scout Agent",
                },
            )

            self.last_provider = "openrouter"
            return response.choices[0].message.content

        except Exception as e:
            self._mark_failure("OpenRouter", str(e))
            return None

    def generate(self, messages: List[Dict], temperature: float = 0.7, retries: int = 3) -> str:
        self.provider_errors = {}
        providers = [
            ("groq", "Groq", self._try_groq),
            ("google", "Gemini", self._try_gemini),
            ("openrouter", "OpenRouter", self._try_openrouter),
        ]

        for attempt in range(retries + 1):
            for provider_key, provider_name, provider_func in providers:
                if not self.keys.get(provider_key):
                    self._mark_failure(provider_name, f"API key is not configured")
                    continue

                print(f"Trying {provider_name} (attempt {attempt + 1})...")

                result = provider_func(messages, temperature)
                if result:
                    print(f"Success with {provider_name}!")
                    return result

            if attempt < retries:
                sleep_time = 2 * (2 ** attempt)
                print(f"All providers failed on attempt {attempt + 1}. Sleeping for {sleep_time}s before next round...")
                time.sleep(sleep_time)

        error_details = "; ".join(
            f"{provider_name}: {self.provider_errors.get(provider_name, 'no response')}"
            for _, provider_name, _ in providers
        )
        raise Exception(
            "All free providers failed. "
            "The app tried Groq, then Gemini, then OpenRouter. "
            f"Provider errors: {error_details}"
        )

    def get_status(self) -> Dict:
        return {
            "groq": bool(self.keys["groq"]),
            "google": bool(self.keys["google"]),
            "openrouter": bool(self.keys["openrouter"]),
            "active_provider": self.last_provider,
        }
