"""
Tool for deleting a specific document from a RAG corpus.
"""

from google.adk.tools.tool_context import ToolContext

from ..config import USE_LOCAL_RAG
from .utils import check_corpus_exists, get_corpus_resource_name


def delete_document(
    corpus_name: str,
    document_id: str,
    tool_context: ToolContext,
) -> dict:
    """
    Delete a specific document from a RAG corpus.

    Args:
        corpus_name (str): The full resource name of the corpus containing the document.
                          Preferably use the resource_name from list_corpora results.
        document_id (str): The ID of the specific document/file to delete. This can be
                          obtained from get_corpus_info results.
        tool_context (ToolContext): The tool context

    Returns:
        dict: Status information about the deletion operation
    """
    # Check if corpus exists
    if not check_corpus_exists(corpus_name, tool_context):
        return {
            "status": "error",
            "message": f"Corpus '{corpus_name}' does not exist",
            "corpus_name": corpus_name,
            "document_id": document_id,
        }

    try:
        corpus_resource_name = get_corpus_resource_name(corpus_name)

        if USE_LOCAL_RAG:
            from ..local_rag import store as local_store

            return local_store.delete_document_dict(corpus_resource_name, document_id)

        from vertexai import rag

        rag_file_path = f"{corpus_resource_name}/ragFiles/{document_id}"
        rag.delete_file(rag_file_path)

        return {
            "status": "success",
            "message": f"Successfully deleted document '{document_id}' from corpus '{corpus_name}'",
            "corpus_name": corpus_name,
            "document_id": document_id,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error deleting document: {str(e)}",
            "corpus_name": corpus_name,
            "document_id": document_id,
        }
