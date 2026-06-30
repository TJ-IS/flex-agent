import type {
  CreateSessionParams,
  SessionDetail,
  ServerEvent,
} from "./types";

const API_BASE = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function createSession(params: CreateSessionParams): Promise<SessionDetail> {
  return request<SessionDetail>("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      language: params.language,
      prompt_set: params.prompt_set,
      mode: params.mode,
      overrides: params.overrides ?? {},
    }),
  });
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  return request<SessionDetail>(`/api/sessions/${encodeURIComponent(sessionId)}`);
}

export async function deleteSession(sessionId: string): Promise<void> {
  await request<{ status: string }>(
    `/api/sessions/${encodeURIComponent(sessionId)}`,
    { method: "DELETE" },
  );
}

export async function getTaskBackground(sessionId: string): Promise<string> {
  const response = await fetch(
    `/api/sessions/${encodeURIComponent(sessionId)}/prompts/task_background.md`,
  );
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.text();
}

export async function saveTaskBackground(
  sessionId: string,
  content: string,
): Promise<void> {
  const response = await fetch(
    `/api/sessions/${encodeURIComponent(sessionId)}/prompts/task_background.md`,
    {
      method: "PUT",
      headers: { "Content-Type": "text/plain; charset=utf-8" },
      body: content,
    },
  );
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Save failed: ${response.status}`);
  }
}

export function downloadFileUrl(
  sessionId: string,
  kind: "corpus.jsonl" | "corpus_with_labels.jsonl",
): string {
  return `/api/sessions/${encodeURIComponent(sessionId)}/files/${kind}`;
}

export async function uploadFile(
  sessionId: string,
  kind: "corpus.jsonl" | "corpus_with_labels.jsonl",
  file: File,
): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(
    `/api/sessions/${encodeURIComponent(sessionId)}/files/${kind}`,
    { method: "PUT", body: form },
  );
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Upload failed: ${response.status}`);
  }
}

export function createSessionWebSocket(
  sessionId: string,
  onEvent: (event: ServerEvent) => void,
  onClose: () => void,
  onError: (error: Event) => void,
): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(
    `${protocol}//${window.location.host}/api/sessions/${encodeURIComponent(sessionId)}/stream`,
  );
  ws.onmessage = (message) => {
    try {
      const event = JSON.parse(message.data) as ServerEvent;
      onEvent(event);
    } catch {
      // ignore malformed payloads
    }
  };
  ws.onclose = () => onClose();
  ws.onerror = (error) => onError(error);
  return ws;
}

export function sendMessage(ws: WebSocket, text: string): void {
  ws.send(JSON.stringify({ type: "message", text }));
}

export function sendInterrupt(ws: WebSocket): void {
  ws.send(JSON.stringify({ type: "interrupt" }));
}

export function languageForPromptSet(promptSet: CreateSessionParams["prompt_set"]): "zh" | "en" {
  return promptSet === "baseline_en" ? "en" : "zh";
}
