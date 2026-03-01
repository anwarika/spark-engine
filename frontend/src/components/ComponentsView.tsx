import React, { useEffect, useState, useCallback } from 'react';
import { MicroappIframe } from './MicroappIframe';
import { componentAPI, demoAPI } from '../services/api';
import type { Component } from '../types';
import { Alert, AlertDescription } from './ui/alert';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Loader2, LayoutGrid, Sparkles } from 'lucide-react';

export const ComponentsView: React.FC = () => {
  const [components, setComponents] = useState<Component[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [seedError, setSeedError] = useState<string | null>(null);

  const fetchComponents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const all = await componentAPI.list();
      const sorted = [...all].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setComponents(sorted);
    } catch (err) {
      console.error('Failed to fetch components:', err);
      setError('Failed to load components');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchComponents(); }, [fetchComponents]);

  const handleLoadDemo = async () => {
    setSeeding(true);
    setSeedError(null);
    try {
      const result = await demoAPI.seed();
      if (result.errors?.length) {
        setSeedError(`Some components failed: ${result.errors.join(', ')}`);
      }
      await fetchComponents();
    } catch (err) {
      setSeedError(err instanceof Error ? err.message : 'Seeding failed');
    } finally {
      setSeeding(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-6">
        <Alert variant="destructive" className="max-w-sm">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (components.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full px-6 py-12">
        <div className="flex items-center justify-center w-12 h-12 rounded-2xl bg-muted mb-4">
          <LayoutGrid className="w-6 h-6 text-muted-foreground" />
        </div>
        <h2 className="text-xl font-semibold mb-1">No components yet</h2>
        <p className="text-muted-foreground text-sm text-center max-w-sm mb-6">
          Generate components via the Chat tab, or load the demo dataset to see pre-built examples.
        </p>
        {seedError && (
          <Alert variant="destructive" className="mb-4 max-w-sm">
            <AlertDescription>{seedError}</AlertDescription>
          </Alert>
        )}
        <Button onClick={handleLoadDemo} disabled={seeding} className="gap-2">
          {seeding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {seeding ? 'Loading demo…' : 'Load Demo Components'}
        </Button>
        <p className="text-xs text-muted-foreground mt-3">
          Generates 5 pre-built components — no LLM required
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Components</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              {components.length} component{components.length !== 1 ? 's' : ''}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleLoadDemo}
            disabled={seeding}
            className="gap-1.5"
          >
            {seeding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            {seeding ? 'Loading…' : 'Load Demo'}
          </Button>
        </div>

        {seedError && (
          <Alert variant="destructive">
            <AlertDescription>{seedError}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {components.map((component) => (
            <div key={component.id} className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <h3 className="font-medium truncate">{component.name}</h3>
                  {component.description && (
                    <p className="text-xs text-muted-foreground truncate">{component.description}</p>
                  )}
                </div>
                <Badge variant="outline" className="flex-shrink-0 text-xs">{component.status}</Badge>
              </div>
              <MicroappIframe componentId={component.id} />
              <p className="text-xs text-muted-foreground">
                {new Date(component.created_at).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
