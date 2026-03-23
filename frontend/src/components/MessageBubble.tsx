import React, { useMemo } from 'react';
import type { Message } from '../types';
import { MicroappIframe } from './MicroappIframe';
import { componentAPI } from '../services/api';
import { useChatStore } from '../store/chatStore';
import { usePinStore } from '../store/pinStore';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const enterStudioMode = useChatStore((s) => s.enterStudioMode);
  const pinComponent = usePinStore((s) => s.pinComponent);
  const pinnedApps = usePinStore((s) => s.pinnedApps);
  const isUser = message.role === 'user';

  const isPinned = useMemo(
    () =>
      !!message.componentId &&
      pinnedApps.some((p) => p.component_id === message.componentId),
    [message.componentId, pinnedApps]
  );

  const handleFeedback = async (rating: 1 | 5) => {
    if (message.componentId) {
      try {
        await componentAPI.submitFeedback(message.componentId, rating);
        alert(rating === 5 ? 'Thanks for your feedback!' : 'Thanks, we\'ll improve it!');
      } catch (error) {
        console.error('Failed to submit feedback:', error);
      }
    }
  };

  const handlePinClick = () => {
    if (!message.componentId) return;
    const defaultName =
      message.content?.trim().slice(0, 80) || `App ${message.componentId.slice(0, 8)}`;
    const slot = window.prompt('Pin name (shown in nav)', defaultName);
    if (!slot?.trim()) return;
    void pinComponent(message.componentId, slot.trim()).catch(() => {});
  };

  const handleSparkPinned = (detail: {
    componentId: string;
    slotName: string;
    meta?: Record<string, unknown>;
  }) => {
    if (!message.componentId || detail.componentId !== message.componentId) return;
    void pinComponent(detail.componentId, detail.slotName, { metadata: detail.meta }).catch(() => {});
  };

  return (
    <div className={`chat ${isUser ? 'chat-end' : 'chat-start'} message-bubble`}>
      <div className="chat-image avatar">
        <div className="w-10 rounded-full bg-neutral text-neutral-content flex items-center justify-center">
          {isUser ? '👤' : '🤖'}
        </div>
      </div>
      <div className="chat-header mb-1">
        {isUser ? 'You' : 'Spark AI'}
        <time className="text-xs opacity-50 ml-2">
          {message.timestamp.toLocaleTimeString()}
        </time>
      </div>
      <div className={`chat-bubble ${isUser ? 'chat-bubble-primary' : 'chat-bubble-secondary'}`}>
        {message.componentId ? (
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <p className="text-sm opacity-80">Generated a microapp for you:</p>
              {isPinned && <span className="badge badge-success badge-sm">Pinned</span>}
            </div>
            <MicroappIframe
              componentId={message.componentId}
              onFeedback={handleFeedback}
              onIterate={
                message.componentId
                  ? () => enterStudioMode(message.componentId!, message.id)
                  : undefined
              }
              onPinClick={isPinned ? undefined : handlePinClick}
              onSparkPinned={handleSparkPinned}
            />
            {message.reasoning && (
              <p className="text-xs opacity-60 mt-2">{message.reasoning}</p>
            )}
          </div>
        ) : (
          <div className="whitespace-pre-wrap">{message.content}</div>
        )}
      </div>
    </div>
  );
};
