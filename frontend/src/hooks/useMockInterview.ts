import { useState, useRef, useCallback, useEffect } from 'react';
import { useASR } from './useASR';
import { classifyText, streamChatAnswer, fetchSession } from '../api';
import type { Utterance, QACard } from '../types';

export function useMockInterview(sessionId: string | null, onFirstQuestion?: (q: string) => void) {
  const [isRecording, setIsRecording] = useState(false);
  const [utterances, setUtterances] = useState<Utterance[]>([]);
  const [qaCards, setQaCards] = useState<QACard[]>([]);
  const abortRef = useRef(false);
  const interimIdRef = useRef<string>(`utt-${Date.now()}`);
  const firstQuestionFiredRef = useRef(false);

  // Reset state and restore history when session changes
  useEffect(() => {
    abortRef.current = true;
    setUtterances([]);
    setQaCards([]);
    setIsRecording(false);
    firstQuestionFiredRef.current = false;
    abortRef.current = false;

    if (!sessionId) return;

    fetchSession(sessionId)
      .then(data => {
        const history = data.history ?? [];
        const restored: QACard[] = [];
        for (let i = 0; i < history.length - 1; i += 2) {
          const user = history[i];
          const assistant = history[i + 1];
          if (user?.role === 'user' && assistant?.role === 'assistant') {
            restored.push({
              id: `restored-${i}`,
              question: user.content,
              answer: assistant.content,
              source: 'direct',
              phase: 'done',
            });
          }
        }
        if (restored.length > 0) {
          firstQuestionFiredRef.current = true;
          setQaCards(restored);
        }
      })
      .catch(() => {});
  }, [sessionId]);

  const triggerAnswer = useCallback((question: string) => {
    if (!sessionId || abortRef.current) return;
    if (!firstQuestionFiredRef.current) {
      firstQuestionFiredRef.current = true;
      onFirstQuestion?.(question);
    }

    const cardId = `card-${Date.now()}`;
    setQaCards(prev => [...prev, { id: cardId, question, answer: '', source: 'direct', phase: 'retrieving' }]);

    setTimeout(() => {
      if (abortRef.current) return;
      setQaCards(prev => prev.map(c => c.id === cardId ? { ...c, phase: 'generating' } : c));

      streamChatAnswer(
        sessionId,
        question,
        (chunk) => {
          if (abortRef.current) return;
          setQaCards(prev => prev.map(c => c.id === cardId ? { ...c, answer: c.answer + chunk } : c));
        },
        (source) => {
          if (abortRef.current) return;
          setQaCards(prev => prev.map(c => c.id === cardId ? { ...c, phase: 'done', source } : c));
        },
      ).catch(() => {
        setQaCards(prev => prev.map(c => c.id === cardId ? { ...c, phase: 'done' } : c));
      });
    }, 800);
  }, [sessionId, onFirstQuestion]);

  const asr = useASR(sessionId, {
    onInterim: (text) => {
      setUtterances([{ id: interimIdRef.current, text, isFinal: false }]);
    },
    onFinal: async (text) => {
      const uttId = interimIdRef.current;
      interimIdRef.current = `utt-${Date.now()}`;
      setUtterances(prev => {
        const filtered = prev.filter(u => u.id !== uttId);
        return [...filtered, { id: uttId, text, isFinal: true }];
      });
      try {
        const isQuestion = await classifyText(text);
        if (isQuestion) triggerAnswer(text);
      } catch {
        triggerAnswer(text);
      }
    },
    onError: (err) => {
      console.error('ASR error:', err);
      setIsRecording(false);
    },
  });

  const toggleRecording = useCallback(async () => {
    if (isRecording) {
      abortRef.current = true;
      asr.stop();
      setIsRecording(false);
      return;
    }
    if (!sessionId) { alert('请先点击「新建会话」'); return; }
    abortRef.current = false;
    interimIdRef.current = `utt-${Date.now()}`;
    setUtterances([]);
    setQaCards([]);
    const ok = await asr.start();
    if (ok) setIsRecording(true);
  }, [isRecording, sessionId, asr]);

  const sendTextQuestion = useCallback((question: string) => {
    if (!sessionId) { alert('请先点击「新建会话」'); return; }
    const uttId = `utt-${Date.now()}`;
    setUtterances(prev => [...prev, { id: uttId, text: question, isFinal: true }]);
    triggerAnswer(question);
  }, [sessionId, triggerAnswer]);

  return { isRecording, toggleRecording, utterances, qaCards, sendTextQuestion };
}
