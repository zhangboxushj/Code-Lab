import { useRef } from 'react';

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
          {(['voice', 'text'] as const).map(mode => (
            <button
              key={mode}
              onClick={() => inputMode !== mode && onToggleInputMode()}
              className={`mode-toggle__btn${inputMode === mode ? ' mode-toggle__btn--active' : ''}`}
            >
              {mode === 'voice' ? '🎙 录音' : '⌨ 打字'}
            </button>
          ))}
        </div>
      </div>

      {inputMode === 'voice' ? (
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <button
            onClick={onToggleRecording}
            className={`record-btn ${isRecording ? 'record-btn--recording' : 'record-btn--idle'}`}
          >
            <span className="record-btn__dot" />
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
            placeholder="输入面试问题，按 Enter 发送..."
            rows={1}
            className="text-input"
          />
          <button
            onClick={onSendText}
            disabled={!textInput.trim()}
            className={`send-btn ${textInput.trim() ? 'send-btn--active' : 'send-btn--disabled'}`}
          >
            发送
          </button>
        </div>
      )}
    </div>
  );
}
