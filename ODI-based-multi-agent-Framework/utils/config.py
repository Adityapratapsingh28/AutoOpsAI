"""
Configuration Module for the Multi-Agent Orchestration Framework.

Centralizes project-level constants and configuration parameters used across
all components of the framework, including LLM provider settings and memory
layer configuration loaded from environment variables.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Project-wide configuration constants.

    Attributes:
        PROJECT_NAME: The full title of the research project.
        VERSION: Current version string.
        PHASE: The active implementation phase.
        LOG_FILE: Default log file path relative to project root.
        LLM_PROVIDER: The LLM backend to use ('groq' or 'openai').
        LLM_MODEL: The model identifier for the LLM provider.
        GROQ_API_KEY: API key for the Groq service, loaded from .env.
        EMBEDDING_MODEL: SentenceTransformers model for embeddings.
        CHROMA_STORAGE_PATH: Path for persistent ChromaDB storage.
        CHROMA_COLLECTION: Name of the ChromaDB collection.
    """

    PROJECT_NAME: str = "Dynamic Scenario-Driven Multi-Agent Orchestration Framework"
    VERSION: str = "0.3.0"
    PHASE: str = "Phase 3"
    LOG_FILE: str = "logs/system.log"

    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Memory Configuration
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_STORAGE_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "chroma_storage",
    )
    CHROMA_COLLECTION: str = "agent_execution_memory"
