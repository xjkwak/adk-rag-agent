const API_BASE = "/api/hub/intake";

export interface IntakeAttachmentMeta {
  filename: string;
  mimeType?: string;
  sizeBytes?: number;
}

export interface IntakeMultiInputPayload {
  text?: string;
  audio?: Blob;
  audioMimeType?: string;
  attachments?: File[];
}

export interface IntakeState {
  conversationId: string;
  status: string;
  requestType?: string;
  collectedFields?: Record<string, unknown>;
  missingFields?: string[];
  ticketPreview?: {
    summary: string;
    description: string;
    issue_type: string;
    request_type: string;
    priority?: string;
    environment?: string;
    labels?: string[];
    intake_flow?: string;
    flow_label?: string;
    time_estimate?: string;
  };
  intakeFlow?: string;
  flowLabel?: string;
  jiraIssueKey?: string;
  jiraIssueUrl?: string;
  kbAnswer?: string;
  kbConfidence?: number;
}

export interface UiHints {
  showTicketPreview?: boolean;
  showKbArticles?: boolean;
  awaitingConfirmation?: boolean;
  awaitingSolutionConfirmation?: boolean;
  showJiraCreated?: boolean;
  isComplete?: boolean;
  intakeFlow?: string;
  flowLabel?: string;
  awaitingFields?: string[];
  fieldOptions?: Record<string, { value: string; label: string }[]>;
}

export interface KbArticle {
  sourceName: string;
  sourceUri: string;
  score: number;
  excerpt: string;
}

export interface IntakeMessageResponse {
  assistantMessage: string;
  state: IntakeState;
  uiHints: UiHints;
  kbAnswer?: string;
  articles?: KbArticle[];
}

export interface SessionResponse {
  conversation_id: string;
  assistant_message: string;
  state: IntakeState;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

/** Backend Pydantic models use snake_case; normalize to frontend camelCase. */
function normalizeUiHints(raw: unknown): UiHints {
  if (!raw || typeof raw !== "object") return {};
  return raw as UiHints;
}

function normalizeMessageResponse(raw: Record<string, unknown>): IntakeMessageResponse {
  return {
    assistantMessage: String(raw.assistant_message ?? raw.assistantMessage ?? ""),
    state: (raw.state ?? {}) as IntakeState,
    uiHints: normalizeUiHints(raw.ui_hints ?? raw.uiHints),
    kbAnswer: (raw.kb_answer ?? raw.kbAnswer) as string | undefined,
    articles: raw.articles as KbArticle[] | undefined,
  };
}

export async function createIntakeSession(): Promise<SessionResponse> {
  const response = await fetch(`${API_BASE}/sessions`, { method: "POST" });
  return handleResponse<SessionResponse>(response);
}

export async function sendIntakeMessage(
  conversationId: string,
  message: string,
): Promise<IntakeMessageResponse> {
  const response = await fetch(`${API_BASE}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });
  const raw = await handleResponse<Record<string, unknown>>(response);
  return normalizeMessageResponse(raw);
}

export async function sendIntakeMultiInput(
  conversationId: string,
  payload: IntakeMultiInputPayload,
): Promise<IntakeMessageResponse> {
  const form = new FormData();
  form.append("conversation_id", conversationId);
  form.append("message", payload.text ?? "");

  if (payload.audio && payload.audioMimeType) {
    const ext = payload.audioMimeType.split("/")[1] || "webm";
    form.append("audio", payload.audio, `recording.${ext}`);
  }

  for (const file of payload.attachments ?? []) {
    form.append("attachments", file, file.name);
  }

  const response = await fetch(`${API_BASE}/message/multi`, {
    method: "POST",
    body: form,
  });
  const raw = await handleResponse<Record<string, unknown>>(response);
  return normalizeMessageResponse(raw);
}

export async function confirmIntakeTicket(
  conversationId: string,
  confirmed: boolean,
): Promise<IntakeMessageResponse> {
  const response = await fetch(`${API_BASE}/confirm-ticket`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, confirmed }),
  });
  const raw = await handleResponse<Record<string, unknown>>(response);
  return normalizeMessageResponse(raw);
}

export async function transcribeAudio(file: Blob, mimeType: string): Promise<string> {
  const form = new FormData();
  form.append("file", file, `recording.${mimeType.split("/")[1] || "webm"}`);
  const response = await fetch(`${API_BASE}/transcribe`, {
    method: "POST",
    body: form,
  });
  const data = await handleResponse<{ transcript: string }>(response);
  return data.transcript;
}
