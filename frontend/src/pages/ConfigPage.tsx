import { useCallback, useEffect, useState } from "react";
import { Loader2, Plus, RefreshCw, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
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
  resetAgentConfig,
  updateAgentConfig,
  uploadDocuments,
  type AgentConfig,
  type IndexedDocument,
} from "@/api/hubConfig";

export default function ConfigPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [agentConfig, setAgentConfig] = useState<AgentConfig | null>(null);
  const [model, setModel] = useState("");
  const [instruction, setInstruction] = useState("");
  const [defaultCorpus, setDefaultCorpus] = useState("peakrock-demo");

  const [corpusName, setCorpusName] = useState("");
  const [corpora, setCorpora] = useState<{ resource_name: string; display_name: string }[]>([]);
  const [documents, setDocuments] = useState<IndexedDocument[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [newCorpusName, setNewCorpusName] = useState("");
  const [creatingCorpus, setCreatingCorpus] = useState(false);
  const [deletingCorpus, setDeletingCorpus] = useState(false);

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
      setModel(agent.model);
      setInstruction(agent.instruction);
      setDefaultCorpus(agent.default_corpus);
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

  const handleSaveAgent = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateAgentConfig({
        model,
        instruction,
        default_corpus: defaultCorpus,
      });
      setAgentConfig(updated);
      setModel(updated.model);
      setInstruction(updated.instruction);
      setDefaultCorpus(updated.default_corpus);
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
      setModel(updated.model);
      setInstruction(updated.instruction);
      setDefaultCorpus(updated.default_corpus);
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
      <div className="max-w-4xl mx-auto p-4 md:p-8 space-y-8 pb-24">
        <div>
          <h1 className="text-2xl font-bold">Configuration</h1>
          <p className="text-muted-foreground mt-1">
            Manage indexed documents, agent instructions, and the Gemini model.
          </p>
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

        <section className="space-y-4 rounded-xl border border-border bg-card/50 p-6">
          <h2 className="text-lg font-semibold">Corpora</h2>
          <p className="text-sm text-muted-foreground">
            Chat uses the default corpus below. Create or delete corpora here; document
            uploads apply to the selected corpus.
          </p>

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
              Saved with agent settings. The chat page does not expose corpus selection.
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
        </section>

        <section className="space-y-4 rounded-xl border border-border bg-card/50 p-6">
          <h2 className="text-lg font-semibold">Knowledge base documents</h2>
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
        </section>

        <section className="space-y-4 rounded-xl border border-border bg-card/50 p-6">
          <h2 className="text-lg font-semibold">Agent model</h2>
          <div className="space-y-1 max-w-md">
            <label className="text-xs text-muted-foreground">Gemini model</label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger>
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                {agentConfig?.available_models.map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </section>

        <section className="space-y-4 rounded-xl border border-border bg-card/50 p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">Agent instruction</h2>
            <div className="flex gap-2">
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
            </div>
          </div>
          <Textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            rows={18}
            className="font-mono text-sm min-h-[320px]"
            placeholder="System instruction for the Oracle agent…"
          />
        </section>

        <div className="flex gap-3">
          <Button type="button" onClick={handleSaveAgent} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Saving…
              </>
            ) : (
              "Save configuration"
            )}
          </Button>
          <Button type="button" variant="outline" onClick={loadAll} disabled={saving}>
            Reload
          </Button>
        </div>
      </div>
    </div>
  );
}
