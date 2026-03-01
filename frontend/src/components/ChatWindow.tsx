import React, { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../store/chatStore';
import { useChat } from '../hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { Button } from './ui/button';
import { Alert, AlertDescription } from './ui/alert';
import {
  Trash2,
  Send,
  Loader2,
  CheckCircle2,
  Circle,
  AlertCircle,
  Sparkles,
  BarChart2,
  Table2,
  LayoutDashboard,
} from 'lucide-react';

const EXAMPLE_PROMPTS = [
  {
    icon: Table2,
    label: 'Sales data table',
    description: 'Filterable, sortable table with sample data',
    prompt: 'Create a table showing sales data with sorting and filtering',
  },
  {
    icon: LayoutDashboard,
    label: 'KPI dashboard',
    description: 'Key metrics with trend indicators',
    prompt: 'Build a KPI dashboard with 4 key metrics and trend indicators',
  },
  {
    icon: BarChart2,
    label: 'Revenue chart',
    description: 'Bar chart comparing regional revenue',
    prompt: 'Create a bar chart comparing monthly revenue across regions',
  },
];

const FEATURE_BADGES = ['⚡ Instant compilation', '🔒 Sandboxed', '♻️ CAG cache'];

const STEP_LABELS: Record<string, string> = {
  db_session: 'Session',
  db_history: 'History',
  llm_generation: 'Generating',
  validation: 'Validating',
  compilation: 'Compiling',
  db_save_component: 'Saving',
  db_save_message: 'Finalizing',
};

export const ChatWindow: React.FC = () => {
  const [input, setInput] = useState('');
  const { messages, isLoading, error, clearMessages, generation, pendingPrompt, setPendingPrompt } = useChatStore();
  const { sendMessage } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    if (pendingPrompt) {
      setInput(pendingPrompt);
      setPendingPrompt(null);
      textareaRef.current?.focus();
    }
  }, [pendingPrompt, setPendingPrompt]);

  const adjustTextareaHeight = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    const messageText = input;
    setInput('');
    await sendMessage(messageText);
  };

  const handleExampleClick = (prompt: string) => {
    setInput(prompt);
    textareaRef.current?.focus();
  };

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Toolbar */}
      <div className="flex-none px-6 py-2 border-b flex justify-end">
        <Button
          variant="ghost"
          size="sm"
          onClick={clearMessages}
          disabled={messages.length === 0}
          className="text-muted-foreground hover:text-foreground gap-1.5"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Clear
        </Button>
      </div>

      {/* Messages */}
      <div className="messages-container flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full px-4 py-12">
            <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 mb-6">
              <Sparkles className="w-7 h-7 text-primary" />
            </div>
            <h2 className="text-3xl font-bold mb-2 text-center">Generate a UI with a single prompt</h2>
            <p className="text-muted-foreground text-base mb-6 text-center max-w-lg">
              Describe any component, chart, or dashboard. Spark builds, compiles, and sandboxes it instantly — powered by React + shadcn/ui.
            </p>
            <div className="flex flex-wrap justify-center gap-3 mb-10">
              {FEATURE_BADGES.map((badge) => (
                <span
                  key={badge}
                  className="text-xs text-muted-foreground bg-muted/60 px-3 py-1.5 rounded-full"
                >
                  {badge}
                </span>
              ))}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-2xl">
              {EXAMPLE_PROMPTS.map(({ icon: Icon, label, description, prompt }) => (
                <button
                  key={label}
                  onClick={() => handleExampleClick(prompt)}
                  className="flex flex-col gap-1.5 items-start px-5 py-4 rounded-2xl border bg-card hover:bg-accent hover:border-primary/30 transition-colors text-left group"
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="w-5 h-5 text-primary flex-shrink-0" />
                    <span className="font-medium text-foreground group-hover:text-foreground">{label}</span>
                  </div>
                  <span className="text-xs text-muted-foreground group-hover:text-muted-foreground">
                    {description}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="py-4 space-y-1">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}

            {/* Generation progress */}
            {isLoading && (
              <div className="px-4 sm:px-6 max-w-4xl mx-auto w-full">
                <div className="flex gap-3 py-2">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center mt-0.5">
                    <Sparkles className="w-4 h-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium mb-2 text-foreground">Building your microapp…</p>
                    {generation ? (
                      <div className="space-y-1.5 bg-muted/40 rounded-xl p-3">
                        {generation.order.map((step) => {
                          const info = generation.steps[step];
                          const isActive = info?.status === 'active';
                          const isDone = info?.status === 'done';
                          const isError = info?.status === 'error';
                          const isPending = !isActive && !isDone && !isError;
                          return (
                            <div key={step} className="flex items-center justify-between gap-2 text-xs">
                              <div className="flex items-center gap-2">
                                {isDone && <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />}
                                {isActive && <Loader2 className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 animate-spin" />}
                                {isError && <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />}
                                {isPending && <Circle className="w-3.5 h-3.5 text-muted-foreground/40 flex-shrink-0" />}
                                <span className={`${isActive ? 'text-foreground font-medium' : isDone ? 'text-muted-foreground' : 'text-muted-foreground/60'}`}>
                                  {STEP_LABELS[step] ?? step.replace(/_/g, ' ')}
                                </span>
                              </div>
                              {typeof info?.ms === 'number' && (
                                <span className="text-muted-foreground/60">{info.ms}ms</span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Thinking…
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div className="px-4 sm:px-6 max-w-4xl mx-auto w-full">
                <Alert variant="destructive">
                  <AlertCircle className="w-4 h-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex-none px-4 sm:px-6 py-4 border-t bg-background">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="flex gap-2 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onInput={adjustTextareaHeight}
                disabled={isLoading}
                placeholder="Describe the component you want to generate…"
                rows={1}
                className="w-full min-h-[44px] max-h-[160px] resize-none rounded-2xl border border-input bg-background px-4 py-3 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 leading-relaxed"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e as unknown as React.FormEvent);
                  }
                }}
              />
            </div>
            <Button
              type="submit"
              disabled={isLoading || !input.trim()}
              size="default"
              className="h-11 px-5 rounded-2xl gap-2 flex-shrink-0"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span className="hidden sm:inline">Send</span>
                </>
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Press Enter to send · Shift+Enter for new line
          </p>
        </form>
      </div>
    </div>
  );
};
