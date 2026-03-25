import React, { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../store/chatStore';
import { useChat } from '../hooks/useChat';
import { MessageBubble } from './MessageBubble';

const SUGGESTED_PROMPTS = [
  'Create a table showing sales data with sorting',
  'Build a KPI dashboard with 3 metrics',
  'Make a filterable product list',
];

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
      <div className="messages-container flex-1 overflow-y-auto">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <h2 className="text-2xl font-bold mb-4">Welcome to Spark! ⚡</h2>
              <p className="text-base-content/70 mb-6">
                Generate interactive Solid.js micro-apps for data visualization,
                dashboards, and more. Just describe what you need!
              </p>
              <div className="space-y-2 text-sm text-left">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="btn btn-ghost btn-block justify-start border border-base-300 hover:bg-base-200 h-auto min-h-0 py-2 px-3 normal-case font-normal whitespace-normal text-left outline-none focus:outline-none focus-visible:outline-none ring-0 focus:ring-0 focus-visible:ring-0 ring-offset-0 shadow-none focus:shadow-none focus-visible:shadow-none"
                    onClick={() => void sendMessage(prompt)}
                    disabled={isLoading}
                  >
                    <span>
                      💡 Try: &quot;{prompt}&quot;
                    </span>
                  </button>
                ))}
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
            {messages.length > 0 && (
              <button
                type="button"
                className="btn btn-ghost"
                onClick={clearMessages}
                disabled={isLoading}
                title="New chat"
                aria-label="New chat"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                  aria-hidden
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};
