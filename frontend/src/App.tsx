import { useState, useRef, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import MainArea from './components/MainArea';
import { useMockInterview } from './hooks/useMockInterview';
import { useSession } from './hooks/useSession';

export default function App() {
  const {
    sessionId, sessionName, sessions, loadSessions,
    handleCreateSession, handleSwitchSession, handleSetSessionName, handleDeleteSession,
  } = useSession();

  const namedRef = useRef(false);
  const [inputMode, setInputMode] = useState<'voice' | 'text'>('voice');
  const [textInput, setTextInput] = useState('');
  const [showKB, setShowKB] = useState(false);

  useEffect(() => { loadSessions(); }, []);

  const handleFirstQuestion = (firstQ: string) => {
    if (!namedRef.current) {
      namedRef.current = true;
      handleSetSessionName(firstQ.slice(0, 30));
    }
  };

  const onCreateSession = async () => {
    namedRef.current = false;
    await handleCreateSession();
  };

  const onSwitchSession = (id: string, name: string) => {
    namedRef.current = !!name;
    handleSwitchSession(id, name);
  };

  const { isRecording, toggleRecording, utterances, qaCards, sendTextQuestion } =
    useMockInterview(sessionId, handleFirstQuestion);

  const handleSendText = () => {
    if (!textInput.trim()) return;
    sendTextQuestion(textInput.trim());
    setTextInput('');
  };

  return (
    <div className="app">
      <Sidebar
        sessionId={sessionId}
        sessions={sessions}
        onCreateSession={onCreateSession}
        onSwitchSession={onSwitchSession}
        onDeleteSession={handleDeleteSession}
        showKB={showKB}
        onToggleKB={() => setShowKB(v => !v)}
      />
      <MainArea
        sessionId={sessionId}
        utterances={utterances}
        qaCards={qaCards}
        isRecording={isRecording}
        onToggleRecording={toggleRecording}
        inputMode={inputMode}
        onToggleInputMode={() => setInputMode(m => m === 'voice' ? 'text' : 'voice')}
        textInput={textInput}
        onTextChange={setTextInput}
        onSendText={handleSendText}
      />
    </div>
  );
}
