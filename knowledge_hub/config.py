"""
Configuration settings for Knowledge HUB.

These settings are used by the various RAG tools.
Vertex AI initialization is performed in the package's __init__.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables (this is redundant if __init__.py is imported first,
# but included for safety when importing config directly)
load_dotenv()

# Vertex AI settings
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION")

# Local RAG (ChromaDB under LOCAL_RAG_DATA_DIR). When true, tools skip Vertex RAG APIs.
USE_LOCAL_RAG = os.environ.get("USE_LOCAL_RAG", "").lower() in ("1", "true", "yes")
_default_local_data = Path(__file__).resolve().parent.parent / "data" / "local_rag"
LOCAL_RAG_DATA_DIR = os.environ.get("LOCAL_RAG_DATA_DIR", str(_default_local_data))

# RAG settings
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 100
DEFAULT_TOP_K = 6
DEFAULT_DISTANCE_THRESHOLD = 0.5
DEFAULT_EMBEDDING_MODEL = "publishers/google/models/text-embedding-005"
DEFAULT_EMBEDDING_REQUESTS_PER_MIN = 1000
