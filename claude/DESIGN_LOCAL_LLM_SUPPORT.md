# Design: Local LLM Support via LM Studio

## Overview

Extend the existing OpenAI communication wrapper to support local AI models running on LM Studio at `http://192.168.56.1:1234`, while maintaining compatibility with OpenAI's public API. Configuration in `config.py` will control which backend to use.

### Critical Requirement: Data Privacy

**This system will handle sensitive data.** The design must ensure:
- Full local operation capability (chat + embeddings via LM Studio)
- **No knowledge base data may be sent to public OpenAI API when configured for local operation**
- Complete isolation when `LLM_PROVIDER=local` is set

---

## Current Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   main.py   │────▶│ openai_client.py │────▶│ OpenAI Public   │
│   tools_    │     │  (Singleton)     │     │ API             │
│   processing│     │  - retry logic   │     └─────────────────┘
└─────────────┘     │  - chat_complete │
                    └──────────────────┘
```

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Configuration Layer (config.py)                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐  │
│  │ LLM_PROVIDER    │    │EMBEDDING_PROVIDER│   │ TOOLS_ENABLED       │  │
│  │ "openai"|"local"│    │ "openai"|"local" │   │ true|false          │  │
│  └────────┬────────┘    └────────┬─────────┘   └─────────────────────┘  │
└───────────┼──────────────────────┼──────────────────────────────────────┘
            │                      │
            ▼                      ▼
┌───────────────────────┐  ┌───────────────────────┐
│    llm_client.py      │  │    rag_manager.py     │
│  ┌─────────────────┐  │  │  ┌─────────────────┐  │
│  │  Chat Completion │  │  │  │   Embeddings    │  │
│  │  Tool Calling    │  │  │  │   Similarity    │  │
│  └────────┬────────┘  │  │  │   Search        │  │
└───────────┼───────────┘  │  └────────┬────────┘  │
            │              └───────────┼───────────┘
            ▼                          ▼
┌───────────────────────┐  ┌───────────────────────┐
│   OpenAI API          │  │   OpenAI API          │
│   api.openai.com      │  │   (embeddings)        │
└───────────────────────┘  └───────────────────────┘
         OR                          OR
┌───────────────────────┐  ┌───────────────────────┐
│   LM Studio           │  │   LM Studio           │
│   192.168.56.1:1234   │  │   (embedding model)   │
└───────────────────────┘  └───────────────────────┘
```

---

## Design Decisions

### Decision 1: Provider Abstraction Strategy

| Status | **DECIDED: Option A** |
|--------|----------------------|

**Option A: Single Client with Configurable Base URL** ✅
- LM Studio exposes an OpenAI-compatible API
- Reuse the existing `OpenAI` Python client, just change `base_url`
- Minimal code changes, maximum compatibility

**Rationale:** LM Studio explicitly maintains OpenAI API compatibility. No need for complex abstraction layers.

---

### Decision 2: Tool Calling Compatibility

| Status | **DECIDED: Option A** |
|--------|----------------------|

**Option A: Universal Tool Schema** ✅
- Keep current OpenAI tool format
- Let LM Studio handle translation
- Add `TOOLS_ENABLED` config flag to disable for incompatible models

**Tool Support Reference:**

| Model | Tool Calling | Notes |
|-------|-------------|-------|
| GPT-4/GPT-4o | Full support | Native OpenAI format |
| DeepSeek | Full support | OpenAI-compatible format |
| Mistral | Partial support | Some models only |
| Llama 3 | Limited | May require `TOOLS_ENABLED=false` |

---

### Decision 3: Configuration Structure

| Status | **DECIDED: config.py style** |
|--------|------------------------------|

- Keep current `config.py` module-level variable style
- Update `config.py_template` with new settings
- Use environment variable overrides where appropriate

---

### Decision 4: Model Parameter Handling

| Status | **DECIDED: Pass all parameters** |
|--------|----------------------------------|

Pass all parameters to both OpenAI and local models, even if local models don't require them. This ensures:
- Consistent code path
- No special-casing per provider
- LM Studio ignores unsupported parameters gracefully

| Parameter | OpenAI | Local (LM Studio) |
|-----------|--------|-------------------|
| `max_tokens` | Required | Passed (optional) |
| `temperature` | 0-2 | Passed |
| `top_p` | Supported | Passed |
| `tool_choice` | "auto" | Passed |

---

