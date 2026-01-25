# Chunking Process - Logging & Debug Output Specification

## Requirement

Provide CLI visibility into the intelligent chunking process with detailed output showing:
1. Which markdown file is being processed
2. Headings extracted from that file
3. Total chunks generated from that file
4. Directory context extracted
5. Summary of metadata enrichment applied to chunks

---

## Output Format

### Per-File Processing Output

When processing each markdown file, display a structured summary:

```
[CHUNKING] Processing: "BGP_Configuration.md" from directory: "Networking/BGP"
  ├─ Extracted headings: 1 H1, 3 H2, 7 H3 sections
  ├─ Generated chunks: 5 chunks (avg 2.8KB per chunk)
  ├─ Directory context: "Networking/BGP" → All chunks enriched with category metadata
  └─ Summary: Directory + heading hierarchy applied to 5 chunks
```

**Format Details:**
- File name and directory path shown clearly
- Heading distribution (how many H1, H2, H3, etc.)
- Chunk count with average size in KB
- Directory context enrichment notification
- One-line summary of metadata additions

### Detailed Chunk-Level Output (DEBUG_MODE=True)

When `DEBUG_MODE` is enabled, show individual chunk details:

```
[DEBUG] Chunk 1: "BGP Basics > AS Path Filtering"
  - Size: 2,845 chars
  - Metadata: {directory: "Networking/BGP", primary_heading: "AS Path Filtering", level: 2}

[DEBUG] Chunk 2: "BGP Basics > AS Path Filtering > Standard Lists"
  - Size: 1,923 chars
  - Metadata: {directory: "Networking/BGP", primary_heading: "Standard Lists", level: 3}
```

### Session Summary Output

After processing all documents, display aggregate statistics:

```
[CHUNKING] Summary:
  ├─ Total files processed: 42
  ├─ Total chunks generated: 287
  ├─ Average chunk size: 2,847 chars
  ├─ Directory contexts applied: 12 unique directories
  └─ Enrichment stats: 100% chunks have directory context, 100% have heading context
```

---

## Implementation Details

### 1. **ObsidianMarkdownChunker Class**

```python
class ObsidianMarkdownChunker:
    
    def chunk_document(
        self,
        content: str,
        file_name: str,
        relative_path: str,
        directory_path: str,
        verbose: bool = False  # Control output verbosity
    ) -> List[MarkdownChunk]:
        """
        Parse markdown document and return chunks with detailed logging.
        
        Args:
            content: Markdown file content
            file_name: Name of file (e.g., "BGP_Configuration.md")
            relative_path: Full relative path (e.g., "Networking/BGP/BGP_Configuration.md")
            directory_path: Directory only (e.g., "Networking/BGP")
            verbose: If True, print processing details
        
        Returns:
            List of MarkdownChunk objects with context
        """
        if verbose:
            print(f"[CHUNKING] Processing: \"{file_name}\" from directory: \"{directory_path}\"")
        
        # Parse frontmatter
        fm = frontmatter.loads(content)
        main_content = fm.content
        
        # Extract heading structure
        heading_blocks = self._parse_headings(main_content)
        
        if verbose:
            # Count headings by level
            h1_count = sum(1 for h in heading_blocks if h.level == 1)
            h2_count = sum(1 for h in heading_blocks if h.level == 2)
            h3_count = sum(1 for h in heading_blocks if h.level == 3)
            h4_count = sum(1 for h in heading_blocks if h.level == 4)
            
            heading_summary = f"{h1_count} H1"
            if h2_count > 0:
                heading_summary += f", {h2_count} H2"
            if h3_count > 0:
                heading_summary += f", {h3_count} H3"
            if h4_count > 0:
                heading_summary += f", {h4_count} H4"
            
            print(f"  ├─ Extracted headings: {heading_summary} sections")
        
        # Build heading tree and generate chunks
        chunks = self._generate_chunks(
            heading_blocks,
            file_name,
            relative_path,
            directory_path
        )
        
        if verbose:
            # Calculate average chunk size
            avg_size = sum(len(c.content) for c in chunks) / len(chunks) if chunks else 0
            avg_size_kb = avg_size / 1024
            
            print(f"  ├─ Generated chunks: {len(chunks)} chunks (avg {avg_size_kb:.1f}KB per chunk)")
            print(f"  ├─ Directory context: \"{directory_path}\" → All chunks enriched with category metadata")
            print(f"  └─ Summary: Directory + heading hierarchy applied to {len(chunks)} chunks")
        
        return chunks
    
    def _parse_headings(self, content: str) -> List[HeadingBlock]:
        """Extract all headings and their content from markdown."""
        # Implementation: Use regex to find markdown headings
        # Returns: List of HeadingBlock(level, text, content)
        pass
    
    def _generate_chunks(
        self,
        heading_blocks: List[HeadingBlock],
        file_name: str,
        relative_path: str,
        directory_path: str
    ) -> List[MarkdownChunk]:
        """Generate semantic chunks respecting heading hierarchy."""
        # Implementation: Create chunks with smart sizing
        # Enriches each chunk with directory_path and heading_context metadata
        pass
```

