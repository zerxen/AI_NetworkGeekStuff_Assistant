"""
LLM Client - Unified interface for OpenAI and LM Studio providers.
Supports both public OpenAI API and local LM Studio with OpenAI-compatible API.
"""

import time
from openai import OpenAI, RateLimitError, APIConnectionError, APIError
from config import get_llm_config, MAX_TOKEN_COMPLETITION, LLM_PROVIDER, TOOLS_ENABLED
from helpers import debug_print


class LLMClient:
    """
    Singleton LLM client that works with both OpenAI and LM Studio.
    Uses OpenAI Python SDK with configurable base_url.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialize()

    def _initialize(self):
        config = get_llm_config()
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        self.model = config["model"]
        self.provider = LLM_PROVIDER
        self.max_tokens = MAX_TOKEN_COMPLETITION
        self._initialized = True
        print(f"LLM Client initialized: provider={self.provider}, model={self.model}")
        debug_print(f"Base URL: {config['base_url']}")

    def chat_completion(self, messages, tools=None, tool_choice="auto",
                        max_tokens=None, retries=3, retry_delay=20):
        """
        Unified chat completion with provider-aware tool handling.
        All parameters are passed to both providers for consistency.

        Args:
            messages: List of message dicts
            tools: Optional tools definition list
            tool_choice: Tool choice mode (default: "auto")
            max_tokens: Max completion tokens (default: from config)
            retries: Number of retry attempts (default: 3)
            retry_delay: Base delay between retries in seconds

        Returns:
            OpenAI-compatible response object
        """
        if max_tokens is None:
            max_tokens = self.max_tokens

        debug_print(f"DEBUG: Sending chat completion request to {self.provider}")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        # Include tools if enabled and provided
        if tools and TOOLS_ENABLED:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        return self._execute_with_retry(retries, retry_delay, **kwargs)

    def _execute_with_retry(self, retries, retry_delay, **kwargs):
        """Execute API call with retry logic (same for both providers)."""
        last_error = None

        for attempt in range(retries):
            try:
                response = self.client.chat.completions.create(**kwargs)
                debug_print(f"DEBUG: Received response from {self.provider}")
                return response
            except RateLimitError as e:
                last_error = e
                wait_time = retry_delay * (attempt + 1)
                print(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            except APIConnectionError as e:
                last_error = e
                if self.provider == "local":
                    print(f"Cannot connect to LM Studio at {get_llm_config()['base_url']}")
                    print("Ensure LM Studio server is running with a model loaded.")
                else:
                    print(f"Connection error, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            except APIError as e:
                raise e

        raise last_error


# Global client instance
_client = None


def get_client():
    """Get the singleton LLM client instance."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def chat_completion(messages, tools=None, tool_choice="auto", max_tokens=None):
    """Convenience function for chat completion."""
    return get_client().chat_completion(
        messages=messages, tools=tools, tool_choice=tool_choice, max_tokens=max_tokens
    )
