import { useState, useCallback } from 'react';
import { listSessions, createSession, fetchSession, renameSession, deleteSession } from '../api';
import type { Session } from '../types';

interface UseSessionReturn {
  sessionId: string | null;
  sessionName: string;
  sessions: Session[];
  loadSessions: () => Promise<void>;
  handleCreateSession: () => Promise<void>;
  handleSwitchSession: (id: string, name: string) => void;
  handleSetSessionName: (name: string) => Promise<void>;
  handleDeleteSession: (id: string) => Promise<void>;
}

export function useSession(): UseSessionReturn {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionName, setSessionName] = useState('');
  const [sessions, setSessions] = useState<Session[]>([]);

  const loadSessions = useCallback(async () => {
    try {
      setSessions(await listSessions());
    } catch { /* backend may not be ready */ }
  }, []);

  const handleCreateSession = useCallback(async () => {
    const id = await createSession();
    setSessionId(id);
    setSessionName('');
    await loadSessions();
  }, [loadSessions]);

  const handleSetSessionName = useCallback(async (name: string) => {
    setSessionName(name);
    if (!sessionId) return;
    await renameSession(sessionId, name);
    setSessions(prev => prev.map(s => s.session_id === sessionId ? { ...s, name } : s));
  }, [sessionId]);

  const handleSwitchSession = useCallback((id: string, name: string) => {
    setSessionId(id);
    setSessionName(name);
  }, []);

  const handleDeleteSession = useCallback(async (id: string) => {
    await deleteSession(id);
    setSessions(prev => prev.filter(s => s.session_id !== id));
    if (sessionId === id) { setSessionId(null); setSessionName(''); }
  }, [sessionId]);

  return {
    sessionId, sessionName, sessions, loadSessions,
    handleCreateSession, handleSwitchSession, handleSetSessionName, handleDeleteSession,
  };
}

export { fetchSession };
