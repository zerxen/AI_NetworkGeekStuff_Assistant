# Design Proposal: Unified OpenAI Communication Wrapper

## Problem Statement

Currently, OpenAI API communication is scattered across multiple files:

| File | OpenAI Usage |
|------|--------------|
| `main.py:17` | `import openai` |
| `main.py:26` | `openai.api_key = OPENAI_API_KEY` (initialization) |
| `main.py:91-97` | `openai.chat.completions.create()` (initial request) |
| `tools_processing.py:3` | `import openai` |
| `tools_processing.py:129-135` | `openai.chat.completions.create()` (follow-up after tools) |

### Issues with Current Approach

1. **Duplicated imports and initialization** - `openai` imported in multiple places
2. **Scattered API calls** - Chat completion calls in both `main.py` and `tools_processing.py`
3. **Duplicated parameters** - `model`, `max_completion_tokens`, `tools`, `tool_choice` repeated
4. **No centralized error handling** - Each call has its own try/except
5. **No retry logic** - Transient API failures not handled consistently
6. **Tight coupling** - Business logic mixed with API communication

---

## Proposed Solution: `openai_client.py` Wrapper Module

Create a single `openai_client.py` file that encapsulates all OpenAI communication.

### Option A: Simple Function-Based Wrapper (Recommended)

```python
# openai_client.py
import openai
from config import OPENAI_API_KEY, MODEL, MAX_TOKEN_COMPLETITION
from helpers import debug_print

# Initialize once at module load
openai.api_key = OPENAI_API_KEY

def chat_completion(messages, tools=None, tool_choice="auto", max_tokens=None):
    """
    Send a chat completion request to OpenAI.

    Args:
        messages: List of message dicts
        tools: Optional tools definition list
        tool_choice: Tool choice mode (default: "auto")
        max_tokens: Max completion tokens (default: from config)

    Returns:
        OpenAI response object

    Raises:
        OpenAIError on API failure
    """
    if max_tokens is None:
        max_tokens = MAX_TOKEN_COMPLETITION

    debug_print("DEBUG: Sending chat completion request")

    response = openai.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_completion_tokens=max_tokens,
        tools=tools,
        tool_choice=tool_choice if tools else None,
    )

    debug_print("DEBUG: Received response from OpenAI")
    return response
```

**Pros:**
- Simple, minimal changes to existing code
- Easy to understand and maintain
- Single point for all API calls

**Cons:**
- Less flexible for future extensions (streaming, async)

---

### Option B: Class-Based Client with Retry Logic

```python
# openai_client.py
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

    def chat_completion(self, messages, tools=None, tool_choice="auto",
                        max_tokens=None, retries=3, retry_delay=1):
        """Send chat completion with automatic retry on transient failures."""
        if max_tokens is None:
            max_tokens = self.max_tokens

        last_error = None
        for attempt in range(retries):
            try:
                response = openai.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_completion_tokens=max_tokens,
                    tools=tools,
                    tool_choice=tool_choice if tools else None,
                )
                return response
            except openai.RateLimitError as e:
                last_error = e
                time.sleep(retry_delay * (attempt + 1))
            except openai.APIConnectionError as e:
                last_error = e
                time.sleep(retry_delay)

        raise last_error

# Singleton instance
def get_client():
    return OpenAIClient()
```

**Pros:**
- Singleton pattern ensures single initialization
- Built-in retry logic for rate limits and connection errors
- More extensible for future features

**Cons:**
- More complex
- Singleton pattern can complicate testing

---

### Option C: Async-Ready Client (Future-Proof)

```python
# openai_client.py
import openai
from config import OPENAI_API_KEY, MODEL, MAX_TOKEN_COMPLETITION
from helpers import debug_print

openai.api_key = OPENAI_API_KEY

def chat_completion(messages, tools=None, tool_choice="auto",
                    max_tokens=None, stream=False):
    """Unified chat completion supporting both sync and streaming."""
    if max_tokens is None:
        max_tokens = MAX_TOKEN_COMPLETITION

    kwargs = {
        "model": MODEL,
        "messages": messages,
        "max_completion_tokens": max_tokens,
        "stream": stream,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice

    return openai.chat.completions.create(**kwargs)

async def chat_completion_async(messages, tools=None, tool_choice="auto",
                                max_tokens=None):
    """Async version for future use."""
    # Implementation for async client
    pass
```

**Pros:**
- Ready for streaming responses
- Async support for concurrent operations

**Cons:**
- Async adds complexity not currently needed
- Over-engineering for current use case

---

## Recommendation: Option A (Simple Function-Based)

For this project's current scope and simplicity, **Option A** is recommended because:

1. **Minimal disruption** - Small changes to existing code
2. **Easy to understand** - No patterns that obscure intent
3. **Sufficient flexibility** - Can be extended later if needed
4. **YAGNI principle** - Don't add complexity until required

---

## Implementation Plan

### Files to Create
- `openai_client.py` - New wrapper module

### Files to Modify

**`main.py`:**
- Remove: `import openai`
- Remove: `openai.api_key = OPENAI_API_KEY`
- Replace: `openai.chat.completions.create(...)` with `chat_completion(...)`
- Add: `from openai_client import chat_completion`

**`tools_processing.py`:**
- Remove: `import openai`
- Replace: `openai.chat.completions.create(...)` with `chat_completion(...)`
- Add: `from openai_client import chat_completion`

### Resulting Architecture

```
main.py
  └── imports chat_completion from openai_client.py
  └── handles user interaction loop

tools_processing.py
  └── imports chat_completion from openai_client.py
  └── handles tool execution and follow-up calls

openai_client.py (NEW)
  └── imports openai, config
  └── initializes API key
  └── exports chat_completion()
```

---

## Future Considerations

If the project grows, consider upgrading to Option B when:
- Rate limiting becomes an issue
- Multiple API endpoints are needed (embeddings, etc.)
- Token counting/budget tracking is required
- Response caching is desired
