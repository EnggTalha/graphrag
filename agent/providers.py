"""
Flexible provider configuration for LLM and embedding models.
"""

import os
from typing import Optional, Union
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models import Model
import time
from sentence_transformers import SentenceTransformer
import requests
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

_embedding_model = None


def _load_sentence_transformer(model_name: str, local_path: Optional[str] = None):
    """Helper to load SentenceTransformer with retries and optional local path."""
    # Prefer explicit local path when provided
    if local_path and os.path.exists(local_path):
        try:
            return SentenceTransformer(local_path, local_files_only=True)
        except Exception:
            # Fall through to remote attempt
            pass

    # Try a few times to allow transient network issues
    attempts = 3
    delay = 1.0
    for attempt in range(attempts):
        try:
            return SentenceTransformer(model_name)
        except Exception as e:
            last_exc = e
            time.sleep(delay)
            delay *= 2

    # If we reach here, raise a helpful error
    raise RuntimeError(
        f"Failed to load SentenceTransformer model '{model_name}': {last_exc}.\n"
        "If you're running offline or behind a firewall, set EMBEDDING_LOCAL_PATH to a local model directory "
        "or configure EMBEDDING_PROVIDER to use a hosted embedding service."
    )


def get_llm_model(model_choice: Optional[str] = None) -> Union[str, Model]:
    """
    Get LLM model served by Ollama (for pydantic_ai.Agent).

    Args:
        model_choice: Optional override for model choice

    Returns:
        Model string or Model instance for pydantic_ai
    """
    llm_choice = model_choice or os.getenv('LLM_CHOICE', 'mistral')
    base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    # Use OpenAI-compatible mode with /v1 endpoint
    provider = OpenAIProvider(base_url=f"{base_url}/v1")
    return OpenAIModel(model_name=llm_choice, provider=provider)


def get_embedding_client() -> SentenceTransformer:
    """
    Get embedding client using SentenceTransformer.

    Returns:
        SentenceTransformer model instance
    """
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    # Determine model name and optional local path
    model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    local_path = os.getenv('EMBEDDING_LOCAL_PATH')

    # Lazy-load the model (with retries) to avoid network calls during module import
    _embedding_model = _load_sentence_transformer(model_name, local_path=local_path)
    return _embedding_model


def get_embedding_model() -> str:
    """
    Get embedding model name (for compatibility).

    Returns:
        Embedding model name
    """
    return 'all-MiniLM-L6-v2'


def get_ingestion_model() -> OpenAIModel:
    """
    Get ingestion-specific LLM model (can be faster/cheaper than main model).

    Returns:
        Configured model for ingestion tasks
    """
    ingestion_choice = os.getenv('INGESTION_LLM_CHOICE')

    # If no specific ingestion model, use the main model
    if not ingestion_choice:
        return get_llm_model()

    return get_llm_model(model_choice=ingestion_choice)


# Provider information functions
def get_llm_provider() -> str:
    """Get the LLM provider name."""
    return os.getenv('LLM_PROVIDER', 'openai')


def get_embedding_provider() -> str:
    """Get the embedding provider name."""
    return os.getenv('EMBEDDING_PROVIDER', 'openai')


def validate_configuration() -> bool:
    """
    Validate that required environment variables are set.

    Returns:
        True if configuration is valid
    """
    required_vars = [
        'LLM_API_KEY',
        'LLM_CHOICE',
        'EMBEDDING_API_KEY',
        'EMBEDDING_MODEL'
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False

    return True


def get_model_info() -> dict:
    """
    Get information about current model configuration.

    Returns:
        Dictionary with model configuration info
    """
    return {
        "llm_provider": get_llm_provider(),
        "llm_model": os.getenv('LLM_CHOICE'),
        "llm_base_url": os.getenv('LLM_BASE_URL'),
        "embedding_provider": get_embedding_provider(),
        "embedding_model": get_embedding_model(),
        "embedding_base_url": os.getenv('EMBEDDING_BASE_URL'),
        "ingestion_model": os.getenv('INGESTION_LLM_CHOICE', 'same as main'),
    }