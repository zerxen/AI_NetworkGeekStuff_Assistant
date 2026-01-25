"""
Centralized OpenAI API client wrapper.
Singleton client for all OpenAI API communication with retry logic.
"""

import openai
import time
from config import OPENAI_API_KEY, MODEL, MAX_TOKEN_COMPLETITION
from helpers import debug_print


class OpenAIClient:
    """Centralized OpenAI API client with retry logic."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        openai.api_key = OPENAI_API_KEY
        self.model = MODEL
        self.max_tokens = MAX_TOKEN_COMPLETITION
        self._initialized = True
        debug_print("DEBUG: OpenAIClient initialized")

    def chat_completion(self, messages, tools=None, tool_choice="auto",
                        max_tokens=None, retries=3, retry_delay=1):
        """
        Send chat completion with automatic retry on transient failures.

        Args:
            messages: List of message dicts
            tools: Optional tools definition list
            tool_choice: Tool choice mode (default: "auto")
            max_tokens: Max completion tokens (default: from config)
            retries: Number of retry attempts (default: 3)
            retry_delay: Base delay between retries in seconds

        Returns:
            OpenAI response object
        """
        if max_tokens is None:
            max_tokens = self.max_tokens

        debug_print("DEBUG: Sending chat completion request")

        last_error = None
        for attempt in range(retries):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "max_completion_tokens": max_tokens,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = tool_choice

                response = openai.chat.completions.create(**kwargs)
                debug_print("DEBUG: Received response from OpenAI")
                return response

            except openai.RateLimitError as e:
                last_error = e
                wait_time = retry_delay * (attempt + 1)
                print(f"Rate limit hit, retrying in {wait_time}s...")
                time.sleep(wait_time)
            except openai.APIConnectionError as e:
                last_error = e
                print(f"Connection error, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            except openai.APIError as e:
                raise e

        raise last_error


_client = None


def get_client():
    """Get the singleton OpenAI client instance."""
    global _client
    if _client is None:
        _client = OpenAIClient()
    return _client


def chat_completion(messages, tools=None, tool_choice="auto", max_tokens=None):
    """Convenience function for chat completion."""
    return get_client().chat_completion(
        messages=messages, tools=tools, tool_choice=tool_choice, max_tokens=max_tokens
    )
