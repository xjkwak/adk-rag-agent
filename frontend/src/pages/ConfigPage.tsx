import { useCallback, useEffect, useRef, useState } from "react";
import { Eye, EyeOff, Loader2, Plus, RefreshCw, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CollapsibleSection } from "@/components/CollapsibleSection";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  createCorpus,
  deleteCorpus,
  deleteDocument,
  fetchAgentConfig,
  fetchCorpora,
  fetchDocuments,
  fetchTenantProfile,
  resetAgentConfig,
  seedTenantCorpus,
  updateAgentConfig,
  uploadDocuments,
  type AgentConfig,
  type IndexedDocument,
  type TenantSummary,
} from "@/api/hubConfig";

export default function ConfigPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [agentConfig, setAgentConfig] = useState<AgentConfig | null>(null);
  const [tenant, setTenant] = useState("peakrock");
  const [model, setModel] = useState("");
  const [instruction, setInstruction] = useState("");
  const [defaultCorpus, setDefaultCorpus] = useState("peakrock-demo");
  const [provider, setProvider] = useState("gemini");
  const [openaiKey, setOpenaiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const keyInputRef = useRef<HTMLInputElement>(null);

  const [corpusName, setCorpusName] = useState("");
  const [corpora, setCorpora] = useState<{ resource_name: string; display_name: string }[]>([]);
  const [documents, setDocuments] = useState<IndexedDocument[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [newCorpusName, setNewCorpusName] = useState("");
  const [creatingCorpus, setCreatingCorpus] = useState(false);
  const [deletingCorpus, setDeletingCorpus] = useState(false);
  const [seedingTenant, setSeedingTenant] = useState(false);

  const loadDocuments = useCallback(async (name: string) => {
    if (!name) return;
    setDocsLoading(true);
    setError(null);
    try {
      const list = await fetchDocuments(name);
      setDocuments(list.files);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents");
      setDocuments([]);
    } finally {
      setDocsLoading(false);
    }
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [agent, corpusList] = await Promise.all([
        fetchAgentConfig(),
        fetchCorpora(),
      ]);
      setAgentConfig(agent);
      setTenant(agent.tenant ?? "peakrock");
      setModel(agent.model);
      setInstruction(agent.instruction);
      setDefaultCorpus(agent.default_corpus);
      setProvider(agent.provider ?? "gemini");
      setOpenaiKey("");
      setCorpora(corpusList.corpora);
      const active =
        corpusList.corpora.find((c) => c.display_name === corpusList.default_corpus)
          ?.display_name ?? corpusList.default_corpus;
      setCorpusName(active);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load configuration");
    } finally {
      setLoading(false);
    }
  }, [loadDocuments]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (corpusName) {
      loadDocuments(corpusName);
    }
  }, [corpusName, loadDocuments]);

  const activeModelList = (cfg: AgentConfig | null, prov: string) =>
    prov === "openai" ? (cfg?.openai_models ?? []) : (cfg?.available_models ?? []);

  const handleProviderChange = (next: string) => {
    setProvider(next);
    setOpenaiKey("");
    const firstModel = activeModelList(agentConfig, next)[0] ?? "";
    setModel(firstModel);
    if (next === "openai" && !agentConfig?.openai_api_key_set) {
      setTimeout(() => keyInputRef.current?.focus(), 50);
    }
  };

  const activeTenantSummary = (): TenantSummary | undefined =>
    agentConfig?.available_tenants.find((item) => item.id === tenant);

  const handleTenantChange = async (nextTenant: string) => {
    setTenant(nextTenant);
    setError(null);
    try {
      const profile = await fetchTenantProfile(nextTenant);
      setInstruction(profile.instruction);
      setDefaultCorpus(profile.default_corpus);
      setCorpusName(profile.default_corpus);
      setAgentConfig((prev) =>
        prev
          ? {
              ...prev,
              tenant: nextTenant,
              default_instruction: profile.instruction,
            }
          : prev,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tenant profile");
    }
  };

  const handleSeedTenant = async () => {
    setSeedingTenant(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await seedTenantCorpus(tenant);
      setSuccess(
        result.message ||
          `Seeded ${result.corpus_name} (${result.files_added} file(s) added).`,
      );
      const corpusList = await fetchCorpora();
      setCorpora(corpusList.corpora);
      setCorpusName(result.corpus_name);
      await loadDocuments(result.corpus_name);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to seed tenant corpus");
    } finally {
      setSeedingTenant(false);
    }
  };

  const handleSaveAgent = async () => {
    if (provider === "openai" && !openaiKey.trim() && !agentConfig?.openai_api_key_set) {
      setError("An OpenAI API key is required to use the OpenAI provider.");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateAgentConfig({
        tenant,
        model,
        instruction,
        default_corpus: defaultCorpus,
        provider,
        openai_api_key: openaiKey || undefined,
      });
      setAgentConfig(updated);
      setTenant(updated.tenant);
      setModel(updated.model);
      setInstruction(updated.instruction);
      setDefaultCorpus(updated.default_corpus);
      setProvider(updated.provider ?? "gemini");
      setOpenaiKey("");
      setSuccess("Agent settings saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save agent settings");
    } finally {
      setSaving(false);
    }
  };

  const handleResetInstruction = () => {
    if (agentConfig) {
      setInstruction(agentConfig.default_instruction);
    }
  };

  const handleResetAgent = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await resetAgentConfig();
      setAgentConfig(updated);
      setTenant(updated.tenant);
      setModel(updated.model);
      setInstruction(updated.instruction);
      setDefaultCorpus(updated.default_corpus);
      setCorpusName(updated.default_corpus);
      setProvider(updated.provider ?? "gemini");
      setOpenaiKey("");
      setSuccess("Agent settings reset to defaults.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to reset agent settings");
    } finally {
      setSaving(false);
    }
  };

  const handleUpload = async (fileList: FileList | null) => {
    if (!fileList?.length || !corpusName) return;
    setUploading(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await uploadDocuments(corpusName, Array.from(fileList));
      setSuccess(result.message || "Upload complete.");
      await loadDocuments(corpusName);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleCreateCorpus = async () => {
    const name = newCorpusName.trim();
    if (!name) return;
    setCreatingCorpus(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await createCorpus(name);
      setSuccess(result.message || `Corpus "${name}" created.`);
      setNewCorpusName("");
      const corpusList = await fetchCorpora();
      setCorpora(corpusList.corpora);
      const created =
        result.display_name ||
        corpusList.corpora.find((c) => c.display_name.includes(name))?.display_name ||
        name;
      setCorpusName(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create corpus");
    } finally {
      setCreatingCorpus(false);
    }
  };

  const handleDeleteCorpus = async () => {
    if (!corpusName) return;
    const label = corpusName;
    if (
      !confirm(
        `Delete corpus "${label}" and all indexed documents? This cannot be undone.`,
      )
    ) {
      return;
    }
    setDeletingCorpus(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await deleteCorpus(corpusName);
      setSuccess(result.message || `Corpus "${label}" deleted.`);
      const [corpusList, agent] = await Promise.all([
        fetchCorpora(),
        fetchAgentConfig(),
      ]);
      setCorpora(corpusList.corpora);
      setDefaultCorpus(agent.default_corpus);
      const next =
        corpusList.corpora.find((c) => c.display_name === agent.default_corpus)
          ?.display_name ??
        corpusList.corpora[0]?.display_name ??
        "";
      setCorpusName(next);
      setDocuments([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete corpus");
    } finally {
      setDeletingCorpus(false);
    }
  };

  const handleDeleteDoc = async (doc: IndexedDocument) => {
    if (!corpusName || !confirm(`Remove "${doc.display_name || doc.file_id}" from the index?`)) {
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      await deleteDocument(corpusName, doc.file_id);
      setSuccess("Document removed from index.");
      await loadDocuments(corpusName);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete document");
    }
  };

  const saveButton = (size: "default" | "sm" = "default") => (
    <Button type="button" onClick={handleSaveAgent} disabled={saving} size={size}>
      {saving ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
          Saving…
        </>
      ) : (
        "Save configuration"
      )}
    </Button>
  );

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />
        Loading configuration…
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto p-4 md:p-8 space-y-6 pb-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold">Configuration</h1>
            <p className="text-muted-foreground mt-1">
              Manage indexed documents, agent instructions, and the AI provider.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {saveButton()}
            <Button type="button" variant="outline" onClick={loadAll} disabled={saving}>
              Reload
            </Button>
          </div>
        </div>

        {(error || success) && (
          <div
            className={`rounded-lg border px-4 py-3 text-sm ${
              error
                ? "border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300"
                : "border-green-500/40 bg-green-500/10 text-green-800 dark:text-green-300"
            }`}
          >
            {error ?? success}
          </div>
        )}

        <CollapsibleSection
          title="Tenant profile"
          description="Select the demo tenant — sets agent instruction and default corpus."
          defaultOpen
        >
          <div className="space-y-1 max-w-md">
            <label className="text-xs text-muted-foreground">Tenant</label>
            <Select value={tenant} onValueChange={(value) => void handleTenantChange(value)}>
              <SelectTrigger>
                <SelectValue placeholder="Select tenant" />
              </SelectTrigger>
              <SelectContent>
                {(agentConfig?.available_tenants ?? []).map((item) => (
                  <SelectItem key={item.id} value={item.id}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {activeTenantSummary() && (
            <div className="space-y-3 text-sm">
              <p className="text-muted-foreground">{activeTenantSummary()?.description}</p>
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="rounded-lg border border-border/70 bg-muted/30 px-3 py-2">
                  <p className="text-xs text-muted-foreground">Default corpus</p>
                  <p className="font-medium">{activeTenantSummary()?.default_corpus}</p>
                </div>
                <div className="rounded-lg border border-border/70 bg-muted/30 px-3 py-2">
                  <p className="text-xs text-muted-foreground">Bundled assets</p>
                  <p className="font-medium">{activeTenantSummary()?.assets_path}</p>
                </div>
              </div>
              {activeTenantSummary()?.asset_files.length ? (
                <ul className="rounded-lg border border-border divide-y divide-border text-xs">
                  {activeTenantSummary()?.asset_files.map((file) => (
                    <li key={file} className="px-3 py-2 font-mono">
                      {file}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground">
                  No bundled asset files found for this tenant.
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => void handleSeedTenant()}
                  disabled={seedingTenant}
                >
                  {seedingTenant ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-1" />
                  ) : (
                    <Upload className="h-4 w-4 mr-1" />
                  )}
                  Seed corpus from assets
                </Button>
                <span className="text-xs text-muted-foreground self-center">
                  Indexes files from the tenant folder into{" "}
                  <code>{activeTenantSummary()?.default_corpus}</code>.
                </span>
              </div>
            </div>
          )}
        </CollapsibleSection>

        <CollapsibleSection
          title="Corpora"
          description="Default corpus for chat, corpus management, and creation."
          defaultOpen
        >
          <div className="space-y-1 max-w-md">
            <label className="text-xs text-muted-foreground">
              Default corpus for chat
            </label>
            <Select value={defaultCorpus} onValueChange={setDefaultCorpus}>
              <SelectTrigger>
                <SelectValue placeholder="Select default corpus" />
              </SelectTrigger>
              <SelectContent>
                {corpora.map((c) => (
                  <SelectItem key={c.resource_name} value={c.display_name}>
                    {c.display_name}
                  </SelectItem>
                ))}
                {defaultCorpus &&
                  !corpora.some((c) => c.display_name === defaultCorpus) && (
                    <SelectItem value={defaultCorpus}>{defaultCorpus}</SelectItem>
                  )}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground pt-1">
              Set automatically when you choose a tenant. Saved with agent settings.
            </p>
          </div>

          <div className="flex flex-wrap items-end gap-3 pt-2">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">
                Corpus to manage
              </label>
              <Select value={corpusName} onValueChange={setCorpusName}>
                <SelectTrigger className="w-[220px]">
                  <SelectValue placeholder="Select corpus" />
                </SelectTrigger>
                <SelectContent>
                  {corpora.map((c) => (
                    <SelectItem key={c.resource_name} value={c.display_name}>
                      {c.display_name}
                    </SelectItem>
                  ))}
                  {corpusName &&
                    !corpora.some((c) => c.display_name === corpusName) && (
                      <SelectItem value={corpusName}>{corpusName}</SelectItem>
                    )}
                </SelectContent>
              </Select>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => loadDocuments(corpusName)}
              disabled={docsLoading || !corpusName}
            >
              <RefreshCw className={`h-4 w-4 mr-1 ${docsLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={handleDeleteCorpus}
              disabled={deletingCorpus || !corpusName}
            >
              {deletingCorpus ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <Trash2 className="h-4 w-4 mr-1" />
              )}
              Delete corpus
            </Button>
          </div>

          <div className="flex flex-wrap items-end gap-2 pt-2 border-t border-border/60">
            <div className="space-y-1 flex-1 min-w-[200px] max-w-sm">
              <label className="text-xs text-muted-foreground">New corpus name</label>
              <Input
                value={newCorpusName}
                onChange={(e) => setNewCorpusName(e.target.value)}
                placeholder="e.g. my-project-demo"
                disabled={creatingCorpus}
              />
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCreateCorpus}
              disabled={creatingCorpus || !newCorpusName.trim()}
            >
              {creatingCorpus ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <Plus className="h-4 w-4 mr-1" />
              )}
              Create corpus
            </Button>
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          title="Knowledge base documents"
          description="Upload and manage indexed files for the selected corpus."
          defaultOpen={false}
        >
          {!corpusName ? (
            <p className="text-sm text-muted-foreground">
              Select or create a corpus above to manage documents.
            </p>
          ) : (
            <>

          <div className="flex flex-wrap items-center gap-3">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm hover:bg-muted">
              <Upload className="h-4 w-4" />
              {uploading ? "Uploading…" : "Upload documents"}
              <input
                type="file"
                multiple
                className="sr-only"
                disabled={uploading || !corpusName}
                onChange={(e) => {
                  handleUpload(e.target.files);
                  e.target.value = "";
                }}
              />
            </label>
            <span className="text-xs text-muted-foreground">
              PDF, Markdown, text, code, and SQL files supported in local RAG mode.
            </span>
          </div>

          {docsLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading documents…
            </div>
          ) : documents.length === 0 ? (
            <p className="text-sm text-muted-foreground py-2">
              No documents indexed in this corpus yet.
            </p>
          ) : (
            <ul className="divide-y divide-border rounded-lg border border-border">
              {documents.map((doc) => (
                <li
                  key={doc.file_id}
                  className="flex items-start justify-between gap-3 px-4 py-3 text-sm"
                >
                  <div className="min-w-0">
                    <p className="font-medium truncate">
                      {doc.display_name || doc.file_id}
                    </p>
                    {doc.source_uri && (
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {doc.source_uri}
                      </p>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="shrink-0 text-muted-foreground hover:text-destructive"
                    title="Remove from index"
                    onClick={() => handleDeleteDoc(doc)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
            </>
          )}
        </CollapsibleSection>

        <CollapsibleSection
          title="AI provider & model"
          description="Provider, API key, and model used by Chat and Support Intake."
          defaultOpen
        >
          <p className="text-sm text-muted-foreground">
            Lighter models (e.g.{" "}
            <code className="text-xs">gemini-2.0-flash-lite</code> or{" "}
            <code className="text-xs">gpt-4o-mini</code>) reduce quota usage.
          </p>

          <div className="space-y-1 max-w-md">
            <label className="text-xs text-muted-foreground">Provider</label>
            <Select value={provider} onValueChange={handleProviderChange}>
              <SelectTrigger>
                <SelectValue placeholder="Select provider" />
              </SelectTrigger>
              <SelectContent>
                {(agentConfig?.available_providers ?? [
                  { id: "gemini", label: "Gemini" },
                  { id: "openai", label: "OpenAI" },
                ]).map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* OpenAI API key — only shown when OpenAI is selected */}
          {provider === "openai" && (
            <div className="space-y-1 max-w-md">
              <label className="text-xs text-muted-foreground">
                OpenAI API key
                {agentConfig?.openai_api_key_set && (
                  <span className="ml-2 text-green-600 dark:text-green-400">
                    saved ({agentConfig.openai_api_key_hint})
                  </span>
                )}
              </label>
              <div className="relative">
                <Input
                  ref={keyInputRef}
                  type={showKey ? "text" : "password"}
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder={
                    agentConfig?.openai_api_key_set
                      ? "Leave blank to keep existing key"
                      : "sk-..."
                  }
                  className="pr-10 font-mono text-sm"
                  autoComplete="off"
                />
                <button
                  type="button"
                  onClick={() => setShowKey((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  tabIndex={-1}
                  aria-label={showKey ? "Hide key" : "Show key"}
                >
                  {showKey ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {!agentConfig?.openai_api_key_set && (
                <p className="text-xs text-muted-foreground pt-0.5">
                  Required to use OpenAI. The key is stored server-side and
                  never returned in plain text.
                </p>
              )}
            </div>
          )}

          {/* Model dropdown — provider-scoped */}
          <div className="space-y-1 max-w-md">
            <label className="text-xs text-muted-foreground">Model</label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger>
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                {activeModelList(agentConfig, provider).map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          title="Agent instruction"
          description="System prompt that guides the Oracle agent in chat."
          defaultOpen={false}
          actions={
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleResetInstruction}
              >
                Restore default text
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleResetAgent}
                disabled={saving}
              >
                Reset all agent settings
              </Button>
            </>
          }
        >
          <Textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            rows={18}
            className="font-mono text-sm min-h-[320px]"
            placeholder="System instruction for the Oracle agent…"
          />
        </CollapsibleSection>
      </div>
    </div>
  );
}
