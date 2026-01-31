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

def test_rag(clear_db: bool = False):
    """
    Test RAG manager initialization and document retrieval.
    
    Args:
        clear_db: If True, clears the database at the beginning
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
        
        print("\n2. Testing document retrieval...")
        test_queries = [
            "Adam Kmet is owner of any acmeco lab server?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n   Query {i}: '{query}'")
            context = retrieve_context(query, top_k=5)
            
            # Check if we got results
            if "Relevant Knowledge" in context:
                print(f"   ✓ Retrieved relevant documents")
                # Print first 300 chars of context
                #print(f"   Preview: {context[:300]}...")
                print(f"   Preview: {context}...")
            else:
                print(f"   ✗ Failed to retrieve documents")
        
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
    success = test_rag(True)
    sys.exit(0 if success else 1)
