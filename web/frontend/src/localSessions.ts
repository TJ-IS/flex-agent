import type { EnvMode, PromptSet } from "./types";

const STORAGE_KEY = "flex-agent:local-sessions";

export interface LocalSessionRecord {
  id: string;
  env_mode: EnvMode;
  prompt_set: PromptSet;
  language: string;
  last_opened: string;
}

function readAll(): LocalSessionRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as LocalSessionRecord[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(records: LocalSessionRecord[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}

export function listLocalSessions(): LocalSessionRecord[] {
  return readAll().sort((a, b) => b.id.localeCompare(a.id));
}

export function registerLocalSession(
  record: Omit<LocalSessionRecord, "last_opened"> & { last_opened?: string },
): void {
  const now = record.last_opened ?? new Date().toISOString();
  const next: LocalSessionRecord = {
    id: record.id,
    env_mode: record.env_mode,
    prompt_set: record.prompt_set,
    language: record.language,
    last_opened: now,
  };
  const rest = readAll().filter((item) => item.id !== next.id);
  writeAll([next, ...rest]);
}

export function removeLocalSession(sessionId: string): void {
  writeAll(readAll().filter((item) => item.id !== sessionId));
}

export function touchLocalSession(sessionId: string): void {
  const records = readAll();
  const index = records.findIndex((item) => item.id === sessionId);
  if (index < 0) return;
  const updated = { ...records[index], last_opened: new Date().toISOString() };
  const rest = records.filter((item) => item.id !== sessionId);
  writeAll([updated, ...rest]);
}
