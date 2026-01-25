# Design: RAG Extension with Image Preprocessing

## Overview

Extend the RAG system to process images linked in markdown files by generating text descriptions using LLM vision capabilities. These descriptions will be included in the context-aware chunks for embeddings, enabling semantic search over image content.

## Current State

### Existing Image Links in Knowledge Base
```
knowledge_sources/
├── NetworkGeekStuff - Article Notes & Preparation/
│   ├── thumbnail.png
│   ├── thumbnail2.png
│   └── Images/
│       ├── lab_topology.drawio.png
│       ├── lab_topology.drawio 1.png
│       ├── lab_topology.drawio 2.png
│       └── Pasted image 20260111143246.png
```

### Current Link Formats Found
```markdown
# Obsidian wiki-style (primary format in use)
![[lab_topology.drawio 2.png]]
![[Pasted image 20260111143246.png]]

# Standard markdown (may also appear)
![Network Topology](./Images/lab_topology.drawio.png)
```

### Current Behavior
- Image links pass through as literal text: `![[image.png]]`
- No image content is processed or described
- Embeddings contain image filenames but no semantic understanding

---

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PREPROCESSING PHASE (One-time)                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐  │
│  │ Scan        │────▶│ Process Images  │────▶│ Store Metadata   │  │
│  │ Markdown    │     │ via LLM Vision  │     │ .meta.json       │  │
│  │ for Images  │     │ (Local/OpenAI)  │     │ (with timestamp) │  │
│  └─────────────┘     └─────────────────┘     └──────────────────┘  │
│                                                                     │
│  Commands: python preprocess_images.py [--clean | --force]         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    CHUNKING PHASE (Existing + Enhanced)             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐  │
│  │ Load        │────▶│ Detect Image    │────▶│ Inject Image     │  │
│  │ Markdown    │     │ Links in Text   │     │ Descriptions     │  │
│  └─────────────┘     └─────────────────┘     └──────────────────┘  │
│                                                                     │
│                              ↓                                      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Enhanced Chunk with Image Context:                          │   │
│  │                                                             │   │
│  │ ## Network Setup                                            │   │
│  │ The following diagram shows our lab topology:               │   │
│  │ ![[lab_topology.drawio.png]]                               │   │
│  │                                                             │   │
│  │ [IMAGE: lab_topology.drawio.png - Network diagram showing  │   │
│  │  three routers R1, R2, R3 connected in a triangle          │   │
│  │  topology with OSPF area 0. Each router has loopback       │   │
│  │  interfaces for management...]                              │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

### Decision 1: Image Processing Pipeline

| Status | **DECIDED: Option A - Separate Preprocessing Script** |
|--------|-------------------------------------------------------|

**Implementation:**
```bash
# Process all images (skip if up-to-date)
python preprocess_images.py

# Force reprocess all images
python preprocess_images.py --force

# Clean up all cached descriptions
python preprocess_images.py --clean
```

**Features:**
- Separate script runs independently of RAG rebuild
- Timestamp-based refresh: compares image mtime vs metadata mtime
- `--clean` flag removes all `.meta.json` sidecar files
- `--force` flag reprocesses all images regardless of timestamps

---

### Decision 2: Vision Provider Configuration

| Status | **DECIDED: Dedicated config section with local default** |
|--------|----------------------------------------------------------|

**New config section in `config.py`:**
```python
# =============================================================================
# Image Processing / Vision Configuration
# =============================================================================
# Vision provider: "openai" or "local" (LM Studio)
VISION_PROVIDER = os.getenv("VISION_PROVIDER", "local")

# OpenAI Vision Settings
OPENAI_VISION_MODEL = "gpt-4o-mini"

# Local Vision Settings (LM Studio)
LOCAL_VISION_MODEL = os.getenv("LOCAL_VISION_MODEL", "mistralai/devstral-small-2-2512")
```

**Note:** Initial configuration uses same model as chat (`mistralai/devstral-small-2-2512`). Can be changed to dedicated vision model (e.g., LLaVA) later.

---

### Decision 3: Metadata Storage Format

| Status | **DECIDED: Option A - Sidecar JSON Files with Timestamp Check** |
|--------|----------------------------------------------------------------|

