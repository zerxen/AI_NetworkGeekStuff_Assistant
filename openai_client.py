"""
DEPRECATED: Use llm_client instead.
This module exists for backward compatibility only.
"""

import warnings
from llm_client import LLMClient, get_client, chat_completion

# Emit deprecation warning on import
warnings.warn(
    "openai_client is deprecated, use llm_client instead",
    DeprecationWarning,
    stacklevel=2
)

# Alias for backward compatibility
OpenAIClient = LLMClient

__all__ = ['OpenAIClient', 'get_client', 'chat_completion']
