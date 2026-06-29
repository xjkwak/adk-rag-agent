import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Send, Paperclip, X, Mic } from "lucide-react";
import { AudioInput } from "@/components/AudioInput";

export interface IntakeInputPayload {
  text?: string;
  audio?: { blob: Blob; mimeType: string };
  attachments?: File[];
}

export interface MessageAttachmentMeta {
  filename: string;
  mimeType?: string;
  sizeBytes?: number;
}

interface IntakeInputFormProps {
  onSubmit: (payload: IntakeInputPayload) => void;
  isLoading: boolean;
}

const ATTACHMENT_ACCEPT =
  ".txt,.log,.json,.csv,.md,.xml,.yaml,.yml,.pdf,.html,.htm,.out,.err";

export function IntakeInputForm({ onSubmit, isLoading }: IntakeInputFormProps) {
  const [inputValue, setInputValue] = useState("");
  const [pendingAudio, setPendingAudio] = useState<{
    blob: Blob;
    mimeType: string;
    transcript?: string;
  } | null>(null);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const hasContent =
    Boolean(inputValue.trim()) ||
    pendingAudio !== null ||
    pendingFiles.length > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasContent || isLoading) return;

    let text = inputValue.trim() || undefined;
    if (pendingAudio) {
      const transcript = (pendingAudio.transcript || "").trim();
      if (!text || text === transcript) {
        text = undefined;
      }
    }

    onSubmit({
      text,
      audio: pendingAudio
        ? { blob: pendingAudio.blob, mimeType: pendingAudio.mimeType }
        : undefined,
      attachments: pendingFiles.length > 0 ? [...pendingFiles] : undefined,
    });

    setInputValue("");
    setPendingAudio(null);
    setPendingFiles([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleAudioReady = useCallback(
    (blob: Blob, mimeType: string, transcript?: string) => {
      setPendingAudio({ blob, mimeType, transcript });
      if (transcript?.trim() && !inputValue.trim()) {
        setInputValue(transcript.trim());
      }
    },
    [inputValue],
  );

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    if (selected.length === 0) return;
    setPendingFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      const merged = [...prev];
      for (const file of selected) {
        if (!names.has(file.name)) {
          merged.push(file);
          names.add(file.name);
        }
      }
      return merged;
    });
    e.target.value = "";
  };

  const removeFile = (name: string) => {
    setPendingFiles((prev) => prev.filter((f) => f.name !== name));
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <AudioInput
          mode="combined"
          onAudioReady={handleAudioReady}
          disabled={isLoading}
        />
        <Button
          type="button"
          variant="outline"
          size="icon"
          disabled={isLoading}
          onClick={() => fileInputRef.current?.click()}
          title="Attach log or document"
          className="h-9 w-9 shrink-0"
        >
          <Paperclip className="h-4 w-4" />
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept={ATTACHMENT_ACCEPT}
          multiple
          className="hidden"
          onChange={handleFileSelect}
        />
        <span className="text-xs text-muted-foreground hidden sm:inline">
          Text, voice, and attachments can be sent together
        </span>
      </div>

      {(pendingAudio || pendingFiles.length > 0) && (
        <div className="flex flex-wrap gap-2">
          {pendingAudio && (
            <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/50 px-2 py-1 text-xs">
              <Mic className="h-3 w-3" />
              Voice note ready
              <button
                type="button"
                className="ml-1 rounded-full hover:text-destructive"
                onClick={() => setPendingAudio(null)}
                aria-label="Remove voice note"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          )}
          {pendingFiles.map((file) => (
            <span
              key={file.name}
              className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/50 px-2 py-1 text-xs max-w-[220px]"
            >
              <Paperclip className="h-3 w-3 shrink-0" />
              <span className="truncate">{file.name}</span>
              <button
                type="button"
                className="ml-1 rounded-full hover:text-destructive shrink-0"
                onClick={() => removeFile(file.name)}
                aria-label={`Remove ${file.name}`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="flex items-end space-x-3">
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your issue, attach a log, or record a voice note…"
            rows={2}
            disabled={isLoading}
            className="flex-1 resize-none min-h-[48px] rounded-xl border-border bg-background/80"
          />
        </div>
        <Button
          type="submit"
          size="icon"
          disabled={isLoading || !hasContent}
          className="w-10 h-10 rounded-full shrink-0"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </form>
  );
}
