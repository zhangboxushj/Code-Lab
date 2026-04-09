import ReactMarkdown from 'react-markdown';
import type { QACard } from '../types';

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
  strong({ children }: { children?: React.ReactNode }) {
    return <strong>{children}</strong>;
  },
  h3({ children }: { children?: React.ReactNode }) {
    return <h3>{children}</h3>;
  },
  p({ children }: { children?: React.ReactNode }) {
    return <p>{children}</p>;
  },
  ul({ children }: { children?: React.ReactNode }) {
    return <ul>{children}</ul>;
  },
  li({ children }: { children?: React.ReactNode }) {
    return <li>{children}</li>;
  },
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
          <div style={{ fontSize: 40 }}>🎙</div>
          <div style={{ fontSize: 16, fontWeight: 500, color: 'var(--text-primary)' }}>面试助手已就绪</div>
          <div style={{ fontSize: 14 }}>
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
                <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>检索知识库中...</span>
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