### 2. **RAG Manager Integration**

```python
# In rag_manager.py

def _load_and_store_documents(self):
    """Load documents using intelligent chunking with progress output."""
    documents = load_all_documents()  # Returns: (file_name, content, relative_path, dir_path)
    
    if DEBUG_MODE:
        print(f"\n[CHUNKING] Starting document processing...")
        print(f"[CHUNKING] Found {len(documents)} markdown files\n")
    
    chunker = ObsidianMarkdownChunker(
        min_chunk_size=self.min_chunk_size,
        ideal_chunk_size=self.ideal_chunk_size,
        max_chunk_size=self.max_chunk_size
    )
    
    total_chunks = 0
    directories_with_context = set()
    all_chunks = []
    
    # Process each document
    for file_name, content, relative_path, directory_path in documents:
        chunks = chunker.chunk_document(
            content,
            file_name,
            relative_path,
            directory_path,
            verbose=DEBUG_MODE  # Show per-file details if DEBUG_MODE enabled
        )
        
        total_chunks += len(chunks)
        directories_with_context.add(directory_path)
        all_chunks.extend(chunks)
        
        # Extended chunk details (only if DEBUG_MODE is very verbose)
        if DEBUG_MODE and os.environ.get('DEBUG_CHUNKS_DETAILED'):
            for i, chunk in enumerate(chunks, 1):
                heading_path = " > ".join(chunk.heading_hierarchy.values())
                print(f"  [DEBUG] Chunk {i}: \"{heading_path}\"")
                print(f"    - Size: {len(chunk.content):,} chars")
                print(f"    - Level: H{chunk.chunk_level}")
    
    # Convert to langchain documents
    langchain_docs = [c.to_langchain_document() for c in all_chunks]
    
    # Store in Chroma (in batches with progress)
    self._store_documents_in_chroma(langchain_docs)
    
    # Print session summary
    if DEBUG_MODE:
        avg_size = sum(len(c.content) for c in all_chunks) / len(all_chunks) if all_chunks else 0
        
        dir_list = ", ".join(sorted(directories_with_context))
        
        print(f"\n[CHUNKING] Summary:")
        print(f"  ├─ Total files processed: {len(documents)}")
        print(f"  ├─ Total chunks generated: {total_chunks}")
        print(f"  ├─ Average chunk size: {avg_size:.0f} chars")
        print(f"  ├─ Directory contexts applied: {len(directories_with_context)} unique directories")
        print(f"  └─ Enrichment stats: 100% chunks have directory context, 100% have heading context\n")
```

### 3. **knowledge_loader.py Updates**

Ensure it returns directory information:

