"""
Vector Store — Local Persistent ChromaDB Integration.

Provides persistent semantic storage and retrieval of agent execution
memories using ChromaDB with SentenceTransformers embeddings. Past
execution traces are stored with metadata and retrieved via similarity
search to support retrieval-augmented agent reasoning.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import chromadb

from memory.embedding_service import EmbeddingService
from utils.config import Config
from utils.logger import setup_logger


class VectorStore:
    """Persistent vector store backed by ChromaDB.

    Stores execution traces as embedded documents and retrieves
    semantically similar past executions to augment agent reasoning.

    Attributes:
        client: A ChromaDB PersistentClient instance.
        collection: The ChromaDB collection for execution memories.
        embedding_service: The EmbeddingService for generating vectors.
    """

    def __init__(self) -> None:
        """Initialize the ChromaDB persistent client and collection."""
        self.logger = setup_logger("VectorStore")
        self.embedding_service = EmbeddingService()

        self.logger.info(
            f"Initializing ChromaDB at: {Config.CHROMA_STORAGE_PATH}"
        )

        self.client = chromadb.PersistentClient(
            path=Config.CHROMA_STORAGE_PATH
        )

        self.collection = self.client.get_or_create_collection(
            name=Config.CHROMA_COLLECTION,
            metadata={"description": "Agent execution memory store"},
        )

        self.logger.info(
            f"ChromaDB collection '{Config.CHROMA_COLLECTION}' ready "
            f"({self.collection.count()} existing entries)."
        )

    def store_execution(
        self,
        execution_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store an execution trace in the vector store.

        Args:
            execution_id: A unique identifier for this execution.
            content: The text content of the execution trace.
            metadata: Optional metadata (scenario, timestamp, etc.).
        """
        if metadata is None:
            metadata = {}

        metadata["timestamp"] = datetime.now().isoformat()

        embedding = self.embedding_service.embed(content)

        self.collection.add(
            ids=[execution_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata],
        )

        self.logger.info(
            f"Stored execution trace '{execution_id}' "
            f"({len(content)} chars, {len(embedding)}-dim embedding)."
        )

    def retrieve_similar(
        self, query: str, top_k: int = 3
    ) -> List[str]:
        """Retrieve the most similar past execution traces.

        Args:
            query: The query text to search for similar executions.
            top_k: Number of top results to return.

        Returns:
            A list of document strings from the most similar executions.
        """
        if self.collection.count() == 0:
            self.logger.info("Vector store is empty — no past executions found.")
            return []

        query_embedding = self.embedding_service.embed(query)

        # Ensure top_k doesn't exceed available documents
        actual_k = min(top_k, self.collection.count())

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_k,
        )

        documents = results.get("documents", [[]])[0]

        self.logger.info(
            f"Retrieved {len(documents)} similar execution(s) for query."
        )
        for i, doc in enumerate(documents):
            self.logger.debug(
                f"  Match {i+1}: {doc[:100]}..."
                if len(doc) > 100
                else f"  Match {i+1}: {doc}"
            )

        return documents

    def retrieve_experiences(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve full experience objects (documents, metadata, distances)."""
        if self.collection.count() == 0:
            return []
            
        query_embedding = self.embedding_service.embed(query)
        actual_k = min(top_k, self.collection.count())
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_k,
        )
        
        experiences = []
        if results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]
            
            for i in range(len(docs)):
                exp = {
                    "id": ids[i],
                    "document": docs[i],
                    "metadata": metadatas[i] if min(len(metadatas), len(docs)) > i else {},
                    "distance": distances[i] if min(len(distances), len(docs)) > i else 0.0
                }
                experiences.append(exp)
                
        return experiences
        
    def update_execution_metadata(self, execution_id: str, metadata: Dict[str, Any]) -> None:
        """Update the metadata of an existing execution trace."""
        self.collection.update(
            ids=[execution_id],
            metadatas=[metadata]
        )