### Decision 5: Retry Logic

| Status | **DECIDED: Option A** |
|--------|----------------------|

**Option A: Keep current retry logic** ✅
- Same retry behavior for both providers
- Handles `RateLimitError`, `APIConnectionError`, `APIError`
- Rate limiting settings preserved

---

### Decision 6: RAG Embedding Provider Strategy

| Status | **DECIDED: Full Local Capability** |
|--------|-----------------------------------|

**Critical: Data Privacy Requirement**

RAG embeddings must be completely redirectable to local LM Studio processing. When `EMBEDDING_PROVIDER=local`:
- **NO knowledge base data sent to public OpenAI API**
- All embedding operations via LM Studio `/v1/embeddings` endpoint
- Requires embedding model loaded in LM Studio (e.g., `nomic-embed-text`)

**Current RAG Architecture (`rag_manager.py`):**
```python
# Currently hardcoded to OpenAI (lines 49-53)
self.embeddings = OpenAIEmbeddings(
    api_key=OPENAI_API_KEY,
    model="text-embedding-3-small"  # 1536 dimensions
)
```

**Target Architecture:**
```python
# Configurable via EMBEDDING_PROVIDER
self.embeddings = self._create_embeddings()  # Returns OpenAI or local

def _create_embeddings(self):
    config = get_embedding_config()
    return OpenAIEmbeddings(
        api_key=config["api_key"],
        base_url=config["base_url"],  # Points to LM Studio when local
        model=config["model"],
    )
```

**Note:** RAG database is small, so rebuilding on embedding model changes is acceptable.

---

### Decision 7: RAG Configuration Structure

| Status | **DECIDED: Grouped in config.py** |
|--------|----------------------------------|

RAG/embedding settings in `config.py`, cleanly separated from chat/tools settings:

```python
# =============================================================================
# LLM Provider Configuration (Chat & Tools)
# =============================================================================
LLM_PROVIDER = "local"  # "openai" or "local"
# ... chat settings ...

# =============================================================================
# RAG / Embedding Configuration
# =============================================================================
EMBEDDING_PROVIDER = "local"  # "openai" or "local"
# ... embedding settings ...

# =============================================================================
# Knowledge Base / Chunking Configuration
# =============================================================================
# ... existing RAG settings ...
```

---

### Decision 8: Database Compatibility Handling

| Status | **DECIDED: Option A** |
|--------|----------------------|

**Option A: Separate Databases per Provider** ✅
```python
persist_dir = f"./chroma_db_{EMBEDDING_PROVIDER}"
# OpenAI embeddings → ./chroma_db_openai/
# Local embeddings  → ./chroma_db_local/
```

**Rationale:**
- No data loss when switching providers
- Can switch back and forth for testing
- Disk space not a concern (small knowledge base)

---

## Implementation Plan

### Phase 1: Configuration Updates

**File: `config.py`**

