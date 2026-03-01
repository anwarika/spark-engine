import React from 'react';
import type { Message } from '../types';
import { MicroappIframe } from './MicroappIframe';
import { componentAPI } from '../services/api';
import { ThumbsUp, ThumbsDown, User, Sparkles } from 'lucide-react';
import { Button } from './ui/button';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  const handleFeedback = async (rating: 1 | 5) => {
    if (message.componentId) {
      try {
        await componentAPI.submitFeedback(message.componentId, rating);
      } catch (error) {
        console.error('Failed to submit feedback:', error);
      }
    }
  };

  return (
    <div className={`px-4 sm:px-6 max-w-4xl mx-auto w-full`}>
      <div className={`flex gap-3 py-3 ${isUser ? 'flex-row-reverse' : ''}`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium mt-0.5
          ${isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-primary/10 text-primary'
          }`}
        >
          {isUser
            ? <User className="w-4 h-4" />
            : <Sparkles className="w-4 h-4" />
          }
        </div>

        {/* Bubble */}
        <div className={`flex-1 min-w-0 ${isUser ? 'flex flex-col items-end' : ''}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-foreground">
              {isUser ? 'You' : 'Spark AI'}
            </span>
            <time className="text-xs text-muted-foreground">
              {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </time>
          </div>

          {message.componentId ? (
            <div className="w-full space-y-2">
              <p className="text-sm text-muted-foreground">Generated a microapp:</p>
              <MicroappIframe componentId={message.componentId} onFeedback={handleFeedback} />
              {message.reasoning && (
                <p className="text-xs text-muted-foreground">{message.reasoning}</p>
              )}
              <div className="flex items-center gap-1 pt-1">
                <span className="text-xs text-muted-foreground mr-1">Helpful?</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-muted-foreground hover:text-green-600 hover:bg-green-50"
                  onClick={() => handleFeedback(5)}
                  title="Thumbs up"
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-muted-foreground hover:text-red-600 hover:bg-red-50"
                  onClick={() => handleFeedback(1)}
                  title="Thumbs down"
                >
                  <ThumbsDown className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          ) : (
            <div className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed max-w-prose whitespace-pre-wrap
              ${isUser
                ? 'bg-primary text-primary-foreground rounded-tr-sm'
                : 'bg-muted text-foreground rounded-tl-sm'
              }`}
            >
              {message.content}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
