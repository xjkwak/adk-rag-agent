"""
Knowledge HUB

A package for interacting with Google Cloud Vertex AI RAG capabilities,
or with an embedded local vector store when USE_LOCAL_RAG=1.
"""

from pathlib import Path

import vertexai
from dotenv import load_dotenv

# Load agent-local .env first, then optional cwd .env (overrides for local dev).
_env_dir = Path(__file__).resolve().parent
load_dotenv(_env_dir / ".env")
load_dotenv(override=True)

from . import config

if config.USE_LOCAL_RAG:
    print(
        "USE_LOCAL_RAG=1: skipping Vertex AI init; using local ChromaDB RAG "
        f"(data dir: {config.LOCAL_RAG_DATA_DIR})."
    )
else:
    try:
        if config.PROJECT_ID and config.LOCATION:
            print(
                f"Initializing Vertex AI with project={config.PROJECT_ID}, "
                f"location={config.LOCATION}"
            )
            vertexai.init(project=config.PROJECT_ID, location=config.LOCATION)
            print("Vertex AI initialization successful")
        else:
            print(
                f"Missing Vertex AI configuration. PROJECT_ID={config.PROJECT_ID}, "
                f"LOCATION={config.LOCATION}. Tools requiring Vertex AI may not work properly."
            )
    except Exception as e:
        print(f"Failed to initialize Vertex AI: {str(e)}")
        print(
            "Check GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION in knowledge_hub/.env, "
            "ADC (gcloud auth application-default login), and that the Vertex AI API is "
            "enabled with billing on that project. Or set USE_LOCAL_RAG=1 for offline Chroma RAG."
        )

# Import agent after initialization is complete
from . import agent
