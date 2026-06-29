import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ScrollArea } from "@/components/ui/scroll-area";
import { IntakeInputForm, type IntakeInputPayload } from "@/components/IntakeInputForm";
import { KbArticleCard } from "@/components/KbArticleCard";
import { SolutionFeedback } from "@/components/SolutionFeedback";
import { MissingFieldsPanel } from "@/components/MissingFieldsPanel";
import { TicketPreviewCard } from "@/components/TicketPreviewCard";
import { JiraCreatedBanner } from "@/components/JiraCreatedBanner";
import {
  createIntakeSession,
  sendIntakeMessage,
  sendIntakeMultiInput,
  confirmIntakeTicket,
  type IntakeState,
  type UiHints,
  type KbArticle,
  type IntakeAttachmentMeta,
} from "@/api/intake";
import { cn } from "@/utils";
import { Loader2 } from "lucide-react";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  articles?: KbArticle[];
  attachments?: IntakeAttachmentMeta[];
  hasAudio?: boolean;
}

function buildUserDisplayMessage(payload: IntakeInputPayload): string {
  const parts: string[] = [];
  if (payload.text?.trim()) {
    parts.push(payload.text.trim());
  }
  if (payload.audio) {
    parts.push("🎤 Voice note");
  }
  if (
    parts.length === 0 &&
    payload.attachments &&
    payload.attachments.length > 0
  ) {
    parts.push("Shared attachments");
  }
  return parts.join("\n");
}

function buildUserAttachmentMeta(
  payload: IntakeInputPayload,
): IntakeAttachmentMeta[] {
  return (payload.attachments ?? []).map((file) => ({
    filename: file.name,
    mimeType: file.type || undefined,
    sizeBytes: file.size,
  }));
}

const SCROLL_NEAR_BOTTOM_PX = 80;

function getScrollViewport(container: HTMLElement | null): HTMLElement | null {
  if (!container) return null;
  return container.querySelector<HTMLElement>('[data-slot="scroll-area-viewport"]');
}

function isNearBottom(viewport: HTMLElement): boolean {
  const distance =
    viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
  return distance <= SCROLL_NEAR_BOTTOM_PX;
}

