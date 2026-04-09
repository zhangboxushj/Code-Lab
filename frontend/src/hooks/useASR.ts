import { useRef, useCallback } from 'react';

const ASR_WS_URL = 'ws://localhost:8001/ws/asr';
const SAMPLE_RATE = 16000;


interface ASRCallbacks {
  onInterim: (text: string) => void;
  onFinal: (text: string) => void;
  onError: (err: string) => void;
}

export function useASR(sessionId: string | null, callbacks: ASRCallbacks) {
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const startingRef = useRef(false);
  const readyRef = useRef(false); // true after backend sends "ready"

  const stop = useCallback(() => {
    startingRef.current = false;
    readyRef.current = false;
    processorRef.current?.disconnect();
    processorRef.current = null;
    audioCtxRef.current?.close();
    audioCtxRef.current = null;
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ end: true }));
      }
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const start = useCallback(async () => {
    if (!sessionId) {
      callbacks.onError('请先新建会话');
      return false;
    }
    if (startingRef.current || wsRef.current) return false;
    startingRef.current = true;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
        video: false,
      });
      streamRef.current = stream;

      const ws = new WebSocket(`${ASR_WS_URL}?session_id=${sessionId}`);
      wsRef.current = ws;

      // Setup AudioContext (but don't connect yet)
      const audioCtx = new AudioContext({ sampleRate: SAMPLE_RATE });
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const bufferSize = 2048; // must be power of 2
      const processor = audioCtx.createScriptProcessor(bufferSize, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        // Only send audio after backend signals ready
        if (!readyRef.current || ws.readyState !== WebSocket.OPEN) return;
        const float32 = e.inputBuffer.getChannelData(0);
        const int16 = new Int16Array(float32.length);
        for (let i = 0; i < float32.length; i++) {
          int16[i] = Math.max(-32768, Math.min(32767, float32[i] * 32768));
        }
        ws.send(int16.buffer);
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data as string) as {
          type: string;
          text?: string;
          is_final?: boolean;
        };
        if (msg.type === 'ready') {
          // Backend ASR connection established, start sending audio
          readyRef.current = true;
          console.log('[ASR] backend ready, starting audio stream');
        } else if (msg.type === 'transcript') {
          if (msg.is_final) {
            callbacks.onFinal(msg.text ?? '');
          } else {
            callbacks.onInterim(msg.text ?? '');
          }
        } else if (msg.type === 'error') {
          callbacks.onError(msg.text ?? 'ASR error');
        }
      };

      ws.onerror = () => callbacks.onError('ASR WebSocket 连接失败');
      ws.onclose = () => { readyRef.current = false; };

      stream.getAudioTracks()[0].onended = () => stop();

      startingRef.current = false;
      return true;
    } catch (err) {
      stop();
      callbacks.onError(err instanceof Error ? err.message : 'ASR 启动失败');
      return false;
    }
  }, [sessionId, callbacks, stop]);

  return { start, stop };
}
