"""
Tool for creating a new RAG corpus (Vertex or local Chroma).
"""

import re

from google.adk.tools.tool_context import ToolContext

from ..config import DEFAULT_EMBEDDING_MODEL, USE_LOCAL_RAG
from .utils import check_corpus_exists


def create_corpus(
    corpus_name: str,
    tool_context: ToolContext,
) -> dict:
    """
    Create a new RAG corpus with the specified name.

    Args:
        corpus_name (str): The name for the new corpus
        tool_context (ToolContext): The tool context for state management

    Returns:
        dict: Status information about the operation
    """
    # Check if corpus already exists
    if check_corpus_exists(corpus_name, tool_context):
        return {
            "status": "info",
            "message": f"Corpus '{corpus_name}' already exists",
            "corpus_name": corpus_name,
            "corpus_created": False,
        }

    if USE_LOCAL_RAG:
        from ..local_rag import store as local_store

        display_name = re.sub(r"[^a-zA-Z0-9_-]", "_", corpus_name)
        return local_store.create_corpus_dict(display_name, tool_context)

    from vertexai import rag

    try:
        # Clean corpus name for use as display name
        display_name = re.sub(r"[^a-zA-Z0-9_-]", "_", corpus_name)

        # Configure embedding model
        embedding_model_config = rag.RagEmbeddingModelConfig(
            vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                publisher_model=DEFAULT_EMBEDDING_MODEL
            )
        )

        # Create the corpus
        rag_corpus = rag.create_corpus(
            display_name=display_name,
            backend_config=rag.RagVectorDbConfig(
                rag_embedding_model_config=embedding_model_config
            ),
        )

        # Update state to track corpus existence
        tool_context.state[f"corpus_exists_{corpus_name}"] = True

        # Set this as the current corpus
        tool_context.state["current_corpus"] = corpus_name

        return {
            "status": "success",
            "message": f"Successfully created corpus '{corpus_name}'",
            "corpus_name": rag_corpus.name,
            "display_name": rag_corpus.display_name,
            "corpus_created": True,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error creating corpus: {str(e)}",
            "corpus_name": corpus_name,
            "corpus_created": False,
        }