**File structure:**
```
Images/
├── lab_topology.drawio.png
├── lab_topology.drawio.png.meta.json   ← Sidecar file
├── thumbnail.png
└── thumbnail.png.meta.json
```

**Metadata format:**
```json
{
  "image_path": "Images/lab_topology.drawio.png",
  "description": "Network diagram showing three Cisco routers...",
  "generated_at": "2026-01-25T10:30:00Z",
  "image_mtime": 1737800000.0,
  "model_used": "mistralai/devstral-small-2-2512",
  "file_size_bytes": 245760
}
```

**Timestamp logic:**
```python
def needs_refresh(image_path: Path, meta_path: Path) -> bool:
    if not meta_path.exists():
        return True
    meta = json.loads(meta_path.read_text())
    image_mtime = image_path.stat().st_mtime
    return image_mtime > meta.get("image_mtime", 0)
```

---

### Decision 4: Image Link Detection Patterns

| Status | **DECIDED: All three patterns supported** |
|--------|------------------------------------------|

**Patterns to detect:**

```python
# All supported patterns
IMAGE_PATTERNS = [
    r'!\[\[([^\]|]+)\]\]',                    # Obsidian: ![[image.png]]
    r'!\[\[([^\]|]+)\|(\d+)\]\]',             # Obsidian with size: ![[image.png|500]]
    r'!\[([^\]]*)\]\(([^)]+)\)',              # Standard: ![alt](path.png)
]

# Combined regex for matching any image link
COMBINED_PATTERN = r'!\[\[([^\]|]+)(?:\|\d+)?\]\]|!\[([^\]]*)\]\(([^)]+)\)'
```

---

### Decision 5: Description Injection Strategy

| Status | **DECIDED: Option A - Inline Expansion** |
|--------|------------------------------------------|

**Before chunking:**
```markdown
The network topology is shown below:
![[lab_topology.png]]
```

**After injection (in chunk content):**
```markdown
The network topology is shown below:
![[lab_topology.png]]
[IMAGE: lab_topology.png - Network diagram showing three routers R1, R2, R3
connected in a triangle topology. Each router runs OSPF in area 0...]
```

**Benefits:**
- Original link preserved for reference
- Description is searchable via text embedding
- Clear visual separation with `[IMAGE: ...]` marker

---

### Decision 6: Image Resolution Order

| Status | **DECIDED: Accepted as proposed** |
|--------|----------------------------------|

**Resolution order when finding image file:**
1. Exact path from markdown file location
2. Same directory as markdown file
3. `Images/` subdirectory relative to markdown file
4. Global `Images/` in knowledge_sources root
5. Recursive search in knowledge_sources (fallback)

---

### Decision 7: Handling Missing/Unreadable Images

| Status | **DECIDED: Option B - Placeholder text** |
|--------|------------------------------------------|

**When image or description not found:**
```markdown
![[missing_diagram.png]]
[IMAGE NOT FOUND: missing_diagram.png]
```

**When image exists but no description cached:**
```markdown
![[unprocessed.png]]
[IMAGE NOT PROCESSED: unprocessed.png - Run preprocess_images.py to generate description]
```

---

## Implementation Plan

### New Files

| File | Purpose |
|------|---------|
| `image_preprocessor.py` | Core image-to-text processing logic |
| `preprocess_images.py` | CLI script with --clean and --force flags |
| `image_resolver.py` | Resolve image paths from markdown links |

### Modified Files

| File | Changes |
|------|---------|
| `config.py` | Add vision provider section |
| `config.py_template` | Document vision settings |
| `markdown_chunker.py` | Inject image descriptions into chunks |

---

### Phase 1: Configuration Updates (`config.py`)

