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
