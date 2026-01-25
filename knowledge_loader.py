"""
Knowledge source loader for RAG pipeline.
Scans the knowledge_sources directory and loads markdown files.
"""

import os
from pathlib import Path
from typing import List, Tuple
from helpers import debug_print
from config import KNOWLEDGE_SOURCES_PATH


def get_knowledge_sources_path() -> Path:
    """Get the knowledge_sources directory path from configuration."""
    return Path(KNOWLEDGE_SOURCES_PATH).resolve()


def load_all_documents() -> List[Tuple[str, str]]:
    """
    Load all markdown files from knowledge_sources directory.
    
    Returns:
        List of tuples: (document_name, document_content)
        document_name format: "Author/Document_Title"
    """
    documents = []
    knowledge_dir = get_knowledge_sources_path()
    
    if not knowledge_dir.exists():
        debug_print(f"WARNING: Knowledge sources directory not found at {knowledge_dir}")
        return documents
    
    # Walk through all author directories
    for author_dir in knowledge_dir.iterdir():
        if not author_dir.is_dir():
            continue
        
        author_name = author_dir.name
        
        # Find all markdown files in author directory
        for md_file in author_dir.glob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if content.strip():  # Only add non-empty documents
                    doc_name = f"{author_name}/{md_file.stem}"
                    documents.append((doc_name, content))
                    debug_print(f"Loaded: {doc_name} ({len(content)} characters)")
            except Exception as e:
                debug_print(f"ERROR loading {md_file}: {e}")
    
    debug_print(f"Total documents loaded: {len(documents)}")
    return documents


def get_document_count() -> int:
    """Get the total count of available documents."""
    return len(load_all_documents())
