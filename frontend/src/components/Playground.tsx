/**
 * Playground — interactive demo page at the top of the app.
 *
 * Left panel:  prompt input + preset examples
 * Right panel: live iframe of the generated component
 *
 * This is intentionally standalone (no auth required for the demo tenant).
 * It doubles as a sales tool: integrators paste the generated SDK snippet
 * into their own app to start shipping Spark widgets in < 5 min.
 */
import React, { useState, useRef } from 'react';

interface GenerateResult {
  component_id: string;
  microapp_url: string;
  status: string;
}

const PRESETS = [
  { label: 'Sales pipeline', prompt: 'Build a sales pipeline dashboard showing deal stages, win rates, and monthly bookings by rep' },
  { label: 'User analytics', prompt: 'Create a user analytics dashboard with daily active users, retention cohorts, and feature adoption trends' },
  { label: 'SaaS metrics', prompt: 'Show key SaaS metrics: MRR, churn rate, net revenue retention, and trial conversion funnel' },
  { label: 'Finance P&L', prompt: 'Build a P&L summary with monthly revenue, COGS, gross profit trend, and expense breakdown by category' },
  { label: 'Product catalog', prompt: 'Create a filterable product catalog table with sorting by price, category, and stock level' },
];

export const Playground: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const generate = async (text: string) => {
    const p = text.trim();
    if (!p) return;
    setIsGenerating(true);
    setResult(null);
    setError(null);

    try {
      const res = await fetch('/api/a2a/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: p }),
      });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error(json.detail ?? `HTTP ${res.status}`);
      }
      const data: GenerateResult = await res.json();
      if (data.status !== 'success') throw new Error(data.status);
      setResult(data);
    } catch (e: unknown) {
      setError((e as Error).message ?? 'Generation failed');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void generate(prompt);
  };

  const sdkSnippet = result
    ? `import { SparkWidget } from '@spark-engine/sdk';

// Add this wherever you want the widget to appear
<SparkWidget
  iframeUrl="${window.location.origin}/api/components/${result.component_id}/iframe"
  style={{ height: 400 }}
/>`
    : '';

  const copySnippet = async () => {
    await navigator.clipboard.writeText(sdkSnippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex-none px-6 pt-6 pb-4 border-b border-base-300">
        <h1 className="text-2xl font-bold">Playground</h1>
        <p className="text-sm text-base-content/60 mt-1">
          Describe any dashboard or widget — Spark generates it live. Copy the snippet to embed it in your app.
        </p>
      </div>

      <div className="flex-1 min-h-0 flex gap-0 overflow-hidden">
        {/* Left panel */}
        <div className="w-[380px] min-w-[280px] flex-none flex flex-col border-r border-base-300 overflow-y-auto">
          <div className="p-5 flex flex-col gap-4">
            {/* Prompt form */}
            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
              <textarea
                ref={textareaRef}
                className="textarea textarea-bordered w-full resize-none text-sm"
                rows={4}
                placeholder="Build a sales pipeline dashboard with deal stages, win rate, and bookings by rep…"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={isGenerating}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    void generate(prompt);
                  }
                }}
              />
              <button
                type="submit"
                className="btn btn-primary btn-sm w-full"
                disabled={!prompt.trim() || isGenerating}
              >
                {isGenerating ? (
                  <span className="loading loading-spinner loading-xs" />
                ) : null}
                {isGenerating ? 'Generating…' : 'Generate'}
              </button>
            </form>

            {/* Preset prompts */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-base-content/50 mb-2">Try a preset</p>
              <div className="flex flex-col gap-1.5">
                {PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    className="btn btn-ghost btn-sm justify-start text-left h-auto py-1.5 px-3 normal-case font-normal border border-base-300 hover:bg-base-200"
                    disabled={isGenerating}
                    onClick={() => {
                      setPrompt(preset.prompt);
                      void generate(preset.prompt);
                    }}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {/* SDK snippet */}
            {result && (
              <div className="rounded-lg border border-base-300 overflow-hidden">
                <div className="flex items-center justify-between px-3 py-2 bg-base-200 border-b border-base-300">
                  <span className="text-xs font-semibold text-base-content/70">SDK snippet</span>
                  <button
                    type="button"
                    className="btn btn-ghost btn-xs"
                    onClick={() => void copySnippet()}
                  >
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <pre className="text-xs p-3 overflow-x-auto whitespace-pre-wrap text-base-content/80 bg-base-100">
                  {sdkSnippet}
                </pre>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="alert alert-error text-sm py-2">
                <span>{error}</span>
              </div>
            )}
          </div>
        </div>

        {/* Right panel — iframe preview */}
        <div className="flex-1 min-w-0 flex flex-col bg-base-200/40">
          {!result && !isGenerating && (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 gap-3">
              <div className="text-4xl opacity-20 font-bold select-none">Spark</div>
              <p className="text-base-content/50 text-sm max-w-xs">
                Your generated component will appear here. Pick a preset or type a prompt to get started.
              </p>
            </div>
          )}

          {isGenerating && (
            <div className="flex-1 flex flex-col items-center justify-center gap-4">
              <span className="loading loading-spinner loading-lg text-primary" />
              <p className="text-sm text-base-content/60">Generating your component…</p>
            </div>
          )}

          {result && !isGenerating && (
            <div className="flex-1 flex flex-col">
              <div className="flex-none px-4 py-2 border-b border-base-300 flex items-center justify-between bg-base-100">
                <span className="text-xs text-base-content/50 font-mono truncate">{result.component_id}</span>
                <a
                  href={result.microapp_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-ghost btn-xs"
                >
                  Open
                </a>
              </div>
              <iframe
                src={result.microapp_url}
                className="flex-1 w-full border-none"
                sandbox="allow-scripts allow-same-origin"
                title="Generated component preview"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
