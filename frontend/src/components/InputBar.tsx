import { useRef } from 'react';

const IconMic = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
  </svg>
);
const IconKeyboard = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M8 14h8"/>
  </svg>
);
const IconSend = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
);
const IconStop = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
    <rect x="3" y="3" width="18" height="18" rx="2"/>
  </svg>
);

interface Props {
  isRecording: boolean;
  onToggleRecording: () => void;
  inputMode: 'voice' | 'text';
  onToggleInputMode: () => void;
  textInput: string;
  onTextChange: (v: string) => void;
  onSendText: () => void;
}

export default function InputBar({
  isRecording, onToggleRecording,
  inputMode, onToggleInputMode,
  textInput, onTextChange, onSendText,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSendText();
    }
  };

  return (
    <div className="input-bar">
      <div className="input-bar__mode-toggle">
        <div className="mode-toggle">
          <button
            onClick={() => inputMode !== 'voice' && onToggleInputMode()}
            className={`mode-toggle__btn${inputMode === 'voice' ? ' mode-toggle__btn--active' : ''}`}
          >
            <IconMic /> 录音
          </button>
          <button
            onClick={() => inputMode !== 'text' && onToggleInputMode()}
            className={`mode-toggle__btn${inputMode === 'text' ? ' mode-toggle__btn--active' : ''}`}
          >
            <IconKeyboard /> 打字
          </button>
        </div>
      </div>

      {inputMode === 'voice' ? (
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <button
            onClick={onToggleRecording}
            className={`record-btn ${isRecording ? 'record-btn--recording' : 'record-btn--idle'}`}
            aria-label={isRecording ? '停止录音' : '开始录音'}
          >
            {isRecording ? <IconStop /> : <span className="record-btn__dot" />}
            {isRecording ? '停止录音' : '开始录音'}
          </button>
        </div>
      ) : (
        <div className="text-input-wrap">
          <textarea
            ref={textareaRef}
            value={textInput}
            onChange={e => onTextChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入面试问题，Enter 发送，Shift+Enter 换行..."
            rows={1}
            className="text-input"
          />
          <button
            onClick={onSendText}
            disabled={!textInput.trim()}
            className={`send-btn ${textInput.trim() ? 'send-btn--active' : 'send-btn--disabled'}`}
            aria-label="发送"
          >
            <IconSend /> 发送
          </button>
        </div>
      )}
    </div>
  );
}
