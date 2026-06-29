const API_BASE = "/api/hub/config";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : body.message ?? res.statusText;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export interface ProviderInfo {
  id: string;
  label: string;
}

export interface TenantSummary {
  id: string;
  label: string;
  description: string;
  default_corpus: string;
  assets_path: string;
  asset_files: string[];
}

export interface AgentConfig {
  tenant: string;
  available_tenants: TenantSummary[];
  model: string;
  instruction: string;
  default_instruction: string;
  available_models: string[];
  default_corpus: string;
  provider: string;
  available_providers: ProviderInfo[];
  openai_api_key_set: boolean;
  openai_api_key_hint: string;
  openai_models: string[];
}

export interface CorpusInfo {
  resource_name: string;
  display_name: string;
  create_time?: string;
  update_time?: string;
}

export interface IndexedDocument {
  file_id: string;
  display_name: string;
  source_uri: string;
  create_time?: string;
  update_time?: string;
}

export interface DocumentList {
  corpus_name: string;
  corpus_display_name: string;
  file_count: number;
  files: IndexedDocument[];
}

export function fetchAgentConfig() {
  return request<AgentConfig>("/agent");
}

export function updateAgentConfig(body: {
  tenant?: string;
  model?: string;
  instruction?: string;
  default_corpus?: string;
  provider?: string;
  openai_api_key?: string;
}) {
  return request<AgentConfig>("/agent", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function resetAgentConfig() {
  return request<AgentConfig>("/agent/reset", { method: "POST" });
}

export function fetchTenants() {
  return request<TenantSummary[]>("/tenants");
}

export function fetchTenantProfile(tenantId: string) {
  return request<TenantSummary & { instruction: string }>(
    `/tenants/${encodeURIComponent(tenantId)}`,
  );
}

export function seedTenantCorpus(tenantId: string) {
  return request<{
    status: string;
    message: string;
    tenant: string;
    corpus_name: string;
    files_added: number;
    files_skipped: number;
    chunk_count: number;
    asset_files: string[];
  }>(`/tenants/${encodeURIComponent(tenantId)}/seed`, { method: "POST" });
}

export function fetchCorpora() {
  return request<{ corpora: CorpusInfo[]; default_corpus: string }>("/corpora");
}

export function fetchDocuments(corpusName: string) {
  return request<DocumentList>(
    `/corpora/${encodeURIComponent(corpusName)}/documents`,
  );
}

export function uploadDocuments(corpusName: string, files: File[]) {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  return request<{
    status: string;
    message: string;
    files_added: number;
    invalid_paths?: string[];
  }>(`/corpora/${encodeURIComponent(corpusName)}/documents`, {
    method: "POST",
    body: form,
  });
}

export function deleteDocument(corpusName: string, documentId: string) {
  return request<{ status: string; message: string }>(
    `/corpora/${encodeURIComponent(corpusName)}/documents/${encodeURIComponent(documentId)}`,
    { method: "DELETE" },
  );
}

export function createCorpus(name: string) {
  return request<{
    status: string;
    message: string;
    corpus_name: string;
    display_name?: string;
    corpus_created?: boolean;
  }>("/corpora", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function deleteCorpus(corpusName: string) {
  return request<{
    status: string;
    message: string;
    corpus_name: string;
  }>(`/corpora/${encodeURIComponent(corpusName)}`, { method: "DELETE" });
}
