# RAG Chunk Structuring Optimization Design
## High-Level Design & Implementation Plan

---

## Problem Analysis

### Current Issues

#### 1. **Naive Chunking Strategy**
- Uses `RecursiveCharacterTextSplitter` with fixed chunk_size (10,000 chars)
- Ignores markdown structure entirely
- Breaks content at arbitrary character boundaries, not semantic boundaries

#### 2. **Lost Context**
- Directory structure context (e.g., `/DXC/`, `/Networking/` folders) is discarded
- All metadata about file location is lost
- Headlines and their hierarchy are invisible to the chunker

#### 3. **Broken Semantics**
- Heading and paragraph relationships are severed
- Parent headings (H1, H2) are separated from their content (H3, H4 subsections)
- Related paragraphs under a heading may be split across chunks
- Reader lacks context for what a chunk is about

#### 4. **Inflexible Sizing**
- Fixed 10,000 char chunks don't adapt to content type
- Short, important sections get padded; complex sections get truncated
- Chunk overlap (2,000 chars) doesn't respect semantic boundaries

### Impact on RAG Quality
```
Bad Chunking → Poor Vector Embeddings → Bad Similarity Search → Wrong Knowledge Retrieved
```

---

## Proposed Solution: Intelligent Hierarchical Chunking

### Architecture Overview

```
Obsidian Vault Files (Markdown)
    ↓
Parse Markdown Structure (headings, content, metadata)
    ↓
Build Document Tree (hierarchy + directory context)
    ↓
Generate Smart Chunks (respecting structure)
    ↓
Enrich Metadata (directory path, heading context, source)
    ↓
Store in Vector DB with Full Context
```

---

## Design Details

### 1. **Markdown Parser Selection**

#### Option A: **Custom Parser + Regex** (Recommended)
**Pros:**
- Full control over what constitutes a "chunk"
- Can implement custom logic for Obsidian vault structure
- Lightweight, no extra dependencies
- Can handle YAML frontmatter easily

**Cons:**
- Need to write and maintain parsing logic
- Less robust for malformed markdown

**Implementation:**
```python
# Custom markdown parser for Obsidian vaults
def parse_markdown_structure(content: str) -> List[HeadingBlock]:
    """
    Parse markdown into heading-based blocks with hierarchy.
    Returns list of semantic chunks with full heading context.
    """
    # Parse YAML frontmatter
    # Extract heading hierarchy (H1, H2, H3, etc.)
    # Group content under each heading
    # Return blocks with context
```

#### Option B: **markdown-it-py**
```
pip install markdown-it-py mdit-py-plugins
```
**Pros:**
- Robust, standards-compliant
- Plugin system for Obsidian extensions
- Good error handling

**Cons:**
- More complex, potentially overkill
- Converts to token stream (need post-processing)

#### Option C: **Python-frontmatter + Regex**
```
pip install python-frontmatter
```
**Pros:**
- Excellent YAML frontmatter handling
- Lightweight
- Combines well with regex parsing

**Cons:**
- Still need regex for markdown structure

---

### 2. **Chunk Structure Model**

Instead of flat text chunks, create semantic blocks:

```python
@dataclass
class MarkdownChunk:
    """A semantically meaningful chunk from markdown document."""
    content: str  # The actual text content
    
    # Heading context
    heading_hierarchy: Dict[int, str]  # {1: "H1 Title", 2: "H2 Subtitle", 3: "H3 Section"}
    primary_heading: str  # The most immediate parent heading
    
    # File/Directory context
    file_name: str  # "MyDocument.md"
    relative_path: str  # "DXC/Networking/MyDocument.md"
    directory_path: str  # "DXC/Networking"
    
    # Content metadata
    chunk_level: int  # Which heading level this chunk is under (1-6)
    is_subsection: bool  # True if chunk is under a subheading
    
    # Ordering
    section_number: str  # "1.2.3" - semantic ordering
    
    def get_full_context(self) -> str:
        """Return full heading path for context: 'Part > Chapter > Section'"""
        return " > ".join(self.heading_hierarchy.values())
    
    def to_langchain_document(self) -> Document:
        """Convert to langchain Document with rich metadata."""
        return Document(
            page_content=self.content,
            metadata={
                "source": self.file_name,
                "path": self.relative_path,
                "directory": self.directory_path,
                "heading_context": self.get_full_context(),
                "primary_heading": self.primary_heading,
                "chunk_level": self.chunk_level,
            }
        )
```

---

### 3. **Intelligent Chunking Strategy**

#### Chunking Rules

