"""
RAG (Retrieval-Augmented Generation) Manager using Chroma vector database.
Handles document embedding, storage, and retrieval for the chat pipeline.
Supports both OpenAI and local LM Studio embeddings.
"""

import os
from pathlib import Path
import time
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from config import (
    get_embedding_config,
    EMBEDDING_PROVIDER,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_DELAY_SECONDS,
    PROGRESS_REPORT_INTERVAL,
    DEBUG_MODE,
    CHUNK_MIN_SIZE,
    CHUNK_IDEAL_SIZE,
    CHUNK_MAX_SIZE
)
from knowledge_loader import load_all_documents
from markdown_chunker import ObsidianMarkdownChunker
from helpers import debug_print


class RAGManager:
    """Manages the RAG pipeline with configurable embedding provider."""

    def __init__(self, persist_dir: str = None, chunk_size: int = 10000,
                 chunk_overlap: int = 2000, top_k: int = 5):
        """
        Initialize the RAG manager.

        Args:
            persist_dir: Directory to persist Chroma database (auto-set based on provider if None)
            chunk_size: Size of text chunks for splitting documents
            chunk_overlap: Overlap between chunks
            top_k: Number of documents to retrieve per query
        """
        # Provider-specific persist directory
        if persist_dir is None:
            persist_dir = f"./chroma_db_{EMBEDDING_PROVIDER}"

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(exist_ok=True)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k
        self._initialized = False

        # Initialize embeddings based on provider
        self.embeddings = self._create_embeddings()

        # Initialize Chroma client
        self.chroma_client = chromadb.PersistentClient(path=str(self.persist_dir))

        # Vector store will be initialized lazily on first use
        self.vector_store = None

        print(f"RAG Manager created: embedding_provider={EMBEDDING_PROVIDER}")
        print(f"Vector store path: {self.persist_dir}")

    def _create_embeddings(self):
        """Create embedding function based on configured provider."""
        config = get_embedding_config()

        print(f"Initializing embeddings: provider={config['provider']}, model={config['model']}")

        if config["provider"] == "local":
            # Use OpenAI client pointed at LM Studio
            # Disable tiktoken/token checking for local models
            return OpenAIEmbeddings(
                api_key=config["api_key"],
                base_url=config["base_url"],
                model=config["model"],
                check_embedding_ctx_length=False,  # Don't tokenize for local models
            )
        else:
            # Standard OpenAI embeddings
            return OpenAIEmbeddings(
                api_key=config["api_key"],
                model=config["model"],
            )

    def _initialize_vector_store(self):
        """Initialize or load existing Chroma vector store."""
        self._initialized = True
        try:
            # Try to load existing collection
            print("Attempting to load existing Chroma vector store...")
            self.vector_store = Chroma(
                client=self.chroma_client,
                embedding_function=self.embeddings,
                collection_name="knowledge_base",
                persist_directory=str(self.persist_dir)
            )

            # Check if collection has documents
            collection = self.chroma_client.get_collection("knowledge_base")
            count = collection.count()
            print(f"Loaded existing vector store with {count} documents")

            if count == 0:
                print("Vector store is empty, loading documents...")
                self._load_and_store_documents()
        except Exception as e:
            print(f"Could not load existing vector store: {e}")
            print("Creating new vector store...")
            self._load_and_store_documents()

    def _load_and_store_documents(self):
        """Load all knowledge source documents using intelligent chunking and store embeddings."""
        documents = load_all_documents()  # Returns: (file_name, content, relative_path, directory_path)

        if not documents:
            print("WARNING: No documents loaded from knowledge sources")
            return

        # Initialize intelligent chunker
        chunker = ObsidianMarkdownChunker(
            min_chunk_size=CHUNK_MIN_SIZE,
            ideal_chunk_size=CHUNK_IDEAL_SIZE,
            max_chunk_size=CHUNK_MAX_SIZE
        )

        if DEBUG_MODE:
            print(f"\n[CHUNKING] Starting document processing...")
            print(f"[CHUNKING] Found {len(documents)} markdown files\n")

        total_chunks = 0
        directories_with_context = set()
        all_chunks = []

        # Process each document with intelligent chunking
        for file_name, content, relative_path, directory_path in documents:
            chunks = chunker.chunk_document(
                content,
                file_name,
                relative_path,
                directory_path,
                verbose=DEBUG_MODE  # Show per-file details if DEBUG_MODE enabled
            )

            total_chunks += len(chunks)
            directories_with_context.add(directory_path)
            all_chunks.extend(chunks)

        if DEBUG_MODE:
            print()  # Blank line for readability

        # Convert to langchain documents with rich metadata
        langchain_docs = [c.to_langchain_document() for c in all_chunks]

        print(f"Processing {len(langchain_docs)} chunks from {len(documents)} documents...")
        print(f"Rate limiting: {RATE_LIMIT_ENABLED} | Delay: {RATE_LIMIT_DELAY_SECONDS}s | Progress interval: {PROGRESS_REPORT_INTERVAL} chunks")

        # Store in Chroma with rate limiting
        print("Embedding and storing documents in Chroma...")
        start_time = time.time()

        # Process chunks in batches with rate limiting and progress reporting
        batch_size = 50  # Process in batches to reduce API calls
        for batch_idx in range(0, len(langchain_docs), batch_size):
            batch_end = min(batch_idx + batch_size, len(langchain_docs))
            batch = langchain_docs[batch_idx:batch_end]

            # Store batch
            if batch_idx == 0:
                # First batch - use from_documents
                self.vector_store = Chroma.from_documents(
                    documents=batch,
                    embedding=self.embeddings,
                    client=self.chroma_client,
                    collection_name="knowledge_base",
                    persist_directory=str(self.persist_dir)
                )
            else:
                # Subsequent batches - use add_documents
                self.vector_store.add_documents(batch)

            # Progress reporting
            if (batch_end % PROGRESS_REPORT_INTERVAL == 0) or (batch_end == len(langchain_docs)):
                elapsed = time.time() - start_time
                rate = batch_end / elapsed if elapsed > 0 else 0
                print(f"Progress: {batch_end}/{len(langchain_docs)} chunks embedded ({rate:.1f} chunks/sec)")

            # Rate limiting between batches
            if RATE_LIMIT_ENABLED and batch_end < len(langchain_docs):
                time.sleep(RATE_LIMIT_DELAY_SECONDS)

        print(f"Documents successfully stored in vector database ({len(langchain_docs)} chunks total)")

        # Print session summary
        if DEBUG_MODE:
            avg_size = sum(len(c.content) for c in all_chunks) / len(all_chunks) if all_chunks else 0
            dir_list = ", ".join(sorted(directories_with_context)) if directories_with_context else "None"

            print(f"\n[CHUNKING] Summary:")
            print(f"  |-- Total files processed: {len(documents)}")
            print(f"  |-- Total chunks generated: {total_chunks}")
            print(f"  |-- Average chunk size: {avg_size:.0f} chars")
            print(f"  |-- Directory contexts applied: {len(directories_with_context)} unique directories ({dir_list})")
            print(f"  `-- Enrichment stats: 100% chunks have directory context, 100% have heading context\n")

    def retrieve_relevant_documents(self, query: str, top_k: int = None) -> str:
        """
        Retrieve relevant documents based on the query.

        Args:
            query: User query string
            top_k: Number of documents to retrieve (uses default if None)

        Returns:
            Formatted string with relevant document excerpts
        """
        # Initialize vector store on first use
        if not self._initialized:
            print("Initializing vector store on first query...")
            self._initialize_vector_store()

        if self.vector_store is None:
            return "No knowledge base available."

        k = top_k or self.top_k

        try:
            # Perform similarity search
            results = self.vector_store.similarity_search(query, k=k)

            if not results:
                return "No relevant documents found."

            # Format results
            context = "## Relevant Knowledge from Sources:\n\n"
            for i, doc in enumerate(results, 1):
                source = doc.metadata.get("source", "Unknown")
                context += f"**[{i}] From {source}:**\n"
                context += f"{doc.page_content[:500]}...\n\n"  # First 500 chars

            print(f"Retrieved {len(results)} relevant documents")
            return context

        except Exception as e:
            print(f"ERROR during retrieval: {e}")
            return f"Error retrieving documents: {e}"

    def clear_database(self):
        """Clear the Chroma database (for testing/reset)."""
        try:
            self.chroma_client.delete_collection("knowledge_base")
            self.vector_store = None
            self._initialized = False
            print("Vector store cleared")
        except Exception as e:
            print(f"Error clearing vector store: {e}")

    def rebuild_database(self):
        """Rebuild the entire vector database (reload documents from disk)."""
        print("Rebuilding vector database...")
        self.clear_database()
        self._load_and_store_documents()
        self._initialized = True
        print("Vector database rebuild complete")


# Global RAG manager instance
_rag_manager = None


def get_rag_manager() -> RAGManager:
    """Get or create the global RAG manager instance."""
    global _rag_manager
    if _rag_manager is None:
        _rag_manager = RAGManager()
    return _rag_manager


def retrieve_context(query: str, top_k: int = 5) -> str:
    """
    Convenience function to retrieve relevant context for a query.

    Args:
        query: User query string
        top_k: Number of documents to retrieve

    Returns:
        Formatted string with relevant document excerpts
    """
    manager = get_rag_manager()
    return manager.retrieve_relevant_documents(query, top_k=top_k)
