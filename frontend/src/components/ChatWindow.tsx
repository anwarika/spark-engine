import React, { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../store/chatStore';
import { useChat } from '../hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';
import { Skeleton } from './ui/skeleton';

export const ChatWindow: React.FC = () => {
  const [input, setInput] = useState('');
  const { messages, isLoading, error, clearMessages, generation } = useChatStore();
  const { sendMessage } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const messageText = input;
    setInput('');
    await sendMessage(messageText);
  };

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="flex-none p-4 border-b">
        <div className="max-w-4xl mx-auto flex justify-end">
          <Button
            variant="ghost"
            size="sm"
            onClick={clearMessages}
            disabled={messages.length === 0}
          >
            Clear Chat
          </Button>
        </div>
      </div>

      <div className="messages-container flex-1 overflow-y-auto">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <h2 className="text-2xl font-bold mb-4">Welcome to Spark! ⚡</h2>
              <p className="text-muted-foreground mb-6">
                I can generate interactive React micro-apps for data visualization,
                dashboards, and more. Just describe what you need!
              </p>
              <div className="space-y-2 text-sm text-left">
                <Alert>
                  <AlertDescription>💡 Try: &quot;Create a table showing sales data with sorting&quot;</AlertDescription>
                </Alert>
                <Alert>
                  <AlertDescription>💡 Try: &quot;Build a KPI dashboard with 3 metrics&quot;</AlertDescription>
                </Alert>
                <Alert>
                  <AlertDescription>💡 Try: &quot;Make a filterable product list&quot;</AlertDescription>
                </Alert>
              </div>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isLoading && (
          <div className="flex gap-3 p-4 max-w-2xl mx-auto">
            <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
              🤖
            </div>
            <Card className="flex-1">
              <CardContent className="pt-4">
                {generation ? (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Skeleton className="h-2 w-16" />
                      <span className="font-medium">Building your microapp</span>
                    </div>
                    <div className="space-y-2">
                      {generation.order.map((step) => {
                        const info = generation.steps[step];
                        const isActive = info?.status === 'active';
                        const isDone = info?.status === 'done';
                        const isError = info?.status === 'error';
                        return (
                          <div key={step} className="flex items-center justify-between gap-3 text-sm">
                            <div className="flex items-center gap-2">
                              <span
                                className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${
                                  isDone ? 'bg-green-100 text-green-800' :
                                  isActive ? 'bg-amber-100 text-amber-800' :
                                  isError ? 'bg-red-100 text-red-800' :
                                  'bg-muted text-muted-foreground'
                                }`}
                              >
                                {isDone ? 'done' : isActive ? '...' : isError ? 'err' : ''}
                              </span>
                              <span className={isActive ? 'font-semibold' : ''}>{step.replace(/_/g, ' ')}</span>
                            </div>
                            <div className="text-xs text-muted-foreground">{typeof info?.ms === 'number' ? `${info.ms}ms` : ''}</div>
                          </div>
                        );
                      })}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      You can switch to the <span className="font-semibold">Components</span> tab as soon as it&apos;s ready.
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center space-x-2">
                    <Skeleton className="h-2 w-16" />
                    <span>Thinking...</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {error && (
          <Alert variant="destructive" className="max-w-2xl mx-auto">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="flex gap-2">
            <Input
              type="text"
              className="flex-1"
              placeholder="Describe the component you want to generate..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
            />
            <Button
              type="submit"
              disabled={isLoading || !input.trim()}
            >
              {isLoading ? (
                <Skeleton className="h-4 w-8" />
              ) : (
                'Send'
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
