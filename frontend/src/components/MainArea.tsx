import type { Utterance, QACard } from '../types';
import QAList from './QAList';
import InputBar from './InputBar';

interface Props {
  sessionId: string | null;
  utterances: Utterance[];
  qaCards: QACard[];
  isRecording: boolean;
  onToggleRecording: () => void;
  inputMode: 'voice' | 'text';
  onToggleInputMode: () => void;
  textInput: string;
  onTextChange: (v: string) => void;
  onSendText: () => void;
}

export default function MainArea({
  sessionId, utterances, qaCards,
  isRecording, onToggleRecording,
  inputMode, onToggleInputMode,
  textInput, onTextChange, onSendText,
}: Props) {
  if (!sessionId) {
    return (
      <div className="main">
        <div className="main__empty">
          <div className="main__empty-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <div className="main__empty-title">还没有会话</div>
          <div className="main__empty-sub">点击左侧「发起新会话」开始</div>
        </div>
      </div>
    );
  }

  return (
    <div className="main">
      {(utterances.length > 0 || isRecording) && (
        <div className="transcript-strip">
          <div className="transcript-strip__label">实时转录</div>
          {utterances.map(u => (
            <div key={u.id} className={`transcript-line ${u.isFinal ? 'transcript-line--final' : 'transcript-line--interim'}`}>
              {u.text}
            </div>
          ))}
          {isRecording && utterances.length === 0 && (
            <div className="transcript-line transcript-line--interim">正在聆听...</div>
          )}
        </div>
      )}

      <QAList qaCards={qaCards} inputMode={inputMode} />

      <InputBar
        isRecording={isRecording}
        onToggleRecording={onToggleRecording}
        inputMode={inputMode}
        onToggleInputMode={onToggleInputMode}
        textInput={textInput}
        onTextChange={onTextChange}
        onSendText={onSendText}
      />
    </div>
  );
}
