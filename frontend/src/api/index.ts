import type { Session, QACard } from '../types';

// --- Session API ---

export async function listSessions(): Promise<Session[]> {
  const res = await fetch('/api/session');
  const data = await res.json() as { sessions: Session[] };
  return data.sessions;
}

export async function createSession(): Promise<string> {
  const res = await fetch('/api/session', { method: 'POST' });
  const data = await res.json() as { session_id: string };
  return data.session_id;
}

export async function fetchSession(id: string): Promise<{ history: { role: string; content: string }[]; name: string }> {
  const res = await fetch(`/api/session/${id}`);
  return res.json();
}

export async function renameSession(id: string, name: string): Promise<void> {
  await fetch(`/api/session/${id}/name`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
}

export async function deleteSession(id: string): Promise<void> {
  await fetch(`/api/session/${id}`, { method: 'DELETE' });
}

// --- Chat API ---

export async function classifyText(text: string): Promise<boolean> {
  const res = await fetch(`/api/chat/classify?text=${encodeURIComponent(text)}`);
  const data = await res.json() as { is_question: boolean };
  return data.is_question;
}

export async function streamChatAnswer(
  sessionId: string,
  question: string,
  onChunk: (text: string) => void,
  onDone: (source: QACard['source']) => void,
): Promise<void> {
  const url = `/api/chat/stream?session_id=${encodeURIComponent(sessionId)}&message=${encodeURIComponent(question)}`;
  const resp = await fetch(url);
  if (!resp.ok || !resp.body) { onDone('direct'); return; }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      const msg = JSON.parse(payload) as { type: string; text?: string; source?: string };
      if (msg.type === 'chunk' && msg.text) onChunk(msg.text);
      else if (msg.type === 'done') onDone((msg.source as QACard['source']) ?? 'direct');
    }
  }
}

// --- Knowledge Base API ---

export async function listKBFiles(): Promise<string[]> {
  const res = await fetch('/api/kb/list');
  const data = await res.json() as { files: string[] };
  return data.files;
}

export async function uploadKBFile(file: File): Promise<{ filename: string; chunks: number }> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch('/api/kb/upload', { method: 'POST', body: form });
  return res.json();
}

export async function deleteKBFile(filename: string): Promise<void> {
  await fetch(`/api/kb/file/${encodeURIComponent(filename)}`, { method: 'DELETE' });
}
