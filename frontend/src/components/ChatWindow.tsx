import React, { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../store/chatStore';
import { useChat } from '../hooks/useChat';
import { MessageBubble } from './MessageBubble';

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
    <div className="chat-container bg-base-100 h-full flex flex-col">
      <div className="flex-none p-4 bg-base-200 border-b border-base-300">
        <div className="max-w-4xl mx-auto flex justify-end">
          <button
            className="btn btn-ghost btn-sm"
            onClick={clearMessages}
            disabled={messages.length === 0}
          >
            Clear Chat
          </button>
        </div>
      </div>

      <div className="messages-container flex-1 overflow-y-auto">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <h2 className="text-2xl font-bold mb-4">Welcome to Spark! ⚡</h2>
              <p className="text-base-content/70 mb-6">
                I can generate interactive Solid.js micro-apps for data visualization,
                dashboards, and more. Just describe what you need!
              </p>
              <div className="space-y-2 text-sm text-left">
                <div className="alert alert-info">
                  <span>💡 Try: "Create a table showing sales data with sorting"</span>
                </div>
                <div className="alert alert-info">
                  <span>💡 Try: "Build a KPI dashboard with 3 metrics"</span>
                </div>
                <div className="alert alert-info">
                  <span>💡 Try: "Make a filterable product list"</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isLoading && (
          <div className="chat chat-start">
            <div className="chat-image avatar">
              <div className="w-10 rounded-full bg-neutral text-neutral-content flex items-center justify-center">
                🤖
              </div>
            </div>
            <div className="chat-bubble chat-bubble-secondary">
              {generation ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="loading loading-dots loading-sm"></span>
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
                              className={[
                                'badge badge-sm',
                                isDone ? 'badge-success' : '',
                                isActive ? 'badge-warning' : '',
                                isError ? 'badge-error' : '',
                                info?.status === 'pending' ? 'badge-ghost' : ''
                              ].join(' ')}
                            >
                              {isDone ? 'done' : isActive ? '...' : isError ? 'err' : ''}
                            </span>
                            <span className={isActive ? 'font-semibold' : ''}>{step.replace(/_/g, ' ')}</span>
                          </div>
                          <div className="text-xs opacity-60">{typeof info?.ms === 'number' ? `${info.ms}ms` : ''}</div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="text-xs opacity-70">
                    You can switch to the <span className="font-semibold">Components</span> tab as soon as it’s ready.
                  </div>
                </div>
              ) : (
                <div className="flex items-center space-x-2">
                  <span className="loading loading-dots loading-sm"></span>
                  <span>Thinking...</span>
                </div>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="alert alert-error shadow-lg max-w-2xl mx-auto">
            <span>{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-base-200 border-t border-base-300">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="flex gap-2">
            <input
              type="text"
              className="input input-bordered flex-1"
              placeholder="Describe the component you want to generate..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading || !input.trim()}
            >
              {isLoading ? (
                <span className="loading loading-spinner"></span>
              ) : (
                'Send'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