export default function IntakePage() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [state, setState] = useState<IntakeState | null>(null);
  const [uiHints, setUiHints] = useState<UiHints>({});
  const [isLoading, setIsLoading] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollRef = useRef(true);

  const scrollToBottom = useCallback((force = false) => {
    const viewport = getScrollViewport(scrollAreaRef.current);
    if (!viewport) return;
    if (force || shouldAutoScrollRef.current) {
      viewport.scrollTop = viewport.scrollHeight;
    }
  }, []);

  useEffect(() => {
    if (!conversationId) return;

    let viewport: HTMLElement | null = null;
    let rafId = 0;

    const onScroll = () => {
      if (viewport) {
        shouldAutoScrollRef.current = isNearBottom(viewport);
      }
    };

    const attach = () => {
      viewport = getScrollViewport(scrollAreaRef.current);
      if (!viewport) {
        rafId = requestAnimationFrame(attach);
        return;
      }
      viewport.addEventListener("scroll", onScroll, { passive: true });
    };

    attach();

    return () => {
      cancelAnimationFrame(rafId);
      viewport?.removeEventListener("scroll", onScroll);
    };
  }, [conversationId]);

  useEffect(() => {
    requestAnimationFrame(() => scrollToBottom(false));
  }, [messages, uiHints, isLoading, scrollToBottom]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const session = await createIntakeSession();
        if (cancelled) return;
        setConversationId(session.conversation_id);
        setState(session.state);
        setMessages([
          {
            id: "opening",
            role: "assistant",
            content: session.assistant_message,
          },
        ]);
      } catch (e) {
        if (!cancelled) {
          setInitError(e instanceof Error ? e.message : "Failed to start session");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const applyResponse = useCallback(
    (
      assistantMessage: string,
      newState: IntakeState,
      hints: UiHints,
      articles?: KbArticle[],
    ) => {
      setState(newState);
      setUiHints(hints ?? {});
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content: assistantMessage,
          articles,
        },
      ]);
    },
    [],
  );

  const handleSend = useCallback(
    async (payload: IntakeInputPayload | string) => {
      if (!conversationId || isLoading) return;

      const normalized: IntakeInputPayload =
        typeof payload === "string" ? { text: payload } : payload;

      const hasMultiInput =
        Boolean(normalized.audio) ||
        Boolean(normalized.attachments && normalized.attachments.length > 0);

      if (
        !normalized.text?.trim() &&
        !normalized.audio &&
        !(normalized.attachments && normalized.attachments.length > 0)
      ) {
        return;
      }

      shouldAutoScrollRef.current = true;
      setIsLoading(true);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString() + "-u",
          role: "user",
          content: buildUserDisplayMessage(normalized),
          attachments: buildUserAttachmentMeta(normalized),
          hasAudio: Boolean(normalized.audio),
        },
      ]);
      try {
        const resp = hasMultiInput
          ? await sendIntakeMultiInput(conversationId, {
              text: normalized.text,
              audio: normalized.audio?.blob,
              audioMimeType: normalized.audio?.mimeType,
              attachments: normalized.attachments,
            })
          : await sendIntakeMessage(conversationId, normalized.text!.trim());
        applyResponse(resp.assistantMessage, resp.state, resp.uiHints, resp.articles);
      } catch (e) {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString() + "-err",
            role: "assistant",
            content: `Error: ${e instanceof Error ? e.message : "Something went wrong"}`,
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [conversationId, isLoading, applyResponse],
  );

  const handleSolutionFeedback = useCallback(
    (resolved: boolean) => {
      void handleSend(resolved ? "yes, that resolved my issue" : "no, it didn't work");
    },
    [handleSend],
  );

  const handleConfirmTicket = useCallback(async () => {
    if (!conversationId || isLoading) return;
    shouldAutoScrollRef.current = true;
    setIsLoading(true);
    try {
      const resp = await confirmIntakeTicket(conversationId, true);
      applyResponse(resp.assistantMessage, resp.state, resp.uiHints, resp.articles);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString() + "-err",
          role: "assistant",
          content: `Error creating ticket: ${e instanceof Error ? e.message : "Unknown error"}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, isLoading, applyResponse]);

  const handleCancelTicket = useCallback(async () => {
    if (!conversationId || isLoading) return;
    setIsLoading(true);
    try {
      const resp = await confirmIntakeTicket(conversationId, false);
      applyResponse(resp.assistantMessage, resp.state, resp.uiHints);
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, isLoading, applyResponse]);

  if (initError) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-destructive">
        {initError}
      </div>
    );
  }

  if (!conversationId) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div ref={scrollAreaRef} className="flex-1 min-h-0 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="max-w-3xl mx-auto space-y-4 px-4 py-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "rounded-xl px-4 py-3 text-sm",
                msg.role === "user"
                  ? "ml-8 bg-primary text-primary-foreground"
                  : "mr-8 bg-muted/60 border border-border",
              )}
            >
              {msg.role === "assistant" ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
              ) : (
                <div className="space-y-2">
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.attachments && msg.attachments.length > 0 && (
                    <ul className="text-xs opacity-90 space-y-1">
                      {msg.attachments.map((file) => (
                        <li key={file.filename}>📎 {file.filename}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
              {msg.articles && msg.articles.length > 0 && (
                <KbArticleCard articles={msg.articles} />
              )}
            </div>
          ))}

          {uiHints?.awaitingFields &&
            uiHints.awaitingFields.length > 0 &&
            !isLoading &&
            !uiHints.awaitingSolutionConfirmation &&
            !uiHints.showTicketPreview && (
              <MissingFieldsPanel
                awaitingFields={uiHints.awaitingFields}
                fieldOptions={uiHints.fieldOptions}
                onSubmit={(msg) => void handleSend(msg)}
                disabled={isLoading}
              />
            )}

          {uiHints?.awaitingSolutionConfirmation && !isLoading && (
            <SolutionFeedback
              onYes={() => handleSolutionFeedback(true)}
              onNo={() => handleSolutionFeedback(false)}
            />
          )}

          {uiHints?.showTicketPreview && state?.ticketPreview && (
            <TicketPreviewCard
              preview={state.ticketPreview}
              onConfirm={() => void handleConfirmTicket()}
              onCancel={() => void handleCancelTicket()}
              disabled={isLoading}
            />
          )}

          {state?.jiraIssueKey && state.jiraIssueUrl && (
            <JiraCreatedBanner
              issueKey={state.jiraIssueKey}
              issueUrl={state.jiraIssueUrl}
            />
          )}

          {isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="h-4 w-4 animate-spin" /> Processing…
            </div>
          )}
          </div>
        </ScrollArea>
      </div>

      <div className="shrink-0 border-t border-border p-4 pb-4 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="max-w-3xl mx-auto">
          <IntakeInputForm
            onSubmit={(payload) => void handleSend(payload)}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
}