```python
import os

# =============================================================================
# LLM Provider Configuration (Chat & Tools)
# =============================================================================
# Provider: "openai" (public API) or "local" (LM Studio)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")

# OpenAI Public API Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_MODEL = "gpt-4o-mini"

# Local LM Studio Settings
LOCAL_BASE_URL = os.getenv("LOCAL_LLM_URL", "http://192.168.56.1:1234/v1")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "deepseek-r1-distill-qwen-7b")
LOCAL_API_KEY = "lm-studio"  # LM Studio accepts any non-empty string

# Tool Support (disable for models without function calling)
TOOLS_ENABLED = os.getenv("TOOLS_ENABLED", "true").lower() == "true"

# Max tokens for completions
MAX_TOKEN_COMPLETITION = 20000

def get_llm_config():
    """Returns the active LLM configuration based on provider selection."""
    if LLM_PROVIDER == "local":
        return {
            "api_key": LOCAL_API_KEY,
            "base_url": LOCAL_BASE_URL,
            "model": LOCAL_MODEL,
        }
    else:
        return {
            "api_key": OPENAI_API_KEY,
            "base_url": OPENAI_BASE_URL,
            "model": OPENAI_MODEL,
        }

# =============================================================================
# RAG / Embedding Configuration
# =============================================================================
# Embedding provider: "openai" or "local"
# WARNING: Changing this requires rebuilding the vector database!
# SECURITY: Set to "local" to ensure no knowledge data is sent to OpenAI
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")

# OpenAI Embedding Settings (used when EMBEDDING_PROVIDER="openai")
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDING_DIMENSIONS = 1536

# Local Embedding Settings (used when EMBEDDING_PROVIDER="local")
# Requires an embedding model loaded in LM Studio
LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "nomic-embed-text-v1.5")
LOCAL_EMBEDDING_DIMENSIONS = 768  # Must match the model!

def get_embedding_config():
    """Returns the active embedding configuration based on provider selection."""
    if EMBEDDING_PROVIDER == "local":
        return {
            "provider": "local",
            "base_url": LOCAL_BASE_URL,
            "api_key": LOCAL_API_KEY,
            "model": LOCAL_EMBEDDING_MODEL,
            "dimensions": LOCAL_EMBEDDING_DIMENSIONS,
        }
    else:
        return {
            "provider": "openai",
            "base_url": OPENAI_BASE_URL,
            "api_key": OPENAI_API_KEY,
            "model": OPENAI_EMBEDDING_MODEL,
            "dimensions": OPENAI_EMBEDDING_DIMENSIONS,
        }

# =============================================================================
# Knowledge Base / Chunking Configuration
# =============================================================================
KNOWLEDGE_SOURCES_PATH = r".\knowledge_sources"
TOP_K_DOCUMENTS = 5
CHUNK_MIN_SIZE = 0
CHUNK_IDEAL_SIZE = 3000
CHUNK_MAX_SIZE = 8000

# =============================================================================
# Rate Limiting Configuration
# =============================================================================
RATE_LIMIT_ENABLED = True
RATE_LIMIT_DELAY_SECONDS = 0.5
PROGRESS_REPORT_INTERVAL = 100

# =============================================================================
# Debug Configuration
# =============================================================================
DEBUG_MODE = False
```

---

### Phase 2: LLM Client Refactoring

**Rename: `openai_client.py` → `llm_client.py`**

```python
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
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        config = get_llm_config()
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        self.model = config["model"]
        self.provider = LLM_PROVIDER
        print(f"LLM Client initialized: provider={self.provider}, model={self.model}")
        debug_print(f"Base URL: {config['base_url']}")

    def chat_completion(self, messages, tools=None, max_tokens=None):
        """
        Unified chat completion with provider-aware tool handling.
        All parameters are passed to both providers for consistency.
        """
        if max_tokens is None:
            max_tokens = MAX_TOKEN_COMPLETITION

        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        # Include tools if enabled and provided
        if tools and TOOLS_ENABLED:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return self._execute_with_retry(**kwargs)

    def _execute_with_retry(self, **kwargs):
        """Execute API call with retry logic (same for both providers)."""
        max_retries = 3
        base_delay = 20

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(**kwargs)
                return response
            except RateLimitError:
                wait_time = base_delay * (attempt + 1)
                print(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            except APIConnectionError:
                if self.provider == "local":
                    print(f"Cannot connect to LM Studio at {get_llm_config()['base_url']}")
                    print("Ensure LM Studio server is running with a model loaded.")
                wait_time = base_delay
                print(f"Connection error, retrying in {wait_time}s...")
                time.sleep(wait_time)
            except APIError as e:
                raise e

        raise Exception(f"Max retries ({max_retries}) exceeded")


# Convenience functions (maintain backward compatibility)
def get_client():
    """Get the singleton LLM client instance."""
    return LLMClient()


def chat_completion(messages, tools=None, max_tokens=None):
    """Convenience function for chat completion."""
    return get_client().chat_completion(messages, tools, max_tokens)
```

**Create backward compatibility shim: `openai_client.py`**

```python
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
```

---

### Phase 3: RAG Manager Updates

**File: `rag_manager.py`**

```python
"""
RAG Manager with configurable embedding provider.
Supports both OpenAI and local LM Studio embeddings.
"""

from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from config import (
    get_embedding_config,
    EMBEDDING_PROVIDER,
    # ... other imports ...
)

class RAGManager:
    """Manages the RAG pipeline with configurable embedding provider."""

    def __init__(self, persist_dir: str = None, ...):
        # Provider-specific persist directory
        if persist_dir is None:
            persist_dir = f"./chroma_db_{EMBEDDING_PROVIDER}"

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(exist_ok=True)

        # Initialize embeddings based on provider
        self.embeddings = self._create_embeddings()

        print(f"RAG Manager created: embedding_provider={EMBEDDING_PROVIDER}")
        print(f"Vector store path: {self.persist_dir}")
        # ... rest of init ...

    def _create_embeddings(self):
        """Create embedding function based on configured provider."""
        config = get_embedding_config()

        print(f"Initializing embeddings: provider={config['provider']}, model={config['model']}")

        if config["provider"] == "local":
            # Use OpenAI client pointed at LM Studio
            return OpenAIEmbeddings(
                api_key=config["api_key"],
                base_url=config["base_url"],
                model=config["model"],
            )
        else:
            # Standard OpenAI embeddings
            return OpenAIEmbeddings(
                api_key=config["api_key"],
                model=config["model"],
            )
```