```python
# =============================================================================
# Image Processing / Vision Configuration
# =============================================================================
# Vision provider for image-to-text preprocessing
# Options: "openai" (GPT-4o) or "local" (LM Studio)
VISION_PROVIDER = os.getenv("VISION_PROVIDER", "local")

# OpenAI Vision Settings (used when VISION_PROVIDER="openai")
OPENAI_VISION_MODEL = "gpt-4o-mini"

# Local Vision Settings (used when VISION_PROVIDER="local")
# Uses same endpoint as LLM_PROVIDER
LOCAL_VISION_MODEL = os.getenv("LOCAL_VISION_MODEL", "mistralai/devstral-small-2-2512")

# Image processing settings
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]
IMAGE_MAX_SIZE_MB = 20  # Skip images larger than this
IMAGE_DESCRIPTION_MAX_TOKENS = 500


def get_vision_config():
    """Returns the active vision configuration for image processing."""
    if VISION_PROVIDER == "local":
        return {
            "provider": "local",
            "base_url": LOCAL_BASE_URL,
            "api_key": LOCAL_API_KEY,
            "model": LOCAL_VISION_MODEL,
        }
    else:
        return {
            "provider": "openai",
            "base_url": OPENAI_BASE_URL,
            "api_key": OPENAI_API_KEY,
            "model": OPENAI_VISION_MODEL,
        }
```

---

### Phase 2: Image Preprocessor (`image_preprocessor.py`)

```python
"""
Image preprocessor for RAG pipeline.
Generates text descriptions of images using LLM vision capabilities.
"""

import base64
import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from config import get_vision_config, KNOWLEDGE_SOURCES_PATH, IMAGE_EXTENSIONS, IMAGE_MAX_SIZE_MB


class ImagePreprocessor:
    """Processes images to generate text descriptions using vision LLM."""

    def __init__(self):
        config = get_vision_config()
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        self.model = config["model"]
        self.provider = config["provider"]
        print(f"Image Preprocessor initialized: provider={self.provider}, model={self.model}")

    def scan_knowledge_base(self) -> list[Path]:
        """Find all image files in knowledge sources."""
        images = []
        base_path = Path(KNOWLEDGE_SOURCES_PATH)
        for ext in IMAGE_EXTENSIONS:
            images.extend(base_path.rglob(f"*{ext}"))
            images.extend(base_path.rglob(f"*{ext.upper()}"))
        return sorted(set(images))

    def needs_processing(self, image_path: Path) -> bool:
        """Check if image needs (re)processing based on timestamps."""
        meta_path = self._get_meta_path(image_path)
        if not meta_path.exists():
            return True

        try:
            meta = json.loads(meta_path.read_text())
            image_mtime = image_path.stat().st_mtime
            return image_mtime > meta.get("image_mtime", 0)
        except (json.JSONDecodeError, KeyError):
            return True

    def process_image(self, image_path: Path, force: bool = False) -> dict:
        """Generate description for a single image."""
        if not force and not self.needs_processing(image_path):
            print(f"  Skipping (up-to-date): {image_path.name}")
            return None

        # Check file size
        size_mb = image_path.stat().st_size / (1024 * 1024)
        if size_mb > IMAGE_MAX_SIZE_MB:
            print(f"  Skipping (too large: {size_mb:.1f}MB): {image_path.name}")
            return None

        print(f"  Processing: {image_path.name}")

        # Generate description
        try:
            description = self._generate_description(image_path)
        except Exception as e:
            print(f"    ERROR: {e}")
            description = f"Error generating description: {e}"

        # Create metadata
        metadata = {
            "image_path": str(image_path),
            "description": description,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "image_mtime": image_path.stat().st_mtime,
            "model_used": self.model,
            "provider": self.provider,
            "file_size_bytes": image_path.stat().st_size
        }

        # Save sidecar file
        meta_path = self._get_meta_path(image_path)
        meta_path.write_text(json.dumps(metadata, indent=2))

        return metadata

    def process_all(self, force: bool = False) -> dict:
        """Process all images in knowledge base."""
        images = self.scan_knowledge_base()
        print(f"Found {len(images)} images in knowledge base")

        stats = {"processed": 0, "skipped": 0, "errors": 0}

        for image_path in images:
            result = self.process_image(image_path, force=force)
            if result is None:
                stats["skipped"] += 1
            elif "Error" in result.get("description", ""):
                stats["errors"] += 1
            else:
                stats["processed"] += 1

        return stats

    def clean_all(self) -> int:
        """Remove all cached metadata files."""
        base_path = Path(KNOWLEDGE_SOURCES_PATH)
        meta_files = list(base_path.rglob("*.meta.json"))
        count = 0
        for meta_path in meta_files:
            meta_path.unlink()
            count += 1
            print(f"  Removed: {meta_path.name}")
        return count

    def _get_meta_path(self, image_path: Path) -> Path:
        """Get the metadata sidecar file path for an image."""
        return image_path.with_suffix(image_path.suffix + ".meta.json")

    def _generate_description(self, image_path: Path) -> str:
        """Call vision LLM to describe image."""
        # Read and encode image
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        # Determine MIME type
        suffix = image_path.suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp"
        }
        mime_type = mime_types.get(suffix, "image/png")

        prompt = f"""Describe this image in detail for a knowledge base search system.
Focus on:
- What the image shows (diagrams, screenshots, network topologies, photos, etc.)
- Any text visible in the image
- Technical details if it's a network/system diagram
- Key elements and their relationships
- Colors, layout, and structure if relevant

Image filename: {image_path.name}

Provide a concise but comprehensive description (2-5 sentences) that would help someone find this image when searching for related topics."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )

        return response.choices[0].message.content.strip()
```

