"""
Embedding Service — Semantic Embedding Generation.

Provides a singleton embedding service using SentenceTransformers to convert
text into dense vector representations for semantic similarity search.
Used by the VectorStore for indexing and retrieval of execution memories.
"""

from typing import List

from sentence_transformers import SentenceTransformer

from utils.config import Config
from utils.logger import setup_logger


class EmbeddingService:
    """Singleton embedding service using SentenceTransformers.

    Loads the embedding model once and reuses it for all subsequent
    embedding requests to avoid redundant model loading overhead.

    Attributes:
        model: The SentenceTransformer model instance.
    """

    _instance = None

    def __new__(cls) -> "EmbeddingService":
        """Ensure only one instance of EmbeddingService exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the embedding model (only on first instantiation)."""
        if self._initialized:
            return

        self.logger = setup_logger("EmbeddingService")
        self.logger.info(f"Loading embedding model: {Config.EMBEDDING_MODEL}")

        try:
            self.model = SentenceTransformer(Config.EMBEDDING_MODEL)
            self.logger.info("Embedding model loaded successfully.")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            raise

        self._initialized = True

    def embed(self, text: str) -> List[float]:
        """Generate a dense vector embedding for the given text.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        self.logger.debug(f"Generating embedding for text ({len(text)} chars).")

        try:
            embedding = self.model.encode(text).tolist()
            self.logger.debug(f"Embedding generated (dim={len(embedding)}).")
            return embedding
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {e}")
            raise
