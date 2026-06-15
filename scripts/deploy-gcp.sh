#!/usr/bin/env bash
# One-shot GCP deploy: Artifact Registry + GCS + Cloud Run (API + UI).
# Reads config from knowledge_hub/.env (project, Jira, Support Intake, etc.).
#
# Usage:
#   ./scripts/deploy-gcp.sh              # full deploy (setup + build + deploy)
#   ./scripts/deploy-gcp.sh --seed       # also seed corpora and sync to GCS
#   ./scripts/deploy-gcp.sh --skip-setup # skip one-time GCP provisioning
#   ./scripts/deploy-gcp.sh --skip-build # redeploy existing images only
#
# Prerequisites: gcloud, docker, authenticated ADC (gcloud auth login)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/knowledge_hub/.env}"

# Defaults (override via env or knowledge_hub/.env)
GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
AR_REPO="${AR_REPO:-knowledge-hub}"
IMAGE_TAG="${IMAGE_TAG:-$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo v1)}"
API_SERVICE="${API_SERVICE:-knowledge-hub-api}"
UI_SERVICE="${UI_SERVICE:-knowledge-hub-ui}"
LOCAL_RAG_MOUNT="${LOCAL_RAG_MOUNT:-/data/local_rag}"

SKIP_SETUP=false
SKIP_BUILD=false
DO_SEED=false

log() { printf '\n==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

load_env_file() {
  [[ -f "$ENV_FILE" ]] || die "Missing $ENV_FILE — copy knowledge_hub/.env.example and configure it."
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line//[[:space:]]/}" ]] && continue
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      val="${BASH_REMATCH[2]}"
      val="${val%\"}"; val="${val#\"}"
      val="${val%\'}"; val="${val#\'}"
      export "$key=$val"
    fi
  done < "$ENV_FILE"
}

parse_args() {
  for arg in "$@"; do
    case "$arg" in
      -h|--help) usage ;;
      --skip-setup) SKIP_SETUP=true ;;
      --skip-build) SKIP_BUILD=true ;;
      --seed) DO_SEED=true ;;
      *) die "Unknown argument: $arg (try --help)" ;;
    esac
  done
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "'$1' not found. Install it and retry."
}

detect_docker_platform() {
  if [[ "$(uname -m)" == "arm64" || "$(uname -m)" == "aarch64" ]]; then
    echo "linux/amd64"
  else
    echo ""
  fi
}

setup_gcp() {
  log "GCP one-time setup (idempotent)"
  gcloud config set project "$GOOGLE_CLOUD_PROJECT"

  gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    storage.googleapis.com \
    secretmanager.googleapis.com \
    aiplatform.googleapis.com \
    --project="$GOOGLE_CLOUD_PROJECT"

  gcloud artifacts repositories create "$AR_REPO" \
    --repository-format=docker \
    --location="$GOOGLE_CLOUD_LOCATION" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --description="Knowledge HUB images" \
    2>/dev/null || true

  gcloud iam service-accounts create knowledge-hub-runner \
    --display-name="Knowledge HUB Cloud Run" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    2>/dev/null || true

  gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
    --member="serviceAccount:${RUN_SA}" \
    --role="roles/aiplatform.user" \
    --quiet >/dev/null

  gcloud storage buckets create "gs://${RAG_BUCKET}" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --location="$GOOGLE_CLOUD_LOCATION" \
    --uniform-bucket-level-access \
    2>/dev/null || true

  gcloud storage buckets add-iam-policy-binding "gs://${RAG_BUCKET}" \
    --member="serviceAccount:${RUN_SA}" \
    --role="roles/storage.objectAdmin" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --quiet >/dev/null

  gcloud auth configure-docker "${AR_HOST}" --quiet
}

build_and_push() {
  local platform_flag=()
  local platform
  platform="$(detect_docker_platform)"
  [[ -n "$platform" ]] && platform_flag=(--platform "$platform")

  log "Building and pushing backend image (${API_IMAGE})"
  docker build "${platform_flag[@]}" -f "$REPO_ROOT/Dockerfile.backend" \
    -t "${API_IMAGE}" "$REPO_ROOT"
  docker push "${API_IMAGE}"

  log "Building and pushing frontend image (${UI_IMAGE})"
  docker build "${platform_flag[@]}" -f "$REPO_ROOT/frontend/Dockerfile" \
    -t "${UI_IMAGE}" "$REPO_ROOT"
  docker push "${UI_IMAGE}"
}

