import React, { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../store/chatStore';
import type { ProgressStatus, GenerationProgress } from '../store/chatStore';
import { DEFAULT_TENANT_ID, DEFAULT_USER_ID } from '../services/api';

type StudioMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  componentId?: string;   // ID produced by this assistant turn
  timestamp: Date;
};

const STEP_ORDER = [
  'db_session',
  'db_history',
  'llm_generation',
  'validation',
  'compilation',
  'db_save_component',
  'db_save_message',
];

function stepLabel(step: string): string {
  const labels: Record<string, string> = {
    db_session: 'Session',
    db_history: 'History',
    llm_generation: 'LLM',
    validation: 'Validate',
    compilation: 'Compile',
    db_save_component: 'Save component',
    db_save_message: 'Save message',
  };
  return labels[step] ?? step.replace(/_/g, ' ');
}

function initSteps(): GenerationProgress {
  const steps: GenerationProgress['steps'] = {};
  STEP_ORDER.forEach((s) => { steps[s] = { status: 'pending' }; });
  return { order: STEP_ORDER, steps };
}

function genId(): string {
  return `studio-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

async function consumeSSE(
  response: Response,
  onEvent: (evt: { event: string; data: Record<string, unknown> }) => void
): Promise<void> {
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sepIndex = buffer.indexOf('\n\n');
    while (sepIndex !== -1) {
      const raw = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + 2);
      let eventName = 'message';
      const dataLines: string[] = [];
      raw.split('\n').forEach((line) => {
        if (line.startsWith('event:')) eventName = line.slice('event:'.length).trim();
        if (line.startsWith('data:')) dataLines.push(line.slice('data:'.length).trim());
      });
      const dataStr = dataLines.join('\n');
      if (dataStr) {
        try {
          onEvent({ event: eventName, data: JSON.parse(dataStr) });
        } catch { /* ignore */ }
      }
      sepIndex = buffer.indexOf('\n\n');
    }
  }
}

// Compact step-by-step progress tracker matching ChatWindow style
const BuildProgress: React.FC<{ generation: GenerationProgress }> = ({ generation }) => (
  <div className="space-y-3">
    <div className="flex items-center gap-2">
      <span className="loading loading-dots loading-sm" />
      <span className="font-medium text-sm">Updating microapp…</span>
    </div>
    <div className="space-y-1.5">
      {generation.order.map((step) => {
        const info = generation.steps[step];
        const isActive = info?.status === 'active';
        const isDone = info?.status === 'done';
        const isError = info?.status === 'error';
        return (
          <div key={step} className="flex items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span
                className={[
                  'badge badge-xs',
                  isDone ? 'badge-success' : '',
                  isActive ? 'badge-warning' : '',
                  isError ? 'badge-error' : '',
                  info?.status === 'pending' ? 'badge-ghost' : '',
                ].join(' ')}
              >
                {isDone ? '✓' : isActive ? '…' : isError ? '!' : ''}
              </span>
              <span className={isActive ? 'font-semibold' : ''}>{stepLabel(step)}</span>
            </div>
            <span className="opacity-50">
              {typeof info?.ms === 'number' ? `${info.ms}ms` : ''}
            </span>
          </div>
        );
      })}
    </div>
  </div>
);

export const StudioChat: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<StudioMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [generation, setGeneration] = useState<GenerationProgress | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    sessionId,
    currentStudioComponentId,
    setCurrentStudioComponentId,
    exitStudioMode,
    revertStudio,
    canRevertStudio,
  } = useChatStore();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const updateStep = (step: string, status: ProgressStatus, ms?: number) => {
    setGeneration((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        steps: { ...prev.steps, [step]: { status, ms } },
      };
    });
  };

  const handleRevert = () => {
    revertStudio();
    setMessages((prev) => [
      ...prev,
      {
        id: genId(),
        role: 'assistant',
        content: '↩ Reverted to previous version.',
        timestamp: new Date(),
      },
    ]);
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !currentStudioComponentId) return;

    const text = input.trim();
    setInput('');
    const componentBeforeEdit = currentStudioComponentId;

    setMessages((prev) => [
      ...prev,
      { id: genId(), role: 'user', content: text, timestamp: new Date() },
    ]);

    const assistantId = genId();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: 'assistant', content: '__loading__', timestamp: new Date() },
    ]);

    setIsLoading(true);
    setGeneration(initSteps());

    let producedComponentId: string | undefined;

    try {
      const streamResp = await fetch('/api/chat/message/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': DEFAULT_TENANT_ID,
          'X-User-ID': DEFAULT_USER_ID,
        },
        body: JSON.stringify({
          session_id: sessionId,
          tenant_id: DEFAULT_TENANT_ID,
          user_id: DEFAULT_USER_ID,
          message: text,
          component_id: componentBeforeEdit,
        }),
      });

      if (!streamResp.ok) throw new Error(`Stream failed: ${streamResp.status}`);

      await consumeSSE(streamResp, (evt) => {
        if (evt.event === 'progress') {
          const { step, status, ms } = evt.data as { step?: string; status?: string; ms?: number };
          if (step && status) {
            if (status === 'start') updateStep(step, 'active');
            if (status === 'done') updateStep(step, 'done', ms);
            if (status === 'error') updateStep(step, 'error', ms);
          }
        }
        if (evt.event === 'microapp_ready') {
          const cid = (evt.data as { component_id?: string }).component_id;
          if (cid) {
            producedComponentId = cid;
            setCurrentStudioComponentId(cid);
          }
        }
        if (evt.event === 'done') {
          const data = evt.data as { content?: string };
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: data.content || 'Updated.', componentId: producedComponentId }
                : m
            )
          );
        }
        if (evt.event === 'error') {
          const msg = (evt.data as { message?: string }).message || 'An error occurred';
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: `Error: ${msg}` } : m))
          );
        }
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Request failed';
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, content: `Error: ${msg}` } : m))
      );
    } finally {
      setIsLoading(false);
      setGeneration(null);
    }
  };

  const isRevertable = canRevertStudio();

  return (
    <div className="h-full flex flex-col bg-base-100 border-l border-base-300">
      {/* Header */}
      <div className="flex-none p-3 bg-base-200 border-b border-base-300">
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-sm">✏ Edit Mode</span>
          <div className="flex gap-2">
            <button
              className="btn btn-xs btn-outline"
              onClick={handleRevert}
              disabled={!isRevertable || isLoading}
              title="Revert to previous version"
            >
              ↩ Revert
            </button>
            <button
              className="btn btn-sm btn-primary"
              onClick={exitStudioMode}
              title="Done editing — return to chat"
            >
              Done
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <div className="alert alert-info text-xs py-2">
          <span>Describe changes — layout, colors, new sections, add charts, etc.</span>
        </div>

        {messages.map((m) => {
          const isUser = m.role === 'user';
          const isLoaderMsg = m.content === '__loading__';
          return (
            <div key={m.id} className={`chat ${isUser ? 'chat-end' : 'chat-start'}`}>
              <div className="chat-image avatar">
                <div className="w-8 rounded-full bg-neutral text-neutral-content flex items-center justify-center text-xs">
                  {isUser ? '👤' : '🤖'}
                </div>
              </div>
              <div
                className={`chat-bubble text-sm ${
                  isUser ? 'chat-bubble-primary' : 'chat-bubble-secondary'
                }`}
              >
                {isLoaderMsg && generation ? (
                  <BuildProgress generation={generation} />
                ) : (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                )}
              </div>
              {/* Revert button per-assistant-message */}
              {!isUser && !isLoaderMsg && m.componentId && (
                <div className="chat-footer mt-1">
                  <button
                    className="btn btn-xs btn-ghost opacity-60 hover:opacity-100"
                    onClick={() => {
                      // Revert to the version before this message (i.e. the parent)
                      revertStudio();
                      setMessages((prev) => [
                        ...prev,
                        {
                          id: genId(),
                          role: 'assistant',
                          content: '↩ Reverted to previous version.',
                          timestamp: new Date(),
                        },
                      ]);
                    }}
                    title="Revert to the version before this change"
                  >
                    ↩ revert
                  </button>
                </div>
              )}
            </div>
          );
        })}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={sendMessage} className="flex-none p-3 border-t border-base-300">
        <div className="flex gap-2">
          <input
            type="text"
            className="input input-bordered input-sm flex-1"
            placeholder="What would you like to change?"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="btn btn-sm btn-primary"
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? <span className="loading loading-spinner loading-sm" /> : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
};
