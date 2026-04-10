"""
Intelligent markdown chunker for Obsidian vaults.
Respects heading hierarchy, directory structure, and content semantics.
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from helpers import debug_print
from image_resolver import ImageResolver
from config import KNOWLEDGE_SOURCES_PATH


@dataclass
class HeadingBlock:
    """Represents a heading and its associated content."""
    level: int  # 1-6 for H1-H6
    text: str  # Heading text
    content: str  # Content under this heading (before next heading at same/higher level)
    start_pos: int  # Position in document


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
    
    def get_full_context(self) -> str:
        """Return full heading path for context: 'Part > Chapter > Section'"""
        return " > ".join(self.heading_hierarchy.values())
    
    def to_langchain_document(self):
        """Convert to langchain Document with rich metadata."""
        from langchain_core.documents import Document
        
        return Document(
            page_content=self.content,
            metadata={
                "source": self.file_name,
                "path": self.relative_path,
                "directory": self.directory_path,
                "heading_context": self.get_full_context(),
                "primary_heading": self.primary_heading,
                "chunk_level": self.chunk_level,
                "heading_hierarchy": str(self.heading_hierarchy),
            }
        )


class ObsidianMarkdownChunker:
    """
    Intelligent chunker for Obsidian vault markdown files.
    Respects heading hierarchy, directory structure, and content semantics.
    """
    
    def __init__(
        self,
        min_chunk_size: int = 500,
        ideal_chunk_size: int = 3000,
        max_chunk_size: int = 8000
    ):
        """
        Initialize the chunker with size constraints.
        
        Args:
            min_chunk_size: Minimum chunk size (chars) - content must be meaningful
            ideal_chunk_size: Ideal chunk size (chars) - target for smart sizing
            max_chunk_size: Maximum chunk size (chars) - hard limit
        """
        self.min_chunk_size = min_chunk_size
        self.ideal_chunk_size = ideal_chunk_size
        self.max_chunk_size = max_chunk_size

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

    def chunk_document(
        self,
        content: str,
        file_name: str,
        relative_path: str,
        directory_path: str,
        verbose: bool = False
    ) -> List[MarkdownChunk]:
        """
        Parse markdown document and return semantically meaningful chunks.
        
        Args:
            content: Markdown file content
            file_name: Name of file (e.g., "BGP_Configuration.md")
            relative_path: Full relative path (e.g., "Networking/BGP/BGP_Configuration.md")
            directory_path: Directory only (e.g., "Networking/BGP")
            verbose: If True, print processing details
        
        Returns:
            List of MarkdownChunk objects with full context
        """
        if verbose:
            print(f"[CHUNKING] Processing: \"{file_name}\" from directory: \"{directory_path}\"")
        
        # Strip YAML front matter (--- ... ---) if present
        match = re.match(r'^---\s*\n.*?\n---\s*\n', content, re.DOTALL)
        main_content = content[match.end():] if match else content

        # Inject image descriptions before chunking
        markdown_path = Path(KNOWLEDGE_SOURCES_PATH) / relative_path
        main_content = self._inject_image_descriptions(main_content, markdown_path)

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
            
            print(f"  |-- Extracted headings: {heading_summary} sections")
        
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
            
            print(f"  |-- Generated chunks: {len(chunks)} chunks (avg {avg_size_kb:.1f}KB per chunk)")
            print(f"  |-- Directory context: \"{directory_path}\" -> All chunks enriched with category metadata")
            print(f"  `-- Summary: Directory + heading hierarchy applied to {len(chunks)} chunks")
        
        return chunks
    
    def _parse_headings(self, content: str) -> List[HeadingBlock]:
        """
        Extract all headings and their associated content from markdown.
        
        Returns:
            List of HeadingBlock objects with heading level, text, and content
        """
        blocks = []
        
        # Regex to match markdown headings: # through ######
        heading_pattern = r'^(#{1,6})\s+(.+?)$'
        
        lines = content.split('\n')
        heading_lines = {}  # line_num -> (level, text)
        
        # First pass: find all headings and their line numbers
        for line_num, line in enumerate(lines):
            match = re.match(heading_pattern, line)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                heading_lines[line_num] = (level, text)
        
        if not heading_lines:
            # No headings found, treat entire content as one block
            return [HeadingBlock(
                level=0,
                text="[Document]",
                content=content,
                start_pos=0
            )]
        
        # Second pass: extract heading content
        sorted_heading_lines = sorted(heading_lines.keys())
        
        for idx, line_num in enumerate(sorted_heading_lines):
            level, text = heading_lines[line_num]
            
            # Content starts after the heading
            content_start = line_num + 1
            
            # Content ends at next heading of same or higher level
            content_end = len(lines)
            for next_line_num in sorted_heading_lines[idx + 1:]:
                next_level, _ = heading_lines[next_line_num]
                if next_level <= level:
                    content_end = next_line_num
                    break
            
            # Get content
            heading_content = '\n'.join(lines[content_start:content_end])
            
            blocks.append(HeadingBlock(
                level=level,
                text=text,
                content=heading_content.strip(),
                start_pos=line_num
            ))
        
        return blocks
    
    def _generate_chunks(
        self,
        heading_blocks: List[HeadingBlock],
        file_name: str,
        relative_path: str,
        directory_path: str
    ) -> List[MarkdownChunk]:
        """
        Generate semantic chunks from heading blocks with intelligent sizing.
        
        Strategy:
        - Group content under heading hierarchies
        - Respect heading relationships (H1 > H2 > H3, etc.)
        - Use smart sizing: if content < ideal_size, keep together
        - If content > max_size, split at subheading boundaries
        """
        chunks = []
        
        if not heading_blocks:
            return chunks
        
        # Build hierarchy: track parent headings
        heading_stack = {}  # level -> heading text
        
        for block in heading_blocks:
            if block.level == 0:
                # Content without heading - create one chunk
                if len(block.content) >= self.min_chunk_size:
                    chunk = MarkdownChunk(
                        content=block.content,
                        heading_hierarchy={},
                        primary_heading="[Document]",
                        file_name=file_name,
                        relative_path=relative_path,
                        directory_path=directory_path,
                        chunk_level=0,
                        is_subsection=False
                    )
                    chunks.append(chunk)
                continue
            
            # Update heading stack (remove deeper levels)
            for level in list(heading_stack.keys()):
                if level >= block.level:
                    del heading_stack[level]
            
            # Add current heading to stack
            heading_stack[block.level] = block.text
            
            # Get full heading hierarchy
            current_hierarchy = {lvl: heading_stack[lvl] for lvl in sorted(heading_stack.keys())}
            
            # Create chunk
            content = f"# {block.text}\n\n{block.content}" if block.content else f"# {block.text}"
            
            # Only create chunk if content is meaningful
            if len(content.strip()) >= self.min_chunk_size or block.level <= 2:
                chunk = MarkdownChunk(
                    content=content,
                    heading_hierarchy=current_hierarchy,
                    primary_heading=block.text,
                    file_name=file_name,
                    relative_path=relative_path,
                    directory_path=directory_path,
                    chunk_level=block.level,
                    is_subsection=block.level > 1
                )
                chunks.append(chunk)
        
        return chunks
