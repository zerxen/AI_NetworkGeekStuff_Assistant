# AI Network Assistant

An AI-powered CLI assistant for network engineering, lab operations, and administrative tasks. Features local LLM support via LM Studio, RAG-based knowledge retrieval from markdown documentation, and SSH-based device management tools.

## Features

- **Dual LLM Provider Support**: Switch between OpenAI API and local LM Studio
- **RAG Knowledge Base**: Semantic search over markdown documentation (Obsidian-compatible)
- **Image Preprocessing**: LLM vision generates searchable descriptions for embedded images
- **Network Device Tools**: SSH-based configuration retrieval and command execution
- **Function Calling**: LLM can invoke tools autonomously with human approval for destructive actions

---

## Configuration

Copy the template and configure your settings:

```bash
cp config.py_template config.py
```

### Key Configuration Options

```python
# LLM Provider: "openai" or "local" (LM Studio)
LLM_PROVIDER = "local"

# Local LM Studio endpoint
LOCAL_BASE_URL = "http://192.168.56.1:1234/v1"
LOCAL_MODEL = "mistralai/devstral-small-2-2512"

# Embedding Provider (for RAG): "openai" or "local"
EMBEDDING_PROVIDER = "local"
LOCAL_EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"

# Vision Provider (for image preprocessing): "openai" or "local"
VISION_PROVIDER = "local"
```

**Data Privacy**: Set all providers to `"local"` to ensure no data is sent to OpenAI.

---

## Testing Setup

### 1. Test LM Studio Connectivity

Verify your local LLM endpoint is working:

```bash
python test_local_llm.py
```

This tests:
- Model listing from LM Studio
- Chat completion functionality
- Embedding model availability (required for RAG)

Expected output:
```
LM Studio Connectivity Test
Endpoint: http://192.168.56.1:1234/v1
1. Listing available models...
   Found 2 model(s):
   - mistralai/devstral-small-2-2512
   - text-embedding-nomic-embed-text-v1.5
2. Testing chat completion...
   Response: LM Studio OK
3. Testing embeddings...
   Embedding dimensions: 768
   SUCCESS: Embeddings working!
```

### 2. Test RAG Pipeline

Verify the knowledge base indexing and retrieval:

```bash
python test_rag.py
```

This tests:
- RAG manager initialization
- Document chunking from `knowledge_sources/`
- Vector database creation (ChromaDB)
- Semantic search retrieval

---

## Available Tools

The assistant has access to these tools (defined in `tools.py`):

| Tool | Description |
|------|-------------|
| `getCurrentDateAndTime` | Returns current date/time with custom strftime format |
| `getTopologyInformation` | Reads network topology from ContainerLab YAML files |
| `getDeviceConfiguration` | Retrieves running config from Cisco devices or network info from Linux VMs via SSH |
| `executeCommandsOnDevice` | Executes arbitrary commands on devices via SSH (requires human approval) |
| `retrieveKnowledge` | Searches the RAG knowledge base for relevant documentation |

---

## RAG Knowledge Base

Place markdown files in `knowledge_sources/` directory. The RAG system:
- Chunks documents by heading hierarchy
- Preserves directory context as metadata
- Supports Obsidian wiki-style links

### Image Preprocessing

Images embedded in markdown are preprocessed using LLM vision to generate searchable text descriptions.

#### How It Works

1. **Preprocessing**: `preprocess_images.py` scans images and generates descriptions via vision LLM
2. **Sidecar Files**: Each image gets a `.meta.json` file with cached description
3. **Chunking**: Descriptions are injected after image links during RAG indexing

#### Sidecar File Format

For `lab_topology.png`, creates `lab_topology.png.meta.json`:

```json
{
  "image_path": "knowledge_sources/Images/lab_topology.png",
  "description": "Network diagram showing three routers connected in triangle topology...",
  "generated_at": "2026-01-25T10:30:00Z",
  "image_mtime": 1737800000.0,
  "model_used": "mistralai/devstral-small-2-2512"
}
```

#### Supported Image Link Formats

- Obsidian wiki-style: `![[image.png]]`
- Obsidian with size: `![[image.png|500]]`
- Standard markdown: `![alt](path/to/image.png)`

#### Usage

```bash
# Process new/modified images (skips up-to-date)
python preprocess_images.py

# Force reprocess all images
python preprocess_images.py --force

# Remove all cached descriptions
python preprocess_images.py --clean

# Rebuild RAG database after preprocessing
python test_rag.py
```

---

## Running the Assistant

Start the interactive CLI:

```bash
python main.py
```

### Example Session

```
Initializing RAG knowledge base...
Knowledge base ready.

Interactive LLM CLI (type 'exit' or Ctrl-C to quit)

You: What is the current time?
Tool executed called: getCurrentDateAndTime with fmt = %Y-%m-%d %H:%M:%S

LLM: The current time is 2026-01-25 14:32:15.

You: What devices are in the lab topology?
Tool executed called: getTopologyInformation

LLM: The lab topology contains:
- cisco1, cisco2, cisco3 (Cisco IOL routers)
- ubuntu1, ubuntu2 (Linux VMs)

You: Show me the running config of cisco1
Tool executed called: getDeviceConfiguration with target = cisco1
Connecting to Cisco device at 172.20.20.11...

LLM: Here is the running configuration of cisco1:
[configuration output]

You: clear
Conversation context cleared.

You: exit
Goodbye.
```

### Special Commands

- `clear` - Reset conversation context
- `exit` / `quit` - Exit the CLI
- `Ctrl-C` - Force exit

---

## Requirements

Install dependencies:

```bash
pip install openai langchain langchain-openai chromadb netmiko paramiko pyyaml python-frontmatter
```

For local LLM support, install and configure [LM Studio](https://lmstudio.ai/) with:
- A chat model (e.g., `mistralai/devstral-small-2-2512`)
- An embedding model (e.g., `nomic-embed-text-v1.5`)
