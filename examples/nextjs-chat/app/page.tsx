"use client";

/**
 * Minimal Next.js chat app with Spark widget integration.
 *
 * Flow:
 * 1. User types a message
 * 2. If the message looks like a data/viz request, Spark generates a component
 * 3. The widget is shown inline in the message thread
 * 4. Otherwise, a plain text response is shown
 *
 * Run:
 *   SPARK_BASE_URL=http://localhost:8000
 *   SPARK_API_KEY=YOUR_SPARK_API_KEY
 *   npm run dev
 */

import { useState, useRef, useEffect } from "react";
import { SparkClient, SparkWidget, SparkRateLimitError, SparkGenerationError } from "@spark-engine/sdk";

const spark = new SparkClient({
  baseUrl: process.env.NEXT_PUBLIC_SPARK_BASE_URL ?? "http://localhost:8000",
  apiKey: process.env.NEXT_PUBLIC_SPARK_API_KEY,
});

type Message =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; text: string; widgetUrl?: string };

function isVizRequest(text: string): boolean {
  const lower = text.toLowerCase();
  return (
    lower.includes("chart") ||
    lower.includes("dashboard") ||
    lower.includes("graph") ||
    lower.includes("show") ||
    lower.includes("table") ||
    lower.includes("metrics") ||
    lower.includes("build") ||
    lower.includes("create") ||
    lower.includes("visuali")
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      if (isVizRequest(text)) {
        // Generate a Spark widget
        const iframeUrl = await spark.generateAndWait({ prompt: text });
        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          text: "Here's what I built:",
          widgetUrl: iframeUrl,
        };
        setMessages((m) => [...m, assistantMsg]);
      } else {
        // Plain text echo (replace with your LLM call)
        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          text: `You said: "${text}" — try asking for a chart or dashboard!`,
        };
        setMessages((m) => [...m, assistantMsg]);
      }
    } catch (e) {
      let errorText = "Something went wrong.";
      if (e instanceof SparkRateLimitError) {
        errorText = `Rate limit hit. Try again in ${e.retryAfter}s.`;
      } else if (e instanceof SparkGenerationError) {
        errorText = "Couldn't generate a widget. Try rephrasing your request.";
      }
      setMessages((m) => [
        ...m,
        { id: crypto.randomUUID(), role: "assistant", text: errorText },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-2xl mx-auto p-4 gap-4">
      <h1 className="text-xl font-bold">Spark Chat Demo</h1>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-4">
        {messages.length === 0 && (
          <p className="text-gray-400 text-sm mt-8 text-center">
            Ask for a dashboard, chart, or table — Spark generates it live.
          </p>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`rounded-2xl px-4 py-2 max-w-[80%] ${
                msg.role === "user"
                  ? "bg-blue-500 text-white"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              <p className="text-sm">{msg.text}</p>
              {msg.role === "assistant" && msg.widgetUrl && (
                <div className="mt-3 rounded-xl overflow-hidden" style={{ height: 360 }}>
                  <SparkWidget
                    iframeUrl={msg.widgetUrl}
                    style={{ width: "100%", height: "100%" }}
                  />
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={(e) => { e.preventDefault(); void send(); }}
        className="flex gap-2"
      >
        <input
          className="flex-1 border rounded-xl px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-300"
          placeholder='Try "Build a sales pipeline dashboard"'
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="bg-blue-500 text-white rounded-xl px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          {loading ? "…" : "Send"}
        </button>
      </form>
    </div>
  );
}
