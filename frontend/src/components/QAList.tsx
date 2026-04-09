import ReactMarkdown from 'react-markdown';
import type { QACard } from '../types';

const IconSparkle = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3l1.88 5.76a1 1 0 0 0 .95.69h6.06l-4.9 3.56a1 1 0 0 0-.36 1.12L17.5 20l-4.9-3.56a1 1 0 0 0-1.18 0L6.5 20l1.87-5.87a1 1 0 0 0-.36-1.12L3.11 9.45h6.06a1 1 0 0 0 .95-.69L12 3z"/>
  </svg>
);

function SourceBadge({ source }: { source: QACard['source'] }) {
  return (
    <span className={`source-badge source-badge--${source === 'kb' ? 'kb' : 'direct'}`}>
      {source === 'kb' ? '知识库' : '直接回答'}
    </span>
  );
}

const mdComponents = {
  code({ children, className }: { children?: React.ReactNode; className?: string }) {
    const isBlock = className?.includes('language-');
    return isBlock ? (
      <pre><code style={{ fontFamily: 'var(--font-mono)' }}>{children}</code></pre>
    ) : (
      <code>{children}</code>
    );
  },
  strong({ children }: { children?: React.ReactNode }) { return <strong>{children}</strong>; },
  h3({ children }: { children?: React.ReactNode }) { return <h3>{children}</h3>; },
  p({ children }: { children?: React.ReactNode }) { return <p>{children}</p>; },
  ul({ children }: { children?: React.ReactNode }) { return <ul>{children}</ul>; },
  li({ children }: { children?: React.ReactNode }) { return <li>{children}</li>; },
};

interface Props {
  qaCards: QACard[];
  inputMode: 'voice' | 'text';
}

export default function QAList({ qaCards, inputMode }: Props) {
  if (qaCards.length === 0) {
    return (
      <div className="qa-list">
        <div className="qa-list__empty">
          <div style={{
            width: 52, height: 52, borderRadius: 14,
            background: 'var(--panel)', border: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--accent)', marginBottom: 8,
          }}>
            <IconSparkle />
          </div>
          <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-secondary)' }}>面试助手已就绪</div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            {inputMode === 'voice' ? '点击下方按钮开始录音' : '在下方输入框输入问题'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="qa-list">
      {qaCards.map(card => (
        <div key={card.id} className="qa-card">
          <div className="qa-card__row qa-card__row--question">
            <div className="qa-card__badge qa-card__badge--q">Q</div>
            <div className="qa-card__text">{card.question}</div>
          </div>

          <div className="qa-card__row">
            <div className="qa-card__badge qa-card__badge--a">A</div>
            <div className="qa-card__text">
              {card.phase === 'retrieving' && (
                <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: 13 }}>检索知识库中...</span>
              )}
              {(card.phase === 'generating' || card.phase === 'done') && (
                <div className="md-content">
                  <ReactMarkdown components={mdComponents as never}>{card.answer}</ReactMarkdown>
                  {card.phase === 'generating' && <span className="qa-card__generating" />}
                </div>
              )}
            </div>
          </div>

          {card.phase === 'done' && (
            <div className="qa-card__footer">
              <SourceBadge source={card.source} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
