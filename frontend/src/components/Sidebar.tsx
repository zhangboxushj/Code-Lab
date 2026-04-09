import { useEffect, useState } from 'react';
import KBPanel from './KBPanel';
import { exportSessionQuestions } from '../api';
import type { Session } from '../types';

const IconPlus = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <path d="M12 5v14M5 12h14"/>
  </svg>
);
const IconChat = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
);
const IconDownload = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
);
const IconTrash = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
  </svg>
);
const IconBook = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
  </svg>
);
const IconBrain = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.46 2.5 2.5 0 0 1-1.07-4.73A3 3 0 0 1 4.5 9.5a3 3 0 0 1 .5-1.67A2.5 2.5 0 0 1 9.5 2"/>
    <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.46 2.5 2.5 0 0 0 1.07-4.73A3 3 0 0 0 19.5 9.5a3 3 0 0 0-.5-1.67A2.5 2.5 0 0 0 14.5 2"/>
  </svg>
);

interface Props {
  sessionId: string | null;
  sessions: Session[];
  onCreateSession: () => void;
  onSwitchSession: (id: string, name: string) => void;
  onDeleteSession: (id: string) => void;
  showKB: boolean;
  onToggleKB: () => void;
}

export default function Sidebar({
  sessionId, sessions,
  onCreateSession, onSwitchSession, onDeleteSession,
  showKB, onToggleKB,
}: Props) {
  const [backendOk, setBackendOk] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      fetch('/health')
        .then(r => r.json())
        .then((d: { status: string }) => { if (!cancelled) setBackendOk(d.status === 'ok'); })
        .catch(() => { if (!cancelled) { setBackendOk(false); setTimeout(check, 3000); } });
    };
    check();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="sidebar">
      <div className="sidebar__logo">
        <div className="sidebar__logo-icon">
          <IconBrain />
        </div>
        面试助手
      </div>

      <button className="sidebar__new-btn" onClick={onCreateSession}>
        <IconPlus />
        发起新会话
      </button>

      {sessions.length > 0 && <div className="sidebar__section-label">会话记录</div>}

      <div className="sidebar__sessions">
        {sessions.length === 0 && <div className="sidebar__empty">暂无会话，点击上方新建</div>}
        {sessions.map(s => {
          const isActive = s.session_id === sessionId;
          const label = s.name || s.session_id.slice(0, 14) + '...';
          return (
            <div
              key={s.session_id}
              onMouseEnter={() => setHoveredId(s.session_id)}
              onMouseLeave={() => setHoveredId(null)}
              onClick={() => onSwitchSession(s.session_id, s.name)}
              className={`session-item${isActive ? ' session-item--active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden', flex: 1 }}>
                <IconChat />
                <span className="session-item__label">{label}</span>
              </div>
              {hoveredId === s.session_id && (
                <div className="session-item__actions">
                  <button
                    className="session-item__btn"
                    onClick={e => { e.stopPropagation(); exportSessionQuestions(s.session_id); }}
                    title="导出面试题"
                    aria-label="导出面试题"
                  >
                    <IconDownload />
                  </button>
                  <button
                    className="session-item__btn session-item__btn--danger"
                    onClick={e => { e.stopPropagation(); onDeleteSession(s.session_id); }}
                    title="删除会话"
                    aria-label="删除会话"
                  >
                    <IconTrash />
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="sidebar__divider" />

      <button
        className={`sidebar__kb-btn${showKB ? ' sidebar__kb-btn--active' : ''}`}
        onClick={onToggleKB}
      >
        <IconBook />
        知识库管理
      </button>

      {showKB && <KBPanel />}

      <div className="sidebar__status">
        <span className={`status-dot ${backendOk ? 'status-dot--ok' : 'status-dot--err'}`} />
        <span>{backendOk ? '服务正常' : '服务异常'}</span>
      </div>
    </div>
  );
}
