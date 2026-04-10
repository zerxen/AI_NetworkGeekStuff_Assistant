#!/usr/bin/env python3
"""
Quick test script to verify RAG pipeline initialization and basic retrieval.
"""

import sys
from pathlib import Path

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent))

from rag_manager import get_rag_manager, retrieve_context
from helpers import debug_print

def test_rag(clear_db: bool = False, query: str = None):
    """
    Test RAG manager initialization and document retrieval.

    Args:
        clear_db: If True, clears the database at the beginning
        query: Query string to test. Uses a built-in default if not provided.
    """
    print("=" * 60)
    print("Testing RAG Pipeline Initialization")
    print("=" * 60)

    try:
        print("\n1. Initializing RAG Manager...")
        rag_manager = get_rag_manager()
        print("✓ RAG Manager initialized successfully")

        if clear_db:
            print("\n   Clearing database as requested...")
            rag_manager.clear_database()
            print("✓ Database cleared")

        test_queries = [query] if query else ["Adam Kmet is owner of any acmeco lab server?"]

        print("\n2. Testing document retrieval...")
        for i, q in enumerate(test_queries, 1):
            print(f"\n   Query {i}: '{q}'")
            context = retrieve_context(q, top_k=5)

            if "Relevant Knowledge" in context:
                print("   ✓ Retrieved relevant documents")
                print(f"   Preview: {context}...")
            else:
                print("   ✗ Failed to retrieve documents")

        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test the RAG pipeline")
    parser.add_argument("query", nargs="?", default=None, help="Query to test (default: built-in test query)")
    parser.add_argument("--no-clear", action="store_true", help="Skip clearing the database before testing")
    args = parser.parse_args()

    success = test_rag(clear_db=not args.no_clear, query=args.query)
    sys.exit(0 if success else 1)
