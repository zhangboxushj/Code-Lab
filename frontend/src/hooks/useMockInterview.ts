import { useState, useRef, useCallback, useEffect } from 'react';
import { useASR } from './useASR';
import { classifyText, streamChatAnswer, fetchSession } from '../api';
import type { Utterance, QACard } from '../types';

const SILENCE_WINDOW_MS = 1500;

export function useMockInterview(sessionId: string | null, onFirstQuestion?: (q: string) => void) {
  const [isRecording, setIsRecording] = useState(false);
  const [utterances, setUtterances] = useState<Utterance[]>([]);
  const [qaCards, setQaCards] = useState<QACard[]>([]);
  const abortRef = useRef(false);
  const interimIdRef = useRef<string>(`utt-${Date.now()}`);
  const firstQuestionFiredRef = useRef(false);

  // ASR fragment merging state
  const pendingFragmentsRef = useRef<string[]>([]);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingClassifyRef = useRef<{ text: string; promise: Promise<boolean>; cancel: () => void } | null>(null);

  const clearSilenceTimer = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  };

  // Reset state and restore history when session changes
  useEffect(() => {
    abortRef.current = true;
    clearSilenceTimer();
    pendingFragmentsRef.current = [];
    pendingClassifyRef.current = null;
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

    if (abortRef.current) return;

    streamChatAnswer(
      sessionId,
      question,
      (chunk) => {
        if (abortRef.current) return;
        setQaCards(prev => prev.map(c => c.id === cardId
          ? { ...c, phase: 'generating', answer: c.answer + chunk }
          : c));
      },
      (source, elapsedMs, timeToFirstToken) => {
        if (abortRef.current) return;
        setQaCards(prev => prev.map(c => c.id === cardId ? { ...c, phase: 'done', source, elapsedMs, timeToFirstToken } : c));
      },
    ).catch(() => {
      setQaCards(prev => prev.map(c => c.id === cardId ? { ...c, phase: 'done' } : c));
    });
  }, [sessionId, onFirstQuestion]);

  // Called when silence window expires — use pending classify result or re-classify merged text
  const flushFragments = useCallback(async () => {
    const mergedText = pendingFragmentsRef.current.join('');
    pendingFragmentsRef.current = [];
    const pending = pendingClassifyRef.current;
    pendingClassifyRef.current = null;

    if (!mergedText.trim() || abortRef.current) return;

    try {
      let isQuestion: boolean;
      if (pending && pending.text === mergedText) {
        // Reuse in-flight classify result — no extra latency
        isQuestion = await pending.promise;
      } else {
        // Fragments were merged, need fresh classify
        pending?.cancel();
        isQuestion = await classifyText(mergedText);
      }
      if (isQuestion && !abortRef.current) triggerAnswer(mergedText);
    } catch {
      if (!abortRef.current) triggerAnswer(mergedText);
    }
  }, [triggerAnswer]);

  const asr = useASR(sessionId, {
    onInterim: (text) => {
      setUtterances([{ id: interimIdRef.current, text, isFinal: false }]);
    },
    onFinal: (text) => {
      const uttId = interimIdRef.current;
      interimIdRef.current = `utt-${Date.now()}`;
      setUtterances(prev => {
        const filtered = prev.filter(u => u.id !== uttId);
        return [...filtered, { id: uttId, text, isFinal: true }];
      });

      // Accumulate fragment
      pendingFragmentsRef.current.push(text);
      const mergedSoFar = pendingFragmentsRef.current.join('');

      // Cancel previous pending classify (text has changed)
      pendingClassifyRef.current?.cancel();

      // Start classify in parallel with silence window
      let cancelled = false;
      const promise = classifyText(mergedSoFar).catch(() => false) as Promise<boolean>;
      pendingClassifyRef.current = {
        text: mergedSoFar,
        promise,
        cancel: () => { cancelled = true; },
      };
      // Suppress result if cancelled
      promise.then(result => {
        if (cancelled) return result;
        return result;
      });

      // Reset silence timer
      clearSilenceTimer();
      silenceTimerRef.current = setTimeout(() => {
        flushFragments();
      }, SILENCE_WINDOW_MS);
    },
    onError: (err) => {
      console.error('ASR error:', err);
      setIsRecording(false);
    },
  });

  const toggleRecording = useCallback(async () => {
    if (isRecording) {
      abortRef.current = true;
      clearSilenceTimer();
      pendingFragmentsRef.current = [];
      pendingClassifyRef.current = null;
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

