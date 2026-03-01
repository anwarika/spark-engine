import React from 'react';
import type { Message } from '../types';
import { MicroappIframe } from './MicroappIframe';
import { componentAPI } from '../services/api';
import { Card, CardContent, CardHeader } from './ui/card';

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
    <div className={`flex gap-3 p-4 max-w-2xl mx-auto ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
        {isUser ? '👤' : '🤖'}
      </div>
      <Card className={`flex-1 ${isUser ? 'bg-primary/10' : 'bg-muted/50'}`}>
        <CardHeader className="pb-1">
          <div className="flex items-center gap-2 text-sm font-medium">
            {isUser ? 'You' : 'Spark AI'}
            <time className="text-xs text-muted-foreground">
              {message.timestamp.toLocaleTimeString()}
            </time>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {message.componentId ? (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground mb-2">
                Generated a microapp for you:
              </p>
              <MicroappIframe componentId={message.componentId} onFeedback={handleFeedback} />
              {message.reasoning && (
                <p className="text-xs text-muted-foreground mt-2">{message.reasoning}</p>
              )}
            </div>
          ) : (
            <div className="whitespace-pre-wrap">{message.content}</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