write_backend_env_file() {
  local outfile=$1
  python3 - "$outfile" <<'PY'
import os
import sys

out = sys.argv[1]
keys = [
    "USE_LOCAL_RAG",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "GOOGLE_GENAI_USE_VERTEXAI",
    "SUPPORT_KB_CORPUS",
    "STT_MODEL",
    "NLU_MODEL",
    "INTAKE_KB_CONFIDENCE_THRESHOLD",
    "UVX_COMMAND",
    "JIRA_URL",
    "JIRA_USERNAME",
    "JIRA_PROJECT_KEY",
    "JIRA_FIXED_ISSUE_KEY",
    "READ_ONLY_MODE",
]
# JIRA_API_TOKEN is mounted via Secret Manager (see sync_jira_secret), not plain env.
mount = os.environ.get("LOCAL_RAG_MOUNT", "/data/local_rag")
values = {
    "USE_LOCAL_RAG": os.environ.get("USE_LOCAL_RAG", "1"),
    "LOCAL_RAG_DATA_DIR": mount,
    "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
    "GOOGLE_CLOUD_LOCATION": os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    "GOOGLE_GENAI_USE_VERTEXAI": os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "True"),
    "SUPPORT_KB_CORPUS": os.environ.get("SUPPORT_KB_CORPUS", "support-kb"),
    "STT_MODEL": os.environ.get("STT_MODEL", "gemini-2.5-flash"),
    "NLU_MODEL": os.environ.get("NLU_MODEL", "gemini-2.5-flash"),
    "INTAKE_KB_CONFIDENCE_THRESHOLD": os.environ.get("INTAKE_KB_CONFIDENCE_THRESHOLD", "0.72"),
    "UVX_COMMAND": os.environ.get("UVX_COMMAND", "uvx"),
    "JIRA_URL": os.environ.get("JIRA_URL", ""),
    "JIRA_USERNAME": os.environ.get("JIRA_USERNAME", ""),
    "JIRA_PROJECT_KEY": os.environ.get("JIRA_PROJECT_KEY", ""),
    "JIRA_FIXED_ISSUE_KEY": os.environ.get("JIRA_FIXED_ISSUE_KEY", ""),
    "READ_ONLY_MODE": os.environ.get("READ_ONLY_MODE", "false"),
}

def yaml_quote(s: str) -> str:
    """gcloud --env-vars-file requires every value to be a YAML string."""
    s = str(s)
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

with open(out, "w", encoding="utf-8") as f:
    for key in ["USE_LOCAL_RAG", "LOCAL_RAG_DATA_DIR"] + keys[1:]:
        f.write(f"{key}: {yaml_quote(values[key])}\n")
PY
}

sync_jira_secret() {
  local secret_name="jira-api-token"
  [[ -n "${JIRA_API_TOKEN:-}" ]] || return 0

  log "Syncing JIRA_API_TOKEN to Secret Manager ($secret_name)"
  gcloud secrets create "$secret_name" \
    --replication-policy="automatic" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    2>/dev/null || true

  printf '%s' "$JIRA_API_TOKEN" | gcloud secrets versions add "$secret_name" \
    --data-file=- \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --quiet

  gcloud secrets add-iam-policy-binding "$secret_name" \
    --member="serviceAccount:${RUN_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --quiet >/dev/null 2>&1 || true
}

attach_jira_secret() {
  if [[ -n "${JIRA_API_TOKEN:-}" ]]; then
    sync_jira_secret
    log "Attaching JIRA_API_TOKEN secret to $API_SERVICE"
    gcloud run services update "$API_SERVICE" \
      --region="$GOOGLE_CLOUD_LOCATION" \
      --project="$GOOGLE_CLOUD_PROJECT" \
      --set-secrets="JIRA_API_TOKEN=jira-api-token:latest"
  else
    gcloud run services update "$API_SERVICE" \
      --region="$GOOGLE_CLOUD_LOCATION" \
      --project="$GOOGLE_CLOUD_PROJECT" \
      --remove-secrets=JIRA_API_TOKEN \
      2>/dev/null || true
  fi
}