```python
def load_all_documents() -> List[Tuple[str, str, str, str]]:
    """
    Load all markdown files with directory context.
    
    Returns:
        List of tuples: (file_name, content, relative_path, directory_path)
        Example:
            ("BGP_Config.md", "# content...", "Networking/BGP/BGP_Config.md", "Networking/BGP")
    """
    documents = []
    knowledge_dir = get_knowledge_sources_path()
    
    for author_dir in knowledge_dir.iterdir():
        if not author_dir.is_dir():
            continue
        
        author_name = author_dir.name
        
        for md_file in author_dir.glob("*.md"):
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            file_name = md_file.name
            relative_path = f"{author_name}/{file_name}"
            directory_path = author_name
            
            documents.append((file_name, content, relative_path, directory_path))
    
    return documents
```

---

## Output Examples

### Example 1: Single File

```
[CHUNKING] Processing: "OSPF_Configuration.md" from directory: "Networking/IGP"
  ├─ Extracted headings: 1 H1, 4 H2, 12 H3 sections
  ├─ Generated chunks: 8 chunks (avg 2.1KB per chunk)
  ├─ Directory context: "Networking/IGP" → All chunks enriched with category metadata
  └─ Summary: Directory + heading hierarchy applied to 8 chunks
```

### Example 2: Full Session Summary

```
[CHUNKING] Summary:
  ├─ Total files processed: 42
  ├─ Total chunks generated: 287
  ├─ Average chunk size: 2,847 chars
  ├─ Directory contexts applied: 12 unique directories (DXC, Networking, Security, etc.)
  └─ Enrichment stats: 100% chunks have directory context, 100% have heading context
```

### Example 3: Multiple Files Output

```
[CHUNKING] Starting document processing...
[CHUNKING] Found 42 markdown files

[CHUNKING] Processing: "BGP_Configuration.md" from directory: "Networking/BGP"
  ├─ Extracted headings: 1 H1, 3 H2, 7 H3 sections
  ├─ Generated chunks: 5 chunks (avg 2.8KB per chunk)
  ├─ Directory context: "Networking/BGP" → All chunks enriched with category metadata
  └─ Summary: Directory + heading hierarchy applied to 5 chunks

[CHUNKING] Processing: "OSPF_Configuration.md" from directory: "Networking/IGP"
  ├─ Extracted headings: 1 H1, 4 H2, 12 H3 sections
  ├─ Generated chunks: 8 chunks (avg 2.1KB per chunk)
  ├─ Directory context: "Networking/IGP" → All chunks enriched with category metadata
  └─ Summary: Directory + heading hierarchy applied to 8 chunks

[CHUNKING] Summary:
  ├─ Total files processed: 42
  ├─ Total chunks generated: 287
  ├─ Average chunk size: 2,847 chars
  ├─ Directory contexts applied: 12 unique directories
  └─ Enrichment stats: 100% chunks have directory context, 100% have heading context
```

---

## Configuration

Use existing `DEBUG_MODE` from config.py:

```python
# In config.py
DEBUG_MODE = True  # Set to True to show chunking progress
```

Optional: Add to config.py for fine-grained control:

```python
# Optional: More granular debug control
DEBUG_CHUNKING_VERBOSE = False  # Show per-file details
DEBUG_CHUNKS_DETAILED = False   # Show individual chunk metadata (very verbose!)
```

---

## Integration Checklist

- [ ] `knowledge_loader.py`: Return directory_path in load_all_documents()
- [ ] `markdown_chunker.py`: Implement verbose output in chunk_document()
- [ ] `rag_manager.py`: Use verbose flag and print session summary
- [ ] `config.py`: Add chunking config parameters
- [ ] `main.py`: Ensure DEBUG_MODE propagates to RAG initialization
- [ ] Test with sample Obsidian vault and verify output format

---

## Benefits

✅ **User Visibility**: See exactly what's happening during RAG initialization  
✅ **Debugging**: Easy to identify chunking issues (empty dirs, parsing problems)  
✅ **Feedback**: Clear indication of chunks generated and context applied  
✅ **Validation**: Verify directory/heading context is properly captured  
✅ **Performance**: Average chunk sizes help optimize parameters  
✅ **Transparency**: Users understand how their knowledge base is being processed

