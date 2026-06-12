"""
Tool for deleting a RAG corpus when it's no longer needed.
"""

from google.adk.tools.tool_context import ToolContext

from ..config import USE_LOCAL_RAG
from .utils import check_corpus_exists, get_corpus_resource_name, resolve_corpus_name


def delete_corpus(
    corpus_name: str,
    confirm: bool,
    tool_context: ToolContext,
) -> dict:
    """
    Delete a RAG corpus when it's no longer needed.
    Requires confirmation to prevent accidental deletion.

    Args:
        corpus_name (str): The full resource name of the corpus to delete.
                           Preferably use the resource_name from list_corpora results.
        confirm (bool): Must be set to True to confirm deletion
        tool_context (ToolContext): The tool context

    Returns:
        dict: Status information about the deletion operation
    """
    corpus_name = resolve_corpus_name(corpus_name, tool_context)

    # Check if corpus exists
    if not check_corpus_exists(corpus_name, tool_context):
        return {
            "status": "error",
            "message": f"Corpus '{corpus_name}' does not exist",
            "corpus_name": corpus_name,
        }

    # Check if deletion is confirmed
    if not confirm:
        return {
            "status": "error",
            "message": "Deletion requires explicit confirmation. Set confirm=True to delete this corpus.",
            "corpus_name": corpus_name,
        }

    try:
        corpus_resource_name = get_corpus_resource_name(corpus_name)

        if USE_LOCAL_RAG:
            from ..local_rag import store as local_store

            return local_store.delete_corpus_dict(corpus_resource_name, tool_context)

        from vertexai import rag

        rag.delete_corpus(corpus_resource_name)

        # Remove from state by setting to False
        state_key = f"corpus_exists_{corpus_name}"
        if state_key in tool_context.state:
            tool_context.state[state_key] = False

        return {
            "status": "success",
            "message": f"Successfully deleted corpus '{corpus_name}'",
            "corpus_name": corpus_name,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error deleting corpus: {str(e)}",
            "corpus_name": corpus_name,
        }
