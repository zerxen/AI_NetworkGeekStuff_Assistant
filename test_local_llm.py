#!/usr/bin/env python3
"""
Micro test script to verify LM Studio connectivity for chat and embeddings.
Tests the local LLM endpoint at http://192.168.56.1:1234
"""

import sys
from openai import OpenAI

# LM Studio configuration
BASE_URL = "http://192.168.56.1:1234/v1"
API_KEY = "lm-studio"  # LM Studio accepts any non-empty string


def test_connection():
    """Test basic connectivity, chat completion, and embeddings."""
    print("=" * 60)
    print("LM Studio Connectivity Test")
    print("=" * 60)
    print(f"\nEndpoint: {BASE_URL}")

    try:
        client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

        # Test 1: List models
        print("\n1. Listing available models...")
        models = client.models.list()
        model_list = list(models)

        chat_model = None
        embedding_model = None

        if model_list:
            print(f"   Found {len(model_list)} model(s):")
            for m in model_list:
                print(f"   - {m.id}")
                # Identify model types
                if "embed" in m.id.lower():
                    embedding_model = m.id
                elif chat_model is None:
                    chat_model = m.id
        else:
            print("   No models found.")
            return False

        # Test 2: Simple chat completion
        if chat_model:
            print(f"\n2. Testing chat completion with: {chat_model}")
            response = client.chat.completions.create(
                model=chat_model,
                messages=[
                    {"role": "user", "content": "Reply with exactly: 'LM Studio OK'"}
                ],
                max_tokens=20
            )
            reply = response.choices[0].message.content.strip()
            print(f"   Response: {reply}")
            print(f"   Tokens: {response.usage.total_tokens if response.usage else 'N/A'}")
        else:
            print("\n2. No chat model found, skipping chat test.")

        # Test 3: Embeddings (critical for RAG)
        if embedding_model:
            print(f"\n3. Testing embeddings with: {embedding_model}")
            embed_response = client.embeddings.create(
                model=embedding_model,
                input="This is a test sentence for embedding."
            )
            embedding = embed_response.data[0].embedding
            print(f"   Embedding dimensions: {len(embedding)}")
            print(f"   First 5 values: {embedding[:5]}")
            print(f"   SUCCESS: Embeddings working!")
        else:
            print("\n3. No embedding model found.")
            print("   WARNING: RAG functionality requires an embedding model!")
            print("   Recommended: Load 'nomic-embed-text-v1.5' in LM Studio")

        print("\n" + "=" * 60)
        print("SUCCESS: LM Studio connection working!")
        if embedding_model:
            print(f"  Chat model: {chat_model}")
            print(f"  Embedding model: {embedding_model}")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure LM Studio is running")
        print("  2. Ensure a model is loaded in LM Studio")
        print("  3. Check that the server is enabled (Server tab in LM Studio)")
        print(f"  4. Verify the endpoint is accessible: {BASE_URL}")
        print("\n" + "=" * 60)
        print("FAILED: Could not connect to LM Studio")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
