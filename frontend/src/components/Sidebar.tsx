import { useEffect, useState } from 'react';
import KBPanel from './KBPanel';
import type { Session } from '../types';

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
      <div className="sidebar__logo">面试助手</div>

      <button className="sidebar__new-btn" onClick={onCreateSession}>
        <span style={{ fontSize: 16, lineHeight: 1 }}>+</span>
        发起新会话
      </button>

      <div className="sidebar__sessions">
        {sessions.length === 0 && <div className="sidebar__empty">暂无会话</div>}
        {sessions.map(s => {
          const isActive = s.session_id === sessionId;
          const label = s.name || s.session_id.slice(0, 12) + '...';
          return (
            <div
              key={s.session_id}
              onMouseEnter={() => setHoveredId(s.session_id)}
              onMouseLeave={() => setHoveredId(null)}
              onClick={() => onSwitchSession(s.session_id, s.name)}
              className={`session-item${isActive ? ' session-item--active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                <span style={{ fontSize: 13, flexShrink: 0 }}>💬</span>
                <span className="session-item__label">{label}</span>
              </div>
              {hoveredId === s.session_id && (
                <button
                  className="session-item__delete"
                  onClick={e => { e.stopPropagation(); onDeleteSession(s.session_id); }}
                  title="删除会话"
                >
                  ×
                </button>
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
        <span>📚</span>
        知识库管理
      </button>

      {showKB && <KBPanel />}

      <div className="sidebar__status">
        <span className={`status-dot ${backendOk ? 'status-dot--ok' : 'status-dot--err'}`} />
        <span style={{ color: backendOk ? 'var(--green)' : 'var(--red)' }}>
          {backendOk ? '服务正常' : '服务异常'}
        </span>
      </div>
    </div>
  );
}
