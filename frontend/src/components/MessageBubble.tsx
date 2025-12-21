import React from 'react';
import type { Message } from '../types';
import { MicroappIframe } from './MicroappIframe';
import { componentAPI } from '../services/api';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

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
            <p className="text-sm opacity-80 mb-2">
              Generated a microapp for you:
            </p>
            <MicroappIframe componentId={message.componentId} onFeedback={handleFeedback} />
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