---

### Phase 3: CLI Script (`preprocess_images.py`)

```python
#!/usr/bin/env python3
"""
CLI script to preprocess images in the knowledge base.

Usage:
    python preprocess_images.py           # Process new/modified images
    python preprocess_images.py --force   # Reprocess all images
    python preprocess_images.py --clean   # Remove all cached descriptions
"""

import sys
import argparse
from image_preprocessor import ImagePreprocessor


def main():
    parser = argparse.ArgumentParser(
        description="Preprocess images in knowledge base for RAG"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force reprocess all images regardless of timestamps"
    )
    parser.add_argument(
        "--clean", "-c",
        action="store_true",
        help="Remove all cached image descriptions"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Image Preprocessor for RAG")
    print("=" * 60)

    preprocessor = ImagePreprocessor()

    if args.clean:
        print("\nCleaning cached descriptions...")
        count = preprocessor.clean_all()
        print(f"\nRemoved {count} metadata files")

    elif args.force:
        print("\nForce processing all images...")
        stats = preprocessor.process_all(force=True)
        print(f"\nCompleted: {stats['processed']} processed, {stats['errors']} errors")

    else:
        print("\nProcessing new/modified images...")
        stats = preprocessor.process_all(force=False)
        print(f"\nCompleted: {stats['processed']} processed, {stats['skipped']} skipped, {stats['errors']} errors")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

### Phase 4: Image Resolver (`image_resolver.py`)

```python
"""
Image path resolver for markdown image links.
Handles Obsidian wiki-style and standard markdown image references.
"""

import re
from pathlib import Path
from config import KNOWLEDGE_SOURCES_PATH


# Patterns for detecting image links
OBSIDIAN_PATTERN = re.compile(r'!\[\[([^\]|]+)(?:\|\d+)?\]\]')  # ![[image.png]] or ![[image.png|500]]
MARKDOWN_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')       # ![alt](path.png)


class ImageResolver:
    """Resolves image paths from markdown links."""

    def __init__(self, base_path: Path = None):
        self.base_path = Path(base_path or KNOWLEDGE_SOURCES_PATH)

    def find_image_links(self, content: str) -> list[tuple[str, str]]:
        """
        Find all image links in markdown content.
        Returns: List of (full_match, image_reference) tuples
        """
        links = []

        # Find Obsidian-style links
        for match in OBSIDIAN_PATTERN.finditer(content):
            links.append((match.group(0), match.group(1)))

        # Find standard markdown links
        for match in MARKDOWN_PATTERN.finditer(content):
            links.append((match.group(0), match.group(2)))

        return links

    def resolve_image_path(self, image_ref: str, markdown_file: Path) -> Path | None:
        """
        Resolve an image reference to an actual file path.

        Resolution order:
        1. Exact path from markdown file location
        2. Same directory as markdown file
        3. Images/ subdirectory relative to markdown file
        4. Global Images/ in knowledge_sources root
        5. Recursive search in knowledge_sources (fallback)
        """
        md_dir = markdown_file.parent

        # 1. Exact path (could be relative or absolute)
        exact_path = md_dir / image_ref
        if exact_path.exists():
            return exact_path

        # 2. Same directory as markdown file
        same_dir = md_dir / Path(image_ref).name
        if same_dir.exists():
            return same_dir

        # 3. Images/ subdirectory relative to markdown file
        images_subdir = md_dir / "Images" / Path(image_ref).name
        if images_subdir.exists():
            return images_subdir

        # 4. Global Images/ in knowledge_sources root
        global_images = self.base_path / "Images" / Path(image_ref).name
        if global_images.exists():
            return global_images

        # 5. Recursive search (fallback)
        image_name = Path(image_ref).name
        for found in self.base_path.rglob(image_name):
            if found.is_file():
                return found

        return None

    def get_image_description(self, image_path: Path) -> str | None:
        """Get cached description for an image, if available."""
        if image_path is None:
            return None

        meta_path = image_path.with_suffix(image_path.suffix + ".meta.json")
        if not meta_path.exists():
            return None

        try:
            import json
            meta = json.loads(meta_path.read_text())
            return meta.get("description")
        except (json.JSONDecodeError, KeyError):
            return None
