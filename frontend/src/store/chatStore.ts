import { create } from 'zustand';
import type { Message } from '../types';
import { v4 as uuidv4 } from 'uuid';

export type ProgressStatus = 'pending' | 'active' | 'done' | 'error';

export interface GenerationProgress {
  order: string[];
  steps: Record<string, { status: ProgressStatus; ms?: number }>;
}

interface ChatState {
  messages: Message[];
  sessionId: string;
  isLoading: boolean;
  error: string | null;
  generation: GenerationProgress | null;
  studioComponentId: string | null;
  studioSourceMessageId: string | null;
  currentStudioComponentId: string | null;
  // Iteration history stack — newest at end. Enables revert.
  studioHistory: string[];
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => string;
  updateMessage: (id: string, patch: Partial<Omit<Message, 'id' | 'timestamp'>>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  initGeneration: (order?: string[]) => void;
  updateGenerationStep: (step: string, status: ProgressStatus, ms?: number) => void;
  clearGeneration: () => void;
  clearMessages: () => void;
  enterStudioMode: (componentId: string, sourceMessageId: string) => void;
  exitStudioMode: () => void;
  setCurrentStudioComponentId: (id: string) => void;
  revertStudio: () => void;
  canRevertStudio: () => boolean;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  sessionId: uuidv4(),
  isLoading: false,
  error: null,
  generation: null,
  studioComponentId: null,
  studioSourceMessageId: null,
  currentStudioComponentId: null,
  studioHistory: [],
  addMessage: (message) => {
    const id = uuidv4();
    set((state) => ({
      messages: [
        ...state.messages,
        {
          ...message,
          id,
          timestamp: new Date()
        }
      ]
    }));
    return id;
  },
  updateMessage: (id, patch) =>
    set((state) => ({
      messages: state.messages.map((m) => (m.id === id ? { ...m, ...patch } : m))
    })),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  initGeneration: (order) =>
    set(() => {
      const defaultOrder = order && order.length
        ? order
        : [
          'db_session',
          'db_history',
          'llm_generation',
          'validation',
          'compilation',
          'db_save_component',
          'db_save_message'
        ];
      const steps: GenerationProgress['steps'] = {};
      defaultOrder.forEach((s) => {
        steps[s] = { status: 'pending' };
      });
      return { generation: { order: defaultOrder, steps } };
    }),
  updateGenerationStep: (step, status, ms) =>
    set((state) => {
      if (!state.generation) return {};
      return {
        generation: {
          ...state.generation,
          steps: {
            ...state.generation.steps,
            [step]: { status, ms }
          }
        }
      };
    }),
  clearGeneration: () => set({ generation: null }),
  clearMessages: () => set({
    messages: [],
    sessionId: uuidv4(),
    generation: null,
    studioComponentId: null,
    studioSourceMessageId: null,
    currentStudioComponentId: null,
    studioHistory: []
  }),
  enterStudioMode: (componentId, sourceMessageId) => set({
    studioComponentId: componentId,
    studioSourceMessageId: sourceMessageId,
    currentStudioComponentId: componentId,
    studioHistory: [componentId]
  }),
  exitStudioMode: () => {
    const { studioSourceMessageId, currentStudioComponentId } = get();
    if (studioSourceMessageId && currentStudioComponentId) {
      set((state) => ({
        messages: state.messages.map((m) =>
          m.id === studioSourceMessageId ? { ...m, componentId: currentStudioComponentId } : m
        )
      }));
    }
    set({
      studioComponentId: null,
      studioSourceMessageId: null,
      currentStudioComponentId: null,
      studioHistory: []
    });
  },
  setCurrentStudioComponentId: (id) =>
    set((state) => ({
      currentStudioComponentId: id,
      // Push new id only if it differs from the current tip
      studioHistory:
        state.studioHistory[state.studioHistory.length - 1] === id
          ? state.studioHistory
          : [...state.studioHistory, id]
    })),
  revertStudio: () => {
    const { studioHistory } = get();
    if (studioHistory.length < 2) return;
    const prev = studioHistory[studioHistory.length - 2];
    set({
      currentStudioComponentId: prev,
      studioHistory: studioHistory.slice(0, -1)
    });
  },
  canRevertStudio: () => get().studioHistory.length >= 2
}));
