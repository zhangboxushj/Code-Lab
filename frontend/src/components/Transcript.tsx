import { useEffect, useRef } from 'react';
import { theme } from '../styles/theme';
import { Utterance } from '../hooks/useMockInterview';

interface Props {
  utterances: Utterance[];
  isRecording: boolean;
}

export default function Transcript({ utterances, isRecording }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [utterances]);

  return (
    <div style={{
      flex: '0 0 40%',
      background: theme.panel,
      overflowY: 'auto',
      padding: '1rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.5rem',
    }}>
      <div style={{
        fontSize: 11,
        color: theme.textSecondary,
        textTransform: 'uppercase',
        letterSpacing: 1,
        marginBottom: 8,
      }}>
        实时转录
      </div>

      {utterances.length === 0 && !isRecording && (
        <div style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: theme.textSecondary,
          fontSize: 14,
        }}>
          点击「开始录音」开始
        </div>
      )}

      {utterances.map((u) => (
        <div
          key={u.id}
          style={{
            padding: u.isFinal ? '8px 12px' : '4px 0',
            borderRadius: u.isFinal ? 8 : 0,
            background: u.isFinal ? '#252836' : 'transparent',
            color: u.isFinal ? theme.textPrimary : theme.textInterim,
            fontStyle: u.isFinal ? 'normal' : 'italic',
            fontSize: 15,
            lineHeight: 1.6,
            transition: 'all 0.2s',
          }}
        >
          {u.text}
        </div>
      ))}

      <div ref={bottomRef} />
    </div>
  );
}
