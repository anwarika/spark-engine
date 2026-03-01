import React, { useEffect, useState } from 'react';
import { catalogAPI, demoAPI, type BuiltInTemplate, type SaveTemplatePayload } from '../services/api';
import { useChatStore } from '../store/chatStore';
import { Card, CardContent, CardHeader } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Tabs, TabsList, TabsTrigger } from './ui/tabs';
import { Alert, AlertDescription } from './ui/alert';
import { Skeleton } from './ui/skeleton';
import { ScrollArea } from './ui/scroll-area';
import { Loader2, Sparkles, CheckCircle2 } from 'lucide-react';

const CATEGORIES = [
  { id: '', name: 'All' },
  { id: 'chart', name: 'Charts' },
  { id: 'table', name: 'Tables' },
  { id: 'card', name: 'Cards' },
  { id: 'dashboard', name: 'Dashboards' },
  { id: 'list', name: 'Lists' },
  { id: 'custom', name: 'Custom' }
];

interface PreviewIframeProps {
  html: string;
  height?: number;
}

const PreviewIframe: React.FC<PreviewIframeProps> = ({ html, height = 400 }) => (
  <iframe
    srcDoc={html}
    style={{ height: `${height}px` }}
    className="w-full rounded-lg border min-h-[360px]"
    sandbox="allow-scripts allow-same-origin"
    title="Template preview"
  />
);

function suggestedPrompt(template: BuiltInTemplate): string {
  const names: Record<string, string> = {
    StatCard: 'Create a KPI dashboard with 4 key metrics and trend indicators',
    DataTable: 'Create a filterable data table showing products with name, category, price, and stock',
    LineChart: 'Create a line chart showing time-series data with dates and values',
    BarChart: 'Create a bar chart comparing categories and values',
    PieChart: 'Create a pie chart for category breakdown distribution',
    AreaChart: 'Create an area chart for cumulative values over time',
    ComposedChart: 'Create a combined line and bar chart',
    ListWithSearch: 'Create a searchable list with product names and categories',
    MetricsDashboard: 'Create a multi-metric dashboard with revenue, orders, MRR, and a trend chart'
  };
  return names[template.name] ?? `Create a ${template.name} component`;
}

