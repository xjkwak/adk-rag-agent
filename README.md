# Knowledge HUB

This repository contains a Google Agent Development Kit (ADK) implementation of a Retrieval Augmented Generation (RAG) agent using Google Cloud Vertex AI.

## Overview

Knowledge HUB allows you to:

- Query document corpora with natural language questions
- List available document corpora
- Create new document corpora
- Add new documents to existing corpora
- Get detailed information about specific corpora
- Delete corpora when they're no longer needed

## Prerequisites

- A Google Cloud account with billing enabled
- A Google Cloud project with the Vertex AI API enabled
- Appropriate access to create and manage Vertex AI resources
- Python 3.9+ environment

## Setting Up Google Cloud Authentication

Before running the agent, you need to set up authentication with Google Cloud:

1. **Install Google Cloud CLI**:
   - Visit [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) for installation instructions for your OS

2. **Initialize the Google Cloud CLI**:
   ```bash
   gcloud init
   ```
   This will guide you through logging in and selecting your project.

3. **Set up Application Default Credentials**:
   ```bash
   gcloud auth application-default login
   ```
   This will open a browser window for authentication and store credentials in:
   `~/.config/gcloud/application_default_credentials.json`

   After login, **attach a quota project** to those user credentials (stops the “without a quota project” warning and helps APIs attribute quota correctly):
   ```bash
   gcloud auth application-default set-quota-project YOUR_PROJECT_ID
   ```
   Use the same project ID as `GOOGLE_CLOUD_PROJECT` in `knowledge_hub/.env`. See [ADC troubleshooting for user credentials](https://cloud.google.com/docs/authentication/adc-troubleshooting/user-creds).

4. **Verify Authentication**:
   ```bash
   gcloud auth list
   gcloud config list
   ```

5. **Enable Required APIs** (if not already enabled):
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```

6. **Troubleshooting: `403 PERMISSION_DENIED` on Vertex (`generateContent`)**  
   Read the **`reason`** in the error JSON (or in logs) to see which case applies.

   **`BILLING_DISABLED`** — Vertex AI needs a **billing account linked** to the project (free tier alone is not enough for many generative API calls).  
   - Open [Google Cloud Console → Billing](https://console.cloud.google.com/billing), link a billing account to project `YOUR_PROJECT_ID`, or use the `consoleUrl` from the error payload.  
   - If you just enabled billing, wait a few minutes and retry.

   **`CONSUMER_INVALID`** — The **project ID** is wrong, the project was removed, or your Google account cannot use that project as an API consumer.  
   - Set `GOOGLE_CLOUD_PROJECT` in `knowledge_hub/.env` to a project you control.  
   - Enable the API: `gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT_ID`  
   - Refresh ADC: `gcloud auth application-default login`  
   - Set quota project: `gcloud auth application-default set-quota-project YOUR_PROJECT_ID`  
   - Ensure your user has a role such as **Vertex AI User** (or broader) on that project.

   **UserWarning: credentials … without a quota project**  
   - Run `gcloud auth application-default set-quota-project YOUR_PROJECT_ID` (same ID as in `knowledge_hub/.env`).

7. **RAG Engine: Spanner mode allowlist / “capacity limitation” when creating a corpus**  
   For new projects, **Spanner** deployment mode in regions such as `us-central1`, `us-east1`, and `us-east4` may be restricted until allowlisted. **Fix:** switch the project’s RAG Engine to **Serverless** for the same region you use in `GOOGLE_CLOUD_LOCATION`, or use another [supported region](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-overview#supported-regions).  
   - **Console:** [Vertex AI → RAG Engine](https://console.cloud.google.com/vertex-ai/rag/corpus) → select your **region** → **Switch to Serverless** (mode is shown on the page).  
   - **API / script:** see [Switching to Serverless mode](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/switching-modes#switching_to_serverless_mode) (`GetRagEngineConfig` / `UpdateRagEngineConfig`).  
   This app’s region comes from **`GOOGLE_CLOUD_LOCATION`** in `knowledge_hub/.env` (it must match the region where you configure RAG Engine).

8. **Google Drive → RAG: `500` / “internal error” / gRPC `13` on import**  
   Ingestion runs as Google’s **Vertex AI RAG Data Service Agent** for your project, **not** as your personal Google account. Share each Drive file (or parent folder) with **Viewer** access to that service account’s email.  
   - In [IAM](https://console.cloud.google.com/iam-admin/iam): enable **Include Google-provided role grants**, find **Vertex AI RAG Data Service Agent**, and copy the address (shape `service-<PROJECT_NUMBER>@gcp-sa-vertex-rag.iam.gserviceaccount.com`).  
   - **`<PROJECT_NUMBER>` is numeric** (Project settings → *Project number*). It is **not** the same string as the project id. Confirm with:  
     `gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)'`  
   - In Drive: **Share** → add that exact email → **Viewer**. Wait several minutes after sharing.  
   - Imports from **Shared drives** are unreliable for some setups; prefer **My Drive**.  
   - If Drive keeps failing: put the same bytes in **Cloud Storage** and import `gs://bucket/object` (grant the RAG agent or bucket IAM so Vertex can read the object).  
   - Native **Google Docs** sometimes ingest poorly; **File → Download → PDF** (or export to `.pdf`/`.txt`), upload, then import that file.  
   - Inspect **Cloud Logging** for the import operation; the API often returns `INTERNAL` while logs show the real cause.  
   Full context: [Use data ingestion with Vertex AI RAG Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/use-data-ingestion).

