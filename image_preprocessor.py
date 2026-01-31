"""
Image preprocessor for RAG pipeline.
Generates text descriptions of images using LLM vision capabilities.
"""

import base64
import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from config import (
    get_vision_config,
    KNOWLEDGE_SOURCES_PATH,
    IMAGE_EXTENSIONS,
    IMAGE_MAX_SIZE_MB,
    IMAGE_DESCRIPTION_MAX_TOKENS,
)


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
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
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
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

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
- All text visible in the image
- Technical details if it's a network/system diagram
- Key elements and their relationships
- If you notice any errors or anomalies in the image, like bad network topology, misconfigurations, write that down.
- All IP addresses, hostnames, labels, and annotations visible in the image. Especially IP addresses associated with devices.

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
            max_tokens=IMAGE_DESCRIPTION_MAX_TOKENS
        )

        return response.choices[0].message.content.strip()