deploy_backend() {
  local env_file
  env_file="$(mktemp)"
  trap 'rm -f "$env_file"' RETURN
  write_backend_env_file "$env_file"

  log "Deploying backend ($API_SERVICE)"
  # Note: --env-vars-file and --set-secrets cannot be used in the same gcloud deploy call.
  gcloud run deploy "$API_SERVICE" \
    --image="${API_IMAGE}" \
    --region="$GOOGLE_CLOUD_LOCATION" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --service-account="$RUN_SA" \
    --port=8080 \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --timeout=300 \
    --min-instances=0 \
    --max-instances=5 \
    --add-volume="name=rag-data,type=cloud-storage,bucket=${RAG_BUCKET}" \
    --add-volume-mount="volume=rag-data,mount-path=${LOCAL_RAG_MOUNT}" \
    --env-vars-file="$env_file"

  attach_jira_secret

  API_URL="$(gcloud run services describe "$API_SERVICE" \
    --region="$GOOGLE_CLOUD_LOCATION" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --format='value(status.url)')"
  API_UPSTREAM_HOST="$(echo "$API_URL" | sed -e 's|https://||' -e 's|http://||')"
}

deploy_frontend() {
  log "Deploying frontend ($UI_SERVICE)"
  gcloud run deploy "$UI_SERVICE" \
    --image="${UI_IMAGE}" \
    --region="$GOOGLE_CLOUD_LOCATION" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --port=8080 \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --timeout=300 \
    --set-env-vars="API_UPSTREAM_HOST=${API_UPSTREAM_HOST},API_UPSTREAM_SCHEME=https"

  UI_URL="$(gcloud run services describe "$UI_SERVICE" \
    --region="$GOOGLE_CLOUD_LOCATION" \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --format='value(status.url)')"
}

seed_corpora() {
  log "Seeding corpora locally and syncing to gs://${RAG_BUCKET}"
  local seed_dir="${REPO_ROOT}/data/local_rag"
  export USE_LOCAL_RAG=1
  export LOCAL_RAG_DATA_DIR="$seed_dir"
  mkdir -p "$seed_dir"

  if command -v uv >/dev/null 2>&1; then
    (cd "$REPO_ROOT" && uv run python scripts/seed_aegis_demo.py)
    (cd "$REPO_ROOT" && uv run python scripts/seed_peakrock_demo.py)
    (cd "$REPO_ROOT" && uv run python scripts/seed_support_kb.py)
  else
    (cd "$REPO_ROOT" && python3 scripts/seed_aegis_demo.py)
    (cd "$REPO_ROOT" && python3 scripts/seed_peakrock_demo.py)
    (cd "$REPO_ROOT" && python3 scripts/seed_support_kb.py)
  fi

  gcloud storage rsync -r "$seed_dir" "gs://${RAG_BUCKET}/"
}

main() {
  parse_args "$@"
  require_cmd gcloud
  require_cmd docker
  require_cmd python3

  load_env_file
  [[ -n "${GOOGLE_CLOUD_PROJECT:-}" ]] || die "GOOGLE_CLOUD_PROJECT not set in $ENV_FILE"

  export LOCAL_RAG_MOUNT
  RUN_SA="knowledge-hub-runner@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"
  RAG_BUCKET="${RAG_BUCKET:-${GOOGLE_CLOUD_PROJECT}-knowledge-hub-rag}"
  AR_HOST="${GOOGLE_CLOUD_LOCATION}-docker.pkg.dev"
  AR_IMAGE_PREFIX="${AR_HOST}/${GOOGLE_CLOUD_PROJECT}/${AR_REPO}"
  API_IMAGE="${AR_IMAGE_PREFIX}/${API_SERVICE}:${IMAGE_TAG}"
  UI_IMAGE="${AR_IMAGE_PREFIX}/${UI_SERVICE}:${IMAGE_TAG}"

  log "Project=$GOOGLE_CLOUD_PROJECT  Region=$GOOGLE_CLOUD_LOCATION  Tag=$IMAGE_TAG"

  if [[ "$SKIP_SETUP" == false ]]; then
    setup_gcp
  fi

  if [[ "$SKIP_BUILD" == false ]]; then
    build_and_push
  fi

  deploy_backend

  if [[ "$DO_SEED" == true ]]; then
    seed_corpora
  fi

  deploy_frontend

  log "Deployment complete"
  echo "  API:    ${API_URL}"
  echo "  UI:     ${UI_URL}/app/"
  echo "  Intake: ${UI_URL}/app/intake"
  echo ""
  echo "Tip: run with --seed on first deploy to load demo + support KB corpora."
}

main "$@"