export const SandboxView: React.FC<{ onTryInChat?: (prompt: string) => void }> = ({ onTryInChat }) => {
  const [templates, setTemplates] = useState<BuiltInTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState('');
  const [expandedCode, setExpandedCode] = useState<string | null>(null);
  const [previewTemplate, setPreviewTemplate] = useState<{ name: string; html: string } | null>(null);
  const [previewLoading, setPreviewLoading] = useState<string | null>(null);
  const { setPendingPrompt } = useChatStore();

  // Demo seeding state
  const [demoSeeding, setDemoSeeding] = useState(false);
  const [demoSeeded, setDemoSeeded] = useState(false);
  const [demoCreated, setDemoCreated] = useState<string[]>([]);
  const [demoError, setDemoError] = useState<string | null>(null);

  // Add Library form state
  const [addName, setAddName] = useState('');
  const [addCategory, setAddCategory] = useState('custom');
  const [addCode, setAddCode] = useState('');
  const [addSaving, setAddSaving] = useState(false);
  const [addSuccess, setAddSuccess] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const list = await catalogAPI.listBuiltIn(category || undefined);
        setTemplates(list);
      } catch (err) {
        console.error('Failed to load templates:', err);
        setError('Failed to load templates');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [category]);

  const handlePreview = async (template: BuiltInTemplate) => {
    setPreviewLoading(template.name);
    setPreviewTemplate(null);
    try {
      const html = await catalogAPI.preview(template.code);
      setPreviewTemplate({ name: template.name, html });
    } catch (err) {
      console.error('Preview failed:', err);
      setPreviewTemplate({
        name: template.name,
        html: `<div style="padding:20px;color:red">Preview failed: ${err instanceof Error ? err.message : 'Unknown error'}</div>`
      });
    } finally {
      setPreviewLoading(null);
    }
  };

  const handleTryInChat = (template: BuiltInTemplate) => {
    const prompt = suggestedPrompt(template);
    setPendingPrompt(prompt);
    onTryInChat?.(prompt);
  };

  const handleSeedDemo = async () => {
    setDemoSeeding(true);
    setDemoError(null);
    try {
      const result = await demoAPI.seed();
      setDemoCreated(result.created.map(c => c.name));
      setDemoSeeded(true);
      if (result.errors?.length) {
        setDemoError(`Some failed: ${result.errors.join(', ')}`);
      }
    } catch (err) {
      setDemoError(err instanceof Error ? err.message : 'Seeding failed');
    } finally {
      setDemoSeeding(false);
    }
  };

  const handleSaveTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addName.trim() || !addCode.trim()) return;
    setAddSaving(true);
    setAddError(null);
    setAddSuccess(false);
    try {
      const payload: SaveTemplatePayload = {
        name: addName.trim(),
        category: addCategory || 'custom',
        react_code: addCode
      };
      await catalogAPI.saveTemplate(payload);
      setAddSuccess(true);
      setAddName('');
      setAddCode('');
      setTimeout(() => setAddSuccess(false), 3000);
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Failed to save template');
    } finally {
      setAddSaving(false);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex-none p-4 border-b">
        <h2 className="text-2xl font-bold">Sandbox</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Browse built-in templates, preview them, and add your own component library.
        </p>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {/* Demo seed section */}
          <Card className="border-dashed">
            <CardContent className="pt-5 pb-4">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-primary" />
                    <span className="font-medium text-sm">Demo Components</span>
                  </div>
                  <p className="text-xs text-muted-foreground max-w-sm">
                    Instantly seed 5 pre-built components (dashboard, chart, table, pie chart, KPI cards)
                    with realistic mock sales &amp; SaaS data — no LLM or API key required.
                  </p>
                  {demoSeeded && demoCreated.length > 0 && (
                    <div className="flex items-center gap-1.5 mt-2 text-xs text-green-600">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Created: {demoCreated.join(', ')}. View them in the Components tab.
                    </div>
                  )}
                  {demoError && (
                    <p className="mt-2 text-xs text-destructive">{demoError}</p>
                  )}
                </div>
                <Button
                  size="sm"
                  variant={demoSeeded ? 'outline' : 'default'}
                  onClick={handleSeedDemo}
                  disabled={demoSeeding}
                  className="gap-1.5 flex-shrink-0"
                >
                  {demoSeeding
                    ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Seeding…</>
                    : demoSeeded
                    ? <><CheckCircle2 className="w-3.5 h-3.5" /> Re-seed Demo</>
                    : <><Sparkles className="w-3.5 h-3.5" /> Load Demo</>
                  }
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Category filter */}
          <Tabs value={category} onValueChange={setCategory}>
            <TabsList className="flex-wrap h-auto gap-1">
              {CATEGORIES.map((c) => (
                <TabsTrigger key={c.id || 'all'} value={c.id}>
                  {c.name}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          {isLoading && (
            <div className="flex justify-center py-8">
              <Skeleton className="h-12 w-48" />
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {!isLoading && !error && templates.length === 0 && (
            <p className="text-muted-foreground text-center py-8">No templates in this category.</p>
          )}

          {!isLoading && !error && templates.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {templates.map((template) => (
                <Card key={template.name}>
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="font-semibold text-lg">{template.name}</h3>
                        <p className="text-sm text-muted-foreground mt-1">{template.description}</p>
                      </div>
                      <Badge variant="secondary">{template.category}</Badge>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {template.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="default"
                        onClick={() => handlePreview(template)}
                        disabled={!!previewLoading}
                      >
                        {previewLoading === template.name ? 'Compiling...' : 'Preview'}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleTryInChat(template)}
                      >
                        Try in Chat
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() =>
                          setExpandedCode(expandedCode === template.name ? null : template.name)
                        }
                      >
                        {expandedCode === template.name ? 'Hide Code' : 'Show Code'}
                      </Button>
                    </div>

                    {previewTemplate?.name === template.name && (
                      <div className="mt-2">
                        <PreviewIframe html={previewTemplate.html} />
                      </div>
                    )}

                    {expandedCode === template.name && (
                      <pre className="p-4 bg-muted rounded-lg text-xs overflow-x-auto max-h-64 overflow-y-auto">
                        <code>{template.code}</code>
                      </pre>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Add Your Library */}
          <Card className="mt-8">
            <CardHeader>
              <h3 className="font-semibold text-lg">Add Your Component Library</h3>
              <p className="text-sm text-muted-foreground">
                Save a React + shadcn component as a reusable template. See{' '}
                <code className="text-xs bg-muted px-1 rounded">
                  backend/app/component_library/CONTRIBUTING_TEMPLATES.md
                </code>{' '}
                for the template format, placeholder syntax, and import rules.
              </p>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSaveTemplate} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="add-name">Name</Label>
                    <Input
                      id="add-name"
                      value={addName}
                      onChange={(e) => setAddName(e.target.value)}
                      placeholder="e.g. MyChart"
                    />
                  </div>
                  <div>
                    <Label htmlFor="add-category">Category</Label>
                    <Input
                      id="add-category"
                      value={addCategory}
                      onChange={(e) => setAddCategory(e.target.value)}
                      placeholder="chart, table, card, dashboard, list, custom"
                    />
                  </div>
                </div>
                <div>
                  <Label htmlFor="add-code">React TSX Code</Label>
                  <textarea
                    id="add-code"
                    value={addCode}
                    onChange={(e) => setAddCode(e.target.value)}
                    placeholder="Paste your React + shadcn component code here..."
                    className="w-full min-h-[200px] p-3 rounded-lg border bg-background font-mono text-sm"
                    spellCheck={false}
                  />
                </div>
                {addError && (
                  <Alert variant="destructive">
                    <AlertDescription>{addError}</AlertDescription>
                  </Alert>
                )}
                {addSuccess && (
                  <Alert>
                    <AlertDescription>Template saved successfully!</AlertDescription>
                  </Alert>
                )}
                <Button type="submit" disabled={addSaving || !addName.trim() || !addCode.trim()}>
                  {addSaving ? 'Saving...' : 'Save Template'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </ScrollArea>
    </div>
  );
};