```
RULE 1: Chunk Boundary = Heading Level
├─ A H2 section with all its content (H3, H4, paragraphs) = ONE chunk IF under size limit
├─ If exceeds max_chunk_size, split at H3 boundaries
└─ Never split a H3 section (split at paragraph level instead)

RULE 2: Include Full Heading Hierarchy
├─ Each chunk includes path: H1 → H2 → H3 (all parents)
├─ Enables reader to understand full context
└─ Improves embedding quality

RULE 3: Variable Chunk Sizes (Smart)
├─ Min chunk size: 500 chars (content must be meaningful)
├─ Ideal chunk size: 2,000-4,000 chars (tunable)
├─ Max chunk size: 8,000 chars (hard limit)
├─ Exception: If single H3 section > 8,000 chars, keep whole section

RULE 4: Directory Context = Metadata
├─ Prepend directory info to chunk metadata
├─ Enables RAG to understand "this is from DXC context"
└─ Improves cosine similarity for directory-specific queries

RULE 5: Preserve Paragraph Integrity
├─ Never split a paragraph in the middle
├─ Group paragraphs with their heading
└─ Keep lists together
```

#### Variable Chunk Sizing Logic

```python
def smart_chunk_section(
    heading_text: str,
    content_blocks: List[str],  # Paragraphs, lists, etc.
    max_chunk_size: int = 8000,
    ideal_chunk_size: int = 3000,
    heading_level: int = 2
) -> List[MarkdownChunk]:
    """
    Create chunks from a heading section with intelligent sizing.
    
    Strategy:
    1. If total content < ideal_size: Return ONE chunk (whole section)
    2. If ideal_size < total < max_size: Return ONE chunk (section is cohesive)
    3. If total > max_size:
       - If heading_level <= 2: Split at H3 boundaries
       - If heading_level >= 3: Split at paragraph boundaries
       - Keep at least min_chunk_size per chunk
    """
```

---

### 4. **New Chunker: `ObsidianMarkdownChunker`**

```python
class ObsidianMarkdownChunker:
    """
    Intelligent chunker for Obsidian vault markdown files.
    Respects heading hierarchy, directory structure, and content semantics.
    """
    
    def __init__(
        self,
        min_chunk_size: int = 500,
        ideal_chunk_size: int = 3000,
        max_chunk_size: int = 8000,
        include_heading_context: bool = True
    ):
        self.min_chunk_size = min_chunk_size
        self.ideal_chunk_size = ideal_chunk_size
        self.max_chunk_size = max_chunk_size
        self.include_heading_context = include_heading_context
    
    def chunk_document(
        self,
        content: str,
        file_name: str,
        relative_path: str,
        directory_path: str
    ) -> List[MarkdownChunk]:
        """
        Parse markdown document and return semantically meaningful chunks.
        
        Process:
        1. Parse frontmatter (YAML metadata)
        2. Extract heading structure
        3. Group content by heading levels
        4. Create chunks respecting hierarchy and sizes
        5. Enrich with directory/file metadata
        """
        
        # Step 1: Parse frontmatter
        fm = frontmatter.loads(content)
        doc_metadata = fm.metadata
        main_content = fm.content
        
        # Step 2: Parse heading structure
        heading_blocks = self._parse_headings(main_content)
        
        # Step 3: Build heading hierarchy tree
        heading_tree = self._build_heading_tree(heading_blocks)
        
        # Step 4: Generate chunks
        chunks = self._generate_chunks(
            heading_tree,
            file_name,
            relative_path,
            directory_path
        )
        
        return chunks
    
    def _parse_headings(self, content: str) -> List[HeadingBlock]:
        """Extract all headings and associated content."""
        
    def _build_heading_tree(self, blocks: List[HeadingBlock]) -> HeadingTree:
        """Build hierarchical tree of headings."""
        
    def _generate_chunks(
        self,
        tree: HeadingTree,
        file_name: str,
        relative_path: str,
        directory_path: str
    ) -> List[MarkdownChunk]:
        """Generate smart chunks from heading tree."""
```

---

### 5. **Integration with RAG Manager**

#### Modified RAG Flow

```python
# In rag_manager.py:

def _load_and_store_documents(self):
    """Load documents using intelligent chunking."""
    documents = load_all_documents()  # Returns (name, content, path, dir)
    
    # Use ObsidianMarkdownChunker instead of RecursiveCharacterTextSplitter
    chunker = ObsidianMarkdownChunker(
        min_chunk_size=self.min_chunk_size,
        ideal_chunk_size=self.ideal_chunk_size,
        max_chunk_size=self.max_chunk_size
    )
    
    langchain_docs = []
    for file_name, content, relative_path, directory_path in documents:
        chunks = chunker.chunk_document(
            content,
            file_name,
            relative_path,
            directory_path
        )
        langchain_docs.extend([c.to_langchain_document() for c in chunks])
    
    # Store in Chroma with rich metadata
    self.vector_store.add_documents(langchain_docs)
```

---

### 6. **Configuration Parameters**

Add to `config.py`:

```python
# Intelligent Chunking Configuration
CHUNK_MIN_SIZE = 500  # Minimum chunk size (chars)
CHUNK_IDEAL_SIZE = 3000  # Ideal chunk size (chars)
CHUNK_MAX_SIZE = 8000  # Maximum chunk size (chars)

# Obsidian/Markdown specific
INCLUDE_FRONTMATTER_IN_CHUNKS = True  # Include YAML metadata in context
PRESERVE_HEADING_HIERARCHY = True  # Keep full heading paths
```

