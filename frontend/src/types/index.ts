export interface Utterance {
  id: string;
  text: string;
  isFinal: boolean;
}

export interface QACard {
  id: string;
  question: string;
  answer: string;
  source: 'kb' | 'direct';
  phase: 'retrieving' | 'generating' | 'done';
  elapsedMs?: number;
  timeToFirstToken?: number;
}

export interface Session {
  session_id: string;
  name: string;
}
