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


def load_all_documents() -> List[Tuple[str, str, str, str]]:
    """
    Load all markdown files from knowledge_sources directory recursively with directory context.
    Scans nested directories at any depth.
    
    Returns:
        List of tuples: (file_name, document_content, relative_path, directory_path)
        Examples:
            ("BGP_Config.md", "# content...", "DXC/Networking/BGP_Config.md", "DXC/Networking")
            ("OSPF.md", "# content...", "Networking/IGP/OSPF.md", "Networking/IGP")
    """
    documents = []
    knowledge_dir = get_knowledge_sources_path()
    
    if not knowledge_dir.exists():
        debug_print(f"WARNING: Knowledge sources directory not found at {knowledge_dir}")
        return documents
    
    # Walk through all directories recursively
    for root, dirs, files in os.walk(knowledge_dir):
        # Get relative path from knowledge_dir
        current_relative_dir = os.path.relpath(root, knowledge_dir)
        
        # Skip the root directory itself
        if current_relative_dir == ".":
            current_relative_dir = ""
        
        # Find all markdown files in this directory
        for file in files:
            if not file.endswith(".md"):
                continue
            
            file_path = os.path.join(root, file)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if content.strip():  # Only add non-empty documents
                    file_name = file
                    
                    # Build relative path: "Networking/BGP/BGP_Config.md"
                    if current_relative_dir:
                        relative_path = os.path.join(current_relative_dir, file_name).replace("\\", "/")
                    else:
                        relative_path = file_name
                    
                    # Directory path: "Networking/BGP"
                    directory_path = current_relative_dir.replace("\\", "/") if current_relative_dir else "root"
                    
                    documents.append((file_name, content, relative_path, directory_path))
                    debug_print(f"Loaded: {relative_path} ({len(content)} characters)")
            except Exception as e:
                debug_print(f"ERROR loading {file_path}: {e}")
    
    debug_print(f"Total documents loaded: {len(documents)}")
    return documents


def get_document_count() -> int:
    """Get the total count of available documents."""
    return len(load_all_documents())