---

### Phase 4: Update Imports

**File: `main.py`** - Update import:
```python
# Old
from openai_client import chat_completion

# New
from llm_client import chat_completion
```

**File: `tools_processing.py`** - Update import:
```python
# Old
from openai_client import chat_completion

# New
from llm_client import chat_completion
```

---

### Phase 5: Update Template

**File: `config.py_template`** - Add all new settings with documentation.

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `config.py` | Modify | Add LLM + embedding provider configuration |
| `config.py_template` | Modify | Add new settings with documentation |
| `openai_client.py` | Rename → `llm_client.py` | Refactor with provider-aware logic |
| `openai_client.py` | Create (new) | Backward compatibility shim |
| `main.py` | Modify | Update import to `llm_client` |
| `tools_processing.py` | Modify | Update import to `llm_client` |
| `rag_manager.py` | Modify | Add embedding provider selection, dynamic persist dir |
| `test_rag.py` | Modify | Add provider info display |

---

## Testing Plan

### 1. Unit Tests

- Config resolution for both LLM providers
- Config resolution for both embedding providers
- Client initialization with each provider
- Verify no OpenAI calls when `LLM_PROVIDER=local` and `EMBEDDING_PROVIDER=local`

### 2. Integration Tests

**LLM/Chat Tests:**
- LM Studio with DeepSeek + tools
- LM Studio with Mistral + tools
- Fallback behavior when `TOOLS_ENABLED=false`

**RAG/Embedding Tests:**
- Local embeddings → ChromaDB storage → retrieval
- Verify separate database directories created
- Database rebuild workflow

### 3. Manual Testing Matrix

**Full Local Operation (Primary Use Case):**

| Component | Provider | Model | Expected |
|-----------|----------|-------|----------|
| Chat | local | deepseek-r1 | Function calling works |
| Embeddings | local | nomic-embed-text | Documents embedded locally |
| RAG | local | - | No data to OpenAI |

**Verify Data Isolation:**

| Test | Method | Expected |
|------|--------|----------|
| Network capture | Wireshark/tcpdump | No traffic to api.openai.com |
| Config check | Print statements | Confirm local base_url used |
| Database path | Check filesystem | `./chroma_db_local/` created |

---

## Appendix: Embedding Model Reference

| Model | Dimensions | Size | Quality | LM Studio Support |
|-------|------------|------|---------|-------------------|
| OpenAI `text-embedding-3-small` | 1536 | API | Excellent | N/A (cloud) |
| `nomic-embed-text-v1.5` | 768 | 274MB | Very Good | Yes |
| `bge-base-en-v1.5` | 768 | 438MB | Very Good | Yes |
| `all-MiniLM-L6-v2` | 384 | 91MB | Good | Yes |
| `mxbai-embed-large-v1` | 1024 | 670MB | Excellent | Yes |

**Note:** When switching embedding models, the ChromaDB collection must be rebuilt as dimensions are incompatible. Since our knowledge base is small, this is acceptable.

---

## Security Considerations

1. **Default to Local**: Both `LLM_PROVIDER` and `EMBEDDING_PROVIDER` default to `"local"`
2. **No Accidental Leaks**: When configured for local, no code path should reach OpenAI
3. **Clear Documentation**: `config.py_template` must clearly document data privacy implications
4. **Startup Logging**: Print provider configuration on startup for verification

---

## Future Enhancements (Out of Scope)

**Chat/LLM:**
- Streaming response support
- LM Studio health check endpoint monitoring
- Automatic model capability detection

**RAG/Embeddings:**
- HuggingFace Embeddings (fully local, no server)
- Automatic embedding dimension detection

**Infrastructure:**
- Configuration validation on startup
- Provider connectivity test command
