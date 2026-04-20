import { useState, useRef } from 'react';
import { useChatStore } from '../store/chatStore';
import { chatAPI, DEFAULT_TENANT_ID, DEFAULT_USER_ID } from '../services/api';

type StreamEvent =
  | { event: 'progress'; data: { step: string; status: 'start' | 'done' | 'error'; ms?: number } }
  | { event: 'microapp_ready'; data: { component_id?: string; parent_component_id?: string } }
  | { event: 'done'; data: { type: 'text' | 'component'; content: string; component_id?: string; reasoning?: string; timing?: Record<string, number> } }
  | { event: 'error'; data: { message: string } };

function stepLabel(step: string): string {
  switch (step) {
    case 'db_session':
      return 'Session';
    case 'db_history':
      return 'History';
    case 'llm_generation':
      return 'LLM';
    case 'validation':
      return 'Validate';
    case 'compilation':
      return 'Compile';
    case 'db_save_component':
      return 'Save component';
    case 'db_save_message':
      return 'Save message';
    default:
      return step;
  }
}

async function consumeSSE(
  response: Response,
  onEvent: (evt: StreamEvent) => void
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
          const parsed = JSON.parse(dataStr);
          onEvent({ event: eventName as StreamEvent['event'], data: parsed } as StreamEvent);
        } catch {
          // ignore malformed chunks
        }
      }

      sepIndex = buffer.indexOf('\n\n');
    }
  }
}

export const useChat = () => {
  const {
    sessionId,
    activeComponentId,
    addMessage,
    updateMessage,
    setLoading,
    setError,
    setActiveComponentId,
    isLoading,
    initGeneration,
    updateGenerationStep,
    clearGeneration
  } = useChatStore();
  const [retrying, setRetrying] = useState(false);
  /** True when this stream is an iteration — assistant bubble stays text-only; parent bubble gets iframe swap */
  const iterationRef = useRef(false);

  const sendMessage = async (message: string) => {
    if (!message.trim() || isLoading) return;

    iterationRef.current = false;

    addMessage({
      role: 'user',
      content: message
    });

    setLoading(true);
    setError(null);
    initGeneration();

    const assistantMessageId = addMessage({
      role: 'assistant',
      content: 'Building your microapp…'
    });

    const iteratingFrom = activeComponentId;
    const body: Record<string, string> = {
      session_id: sessionId,
      tenant_id: DEFAULT_TENANT_ID,
      user_id: DEFAULT_USER_ID,
      message
    };
    if (iteratingFrom) {
      body.component_id = iteratingFrom;
    }

    try {
      const streamResp = await fetch('/api/chat/message/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': DEFAULT_TENANT_ID,
          'X-User-ID': DEFAULT_USER_ID,
        },
        body: JSON.stringify(body)
      });

      if (!streamResp.ok) {
        throw new Error(`Stream request failed: ${streamResp.status}`);
      }

      await consumeSSE(streamResp, (evt) => {
        if (evt.event === 'progress') {
          const { step, status, ms } = evt.data;
          if (status === 'start') updateGenerationStep(step, 'active');
          if (status === 'done') updateGenerationStep(step, 'done', ms);
          if (status === 'error') updateGenerationStep(step, 'error', ms);
          updateMessage(assistantMessageId, { content: `Building your microapp… (${stepLabel(step)})` });
        }

        if (evt.event === 'microapp_ready') {
          const { component_id: cid, parent_component_id: parentId } = evt.data;
          if (cid) {
            setActiveComponentId(cid);
          }
          if (parentId && cid) {
            iterationRef.current = true;
            const parentMsg = useChatStore.getState().messages.find(
              (m) => m.componentId === parentId
            );
            if (parentMsg) {
              updateMessage(parentMsg.id, { componentId: cid });
            }
          } else if (cid) {
            updateMessage(assistantMessageId, { componentId: cid });
          }
        }

        if (evt.event === 'done') {
          const patch: {
            content: string;
            componentId?: string;
            reasoning?: string;
          } = {
            content: evt.data.content,
            reasoning: evt.data.reasoning
          };
          if (!iterationRef.current && evt.data.component_id) {
            patch.componentId = evt.data.component_id;
          }
          updateMessage(assistantMessageId, patch);
        }

        if (evt.event === 'error') {
          throw new Error(evt.data.message);
        }
      });
    } catch (error) {
      try {
        const response = await chatAPI.sendMessage(sessionId, message, iteratingFrom ?? undefined);
        const cid = response.component_id ? String(response.component_id) : undefined;
        if (iteratingFrom && cid) {
          const parentMsg = useChatStore.getState().messages.find(
            (m) => m.componentId === iteratingFrom
          );
          if (parentMsg) {
            updateMessage(parentMsg.id, { componentId: cid });
          }
          setActiveComponentId(cid);
          updateMessage(assistantMessageId, {
            content: response.content,
            reasoning: response.reasoning
          });
        } else {
          updateMessage(assistantMessageId, {
            content: response.content,
            componentId: cid,
            reasoning: response.reasoning
          });
          if (cid) {
            setActiveComponentId(cid);
          }
        }
        return;
      } catch (fallbackError) {
        const errorMessage =
          fallbackError instanceof Error ? fallbackError.message : 'An error occurred';
        setError(errorMessage);
        updateMessage(assistantMessageId, {
          content: `Error: ${errorMessage}. Please try again.`
        });
        return;
      }
    } finally {
      setLoading(false);
      clearGeneration();
    }
  };

  const retry = async (lastMessage: string) => {
    setRetrying(true);
    await sendMessage(lastMessage);
    setRetrying(false);
  };

  return {
    sendMessage,
    retry,
    isLoading,
    retrying
  };
};