---

## Implementation Plan

### Phase 1: Core Chunking Engine (Week 1)
- [ ] Create `markdown_chunker.py` with `ObsidianMarkdownChunker` class
- [ ] Implement heading parser using regex/frontmatter
- [ ] Implement smart chunk sizing logic
- [ ] Create `MarkdownChunk` dataclass and helper methods
- [ ] Add unit tests for parsing and chunking

### Phase 2: Integration with RAG (Week 1)
- [ ] Update `rag_manager.py` to use new chunker
- [ ] Update `knowledge_loader.py` to pass directory/file info
- [ ] Add new config parameters
- [ ] Test with sample Obsidian vault

### Phase 3: Metadata Enrichment (Week 2)
- [ ] Ensure directory paths are captured in metadata
- [ ] Test RAG retrieval with directory-specific queries
- [ ] Validate heading context in retrieved documents

### Phase 4: Optimization & Testing (Week 2)
- [ ] Test with full Obsidian vault
- [ ] Benchmark: chunk quality vs. speed
- [ ] Tune chunk size parameters
- [ ] Performance profiling

---

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Semantic Quality** | Poor (arbitrary breaks) | High (respects structure) |
| **Heading Context** | Lost | Preserved in metadata |
| **Directory Context** | Lost | Included in metadata |
| **Chunk Coherence** | Low | High (related content together) |
| **Embedding Quality** | Mediocre | Better (more contextual) |
| **Retrieval Accuracy** | Poor for structured queries | Better for context-aware queries |
| **Chunk Count** | Higher (more small chunks) | Optimized (fewer, better chunks) |

---

## Technical Considerations

### 1. **Dependencies**
- `python-frontmatter` - Parse YAML frontmatter (~50KB, well-maintained)
- `regex` (built-in `re` module) - Heading extraction
- No need for full markdown parser (overkill for our use case)

### 2. **Performance**
- Initial chunking slower (proper parsing) but still fast (<1 sec per doc)
- Fewer total chunks → faster embeddings
- Improved retrieval (less noise) → faster queries

### 3. **Obsidian Vault Considerations**
- Handle wikilinks `[[Note]]` - keep as text or strip?
- Handle front matter YAML - include in chunk or just metadata?
- Handle code blocks - treat as special content type?
- Recommendation: Include everything as-is initially, refine later

### 4. **Backward Compatibility**
- Old Chroma DB will be invalidated (different chunks)
- Add `rebuild_database()` function (already exists in RAG manager)
- Users will need to clear and rebuild vector DB

---

## Example: Before vs. After

### Input Document

```markdown
---
author: "John Doe"
topic: "Network Configuration"
---

# BGP Configuration Guide

## AS Path Filtering

AS path filtering is used to control...

### Standard AS Path Lists

Standard AS path lists are numbered...

#### Configuration Steps

1. Define the AS path
2. Apply to route-map
3. Set route-map on interface

### Extended AS Path Lists

Extended lists offer more control...
```

### Before (Current)
```
Chunk 1: "BGP Configuration Guide\n\nAS Path Filtering\n\nAS path filtering is used to control..." (truncated)
Chunk 2: "Standard AS Path Lists\n\nStandard AS path lists are numbered..." (truncated)
Chunk 3: "Extended AS Path Lists\n\nExtended lists offer more control..." (truncated)
```
❌ Lost heading hierarchy
❌ No context about what "AS Path" means
❌ Arbitrary breaks in content

### After (Proposed)
```
Chunk 1: 
  Content: "BGP Configuration Guide\n\nAS Path Filtering\n\nAS path filtering is used to control...\n\nStandard AS Path Lists\n\nStandard AS path lists are numbered...\n\n#### Configuration Steps\n\n1. Define the AS path\n2. Apply to route-map\n3. Set route-map on interface"
  Metadata: {
    "source": "BGP_Configuration_Guide.md",
    "directory": "Networking/BGP",
    "heading_context": "BGP Configuration Guide > AS Path Filtering",
    "primary_heading": "AS Path Filtering"
  }

Chunk 2:
  Content: "Extended AS Path Lists\n\nExtended lists offer more control..."
  Metadata: {
    "source": "BGP_Configuration_Guide.md",
    "directory": "Networking/BGP",
    "heading_context": "BGP Configuration Guide > Extended AS Path Lists",
    "primary_heading": "Extended AS Path Lists"
  }
```
✅ Preserved heading hierarchy
✅ Full context in metadata
✅ Semantic chunk boundaries
✅ Related content grouped together

---

## Recommendation

**Start with Phase 1 + 2 (Custom Parser + Integration)**

**Why:**
1. Simple regex-based heading parser is lightweight and maintainable
2. Use `python-frontmatter` for YAML handling
3. No complex dependencies
4. Full control over Obsidian vault specifics
5. Can evolve if needed (migrate to markdown-it-py later)

**Libraries to Install:**
```bash
pip install python-frontmatter
```

That's it! No other dependencies needed.

