#!/usr/bin/env python3
"""
Test script to validate the intelligent chunking implementation.
"""

import sys
from markdown_chunker import ObsidianMarkdownChunker

# Test markdown content
test_content = """---
title: "BGP Configuration Guide"
author: "John Doe"
---

# BGP Configuration Guide

## AS Path Filtering

AS path filtering is used to control which routes are accepted based on the AS path.

### Standard AS Path Lists

Standard AS path lists are numbered from 1-65535 and allow pattern matching on the full AS path.

These are useful for:
- Filtering based on specific ASes
- Controlling route preference

#### Configuration Steps

1. Define the AS path access list
2. Apply the access list to a route-map
3. Set the route-map on the BGP session

### Extended AS Path Lists

Extended AS path lists provide more granular control.

## Community-Based Filtering

Communities are tags attached to routes.

### Standard Communities

Standard communities use a 32-bit value.

### Extended Communities

Extended communities provide more flexibility.
"""

def test_chunking():
    """Test the markdown chunker."""
    print("Testing ObsidianMarkdownChunker...\n")
    
    chunker = ObsidianMarkdownChunker(
        min_chunk_size=500,
        ideal_chunk_size=3000,
        max_chunk_size=8000
    )
    
    chunks = chunker.chunk_document(
        content=test_content,
        file_name="BGP_Configuration.md",
        relative_path="Networking/BGP/BGP_Configuration.md",
        directory_path="Networking/BGP",
        verbose=True
    )
    
    print(f"\n{'='*70}")
    print("Generated Chunks Details:")
    print(f"{'='*70}\n")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i}:")
        print(f"  Heading Context: {chunk.get_full_context()}")
        print(f"  Primary Heading: {chunk.primary_heading}")
        print(f"  Directory: {chunk.directory_path}")
        print(f"  Size: {len(chunk.content)} chars")
        print(f"  Level: H{chunk.chunk_level}")
        print(f"  Content Preview: {chunk.content[:100]}...")
        print()
    
    print(f"{'='*70}")
    print(f"Total chunks generated: {len(chunks)}")
    print(f"Average chunk size: {sum(len(c.content) for c in chunks) / len(chunks):.0f} chars")
    print(f"Directory contexts applied: {set(c.directory_path for c in chunks)}")
    
    return chunks

if __name__ == "__main__":
    try:
        chunks = test_chunking()
        print("\n✅ Chunking test completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during chunking test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