```

---

### Phase 5: Markdown Chunker Updates (`markdown_chunker.py`)

**Add import at top:**
```python
from image_resolver import ImageResolver
```

**Add method to ObsidianMarkdownChunker class:**
```python
def _inject_image_descriptions(self, content: str, markdown_path: Path) -> str:
    """
    Find image links in content and inject their descriptions.

    Args:
        content: Markdown content to process
        markdown_path: Path to the markdown file (for resolving relative paths)

    Returns:
        Content with image descriptions injected after image links
    """
    resolver = ImageResolver()
    links = resolver.find_image_links(content)

    if not links:
        return content

    result = content

    for full_match, image_ref in links:
        # Resolve image path
        image_path = resolver.resolve_image_path(image_ref, markdown_path)

        if image_path is None:
            # Image not found
            injection = f"\n[IMAGE NOT FOUND: {image_ref}]"
        else:
            # Try to get description
            description = resolver.get_image_description(image_path)
            if description:
                injection = f"\n[IMAGE: {image_ref} - {description}]"
            else:
                injection = f"\n[IMAGE NOT PROCESSED: {image_ref} - Run preprocess_images.py to generate description]"

        # Insert description after the image link
        result = result.replace(full_match, full_match + injection, 1)

    return result
```

**Modify chunk_document method to call injection:**
```python
def chunk_document(self, content: str, file_name: str, relative_path: str,
                   directory_path: str, verbose: bool = False) -> list[MarkdownChunk]:
    """..."""
    # Inject image descriptions before chunking
    markdown_path = Path(KNOWLEDGE_SOURCES_PATH) / relative_path
    content = self._inject_image_descriptions(content, markdown_path)

    # ... rest of existing method ...
```

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `config.py` | Modify | Add vision provider section |
| `config.py_template` | Modify | Document vision settings |
| `image_preprocessor.py` | Create | Core image-to-text with timestamp check |
| `image_resolver.py` | Create | Path resolution for image links |
| `preprocess_images.py` | Create | CLI with --clean and --force flags |
| `markdown_chunker.py` | Modify | Inject descriptions into chunks |

---

## Testing Plan

### 1. Unit Tests

- Image scanning in knowledge base
- Timestamp comparison logic
- All three link pattern detection
- Path resolution order
- Description injection formatting

### 2. Integration Tests

```bash
# Test preprocessing
python preprocess_images.py
# Verify .meta.json files created

# Test timestamp refresh
# Modify an image, run again, verify only that image reprocessed

# Test cleanup
python preprocess_images.py --clean
# Verify all .meta.json files removed

# Test force reprocess
python preprocess_images.py --force
# Verify all images reprocessed
```

### 3. RAG Verification

```python
# Query that should match image content
retrieve_context("network topology diagram routers", top_k=3)
# Should return chunks with image descriptions
```

---

## Usage

```bash
# 1. First-time setup: Process all images
python preprocess_images.py

# 2. After adding new images or modifying existing ones
python preprocess_images.py   # Only processes changed images

# 3. If descriptions seem wrong, force regenerate
python preprocess_images.py --force

# 4. To start fresh
python preprocess_images.py --clean
python preprocess_images.py

# 5. Rebuild RAG database (will include image descriptions)
python test_rag.py --rebuild
```
