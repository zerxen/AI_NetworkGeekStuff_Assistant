"""
Image path resolver for markdown image links.
Handles Obsidian wiki-style and standard markdown image references.
"""

import re
import json
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
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return meta.get("description")
        except (json.JSONDecodeError, KeyError):
            return None
