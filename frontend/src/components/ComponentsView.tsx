import React, { useEffect, useState } from 'react';
import { MicroappIframe } from './MicroappIframe';
import { componentAPI } from '../services/api';
import type { Component } from '../types';
import { useChatStore } from '../store/chatStore';
import { Alert, AlertDescription } from './ui/alert';
import { Badge } from './ui/badge';
import { Skeleton } from './ui/skeleton';

export const ComponentsView: React.FC = () => {
  const [components, setComponents] = useState<Component[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { messages } = useChatStore();

  // Extract component IDs from messages
  const componentIdsFromMessages = messages
    .filter((msg) => msg.componentId)
    .map((msg) => msg.componentId!)
    .filter((id, index, self) => self.indexOf(id) === index); // unique

  useEffect(() => {
    const fetchComponents = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const allComponents = await componentAPI.list();
        // Filter to only show components that are in the current session's messages
        const sessionComponents = allComponents.filter((comp) =>
          componentIdsFromMessages.includes(comp.id)
        );
        // Sort by created_at descending (newest first)
        sessionComponents.sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        setComponents(sessionComponents);
      } catch (err) {
        console.error('Failed to fetch components:', err);
        setError('Failed to load components');
      } finally {
        setIsLoading(false);
      }
    };

    if (componentIdsFromMessages.length > 0) {
      fetchComponents();
    } else {
      setComponents([]);
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length, componentIdsFromMessages.length]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Skeleton className="h-12 w-12 rounded-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (components.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center max-w-md">
          <h2 className="text-2xl font-bold mb-4">No Microapps Yet</h2>
          <p className="text-muted-foreground">
            Microapps you generate in the chat will appear here. Start a conversation to create your first microapp!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      <div className="mb-4">
        <h2 className="text-2xl font-bold">Your Microapps</h2>
        <p className="text-sm text-muted-foreground mt-1">
          {components.length} microapp{components.length !== 1 ? 's' : ''} rendered
        </p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {components.map((component) => (
          <div key={component.id} className="space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-lg">{component.name}</h3>
                {component.description && (
                  <p className="text-sm text-muted-foreground">{component.description}</p>
                )}
              </div>
              <Badge variant="outline">{component.status}</Badge>
            </div>
            <MicroappIframe componentId={component.id} />
            <div className="text-xs text-muted-foreground">
              Created: {new Date(component.created_at).toLocaleString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