9. **Private GCS objects: `AccessDenied` in the browser / RAG import fails**  
   A URL like `https://storage.googleapis.com/BUCKET/OBJECT` returns **AccessDenied** for anonymous users when the object is **not** public. That is expected: the file is private.  
   RAG ingestion still uses **`gs://bucket/object`** (or that HTTPS form, which the app converts); Vertex reads the object using **Google-managed identities** for your project, not your personal login. Grant **Storage Object Viewer** (`roles/storage.objectViewer`) on the bucket or object to the **Vertex AI RAG Data Service Agent** for the **same** GCP project where the corpus lives (`service-<PROJECT_NUMBER>@gcp-sa-vertex-rag.iam.gserviceaccount.com`). If the bucket lives in a **different** project, add that principal in the bucket’s **IAM** (cross-project read).  
   Optional for quick tests only: make the object or bucket publicly readable (not recommended for sensitive data).

## Installation

1. **Set up a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Environment Variables**:
   
   The ADK loads configuration from the agent directory. Copy the example and edit it:
   ```bash
   cp knowledge_hub/.env.example knowledge_hub/.env
   ```
   
   Edit `knowledge_hub/.env` with your Google Cloud configuration:
   ```bash
   # Required: Your Google Cloud Project ID (must match a project where you enabled Vertex AI)
   GOOGLE_CLOUD_PROJECT=your-project-id-here
   
   # Required: Your Google Cloud region
   GOOGLE_CLOUD_LOCATION=us-central1
   
   # Routes the agent LLM through Vertex (same project as RAG tools)
   GOOGLE_GENAI_USE_VERTEXAI=True
   ```
   
   **Optional**: If you want to use alternative model providers or LiteLLM for model routing, uncomment and configure:
   ```bash
   # OpenAI API Key (if using OpenAI models)
   # OPENAI_API_KEY=your-openai-api-key-here
   
   # Anthropic API Key (if using Claude models)
   # ANTHROPIC_API_KEY=your-anthropic-api-key-here
   
   # LiteLLM Configuration
   # LITELLM_MODEL_LIST_PATH=/path/to/model_list.json
   # LITELLM_MASTER_KEY=your-litellm-master-key-here
   ```

4. **Local RAG (optional, ChromaDB — no Vertex RAG Engine)**  
   Set in `knowledge_hub/.env`:
   ```bash
   USE_LOCAL_RAG=1
   # Optional: where to store the registry + Chroma data (default: ./data/local_rag under the repo)
   # LOCAL_RAG_DATA_DIR=/path/to/my_local_rag
   ```
   When `USE_LOCAL_RAG=1`, the same tools (`list_corpora`, `create_corpus`, `add_data`, `rag_query`, `get_corpus_info`, `delete_document`, `delete_corpus`) run against an **on-disk Chroma** index. Vertex AI is **not** initialized for RAG (you still need GCP/Vertex only if the **LLM** stays on Gemini via Vertex).  
   **Ingestion in local mode:** `gs://…`, public `https://storage.googleapis.com/…` (mapped to `gs://`), `http(s)://` PDF or plain text, and **absolute local file paths**. **Google Drive / Google Docs links are not supported** in local mode.  
   Embeddings use Chroma’s default ONNX model (downloaded on first use).

## Running the Application

To start both the backend and frontend servers:

```bash
make dev
```

This command will:
- Start the ADK backend server on port 8000
- Start the React frontend development server
- Set up proxy configuration for API communication

**Alternative commands:**
- `make dev-backend` - Start only the backend server
- `make dev-frontend` - Start only the frontend server
- `make playground` - Start the ADK web playground on port 8501

## Using the Agent

The agent provides the following functionality through its tools:

### 1. Query Documents
Allows you to ask questions and get answers from your document corpus:
- Automatically retrieves relevant information from the specified corpus
- Generates informative responses based on the retrieved content

### 2. List Corpora
Shows all available document corpora in your project:
- Displays corpus names and basic information
- Helps you understand what data collections are available

### 3. Create Corpus
Create a new empty document corpus:
- Specify a custom name for your corpus
- Sets up the corpus with recommended embedding model configuration
- Prepares the corpus for document ingestion

### 4. Add New Data
Add documents to existing corpora or create new ones:
- Supports Google Drive URLs and GCS (Google Cloud Storage) paths
- Automatically creates new corpora if they don't exist

### 5. Get Corpus Information
Provides detailed information about a specific corpus:
- Shows document count, file metadata, and creation time
- Useful for understanding corpus contents and structure

### 6. Delete Corpus
Removes corpora that are no longer needed:
- Requires confirmation to prevent accidental deletion
- Permanently removes the corpus and all associated files

## Troubleshooting

If you encounter issues:

- **Authentication Problems**:
  - Run `gcloud auth application-default login` again
  - Check if your service account has the necessary permissions

- **API Errors**:
  - Ensure the Vertex AI API is enabled: `gcloud services enable aiplatform.googleapis.com`
  - Verify your project has billing enabled

- **Quota Issues**:
  - Check your Google Cloud Console for any quota limitations
  - Request quota increases if needed

- **Missing Dependencies**:
  - Ensure all requirements are installed: `pip install -r requirements.txt`

## Additional Resources

- [Vertex AI RAG Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-overview)
- [Google Agent Development Kit (ADK) Documentation](https://github.com/google/agents-framework)
- [Google Cloud Authentication Guide](https://cloud.google.com/docs/authentication)
