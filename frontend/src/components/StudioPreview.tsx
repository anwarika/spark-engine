import React, { useMemo } from 'react';
import { useChatStore } from '../store/chatStore';

export const StudioPreview: React.FC = () => {
  const currentStudioComponentId = useChatStore((s) => s.currentStudioComponentId);

  const iframeUrl = useMemo(
    () => (currentStudioComponentId ? `/api/components/${currentStudioComponentId}/iframe` : ''),
    [currentStudioComponentId]
  );

  if (!currentStudioComponentId) return null;

  return (
    <div className="h-full w-full flex flex-col bg-base-200">
      <iframe
        key={currentStudioComponentId}
        src={iframeUrl}
        className="flex-1 w-full min-h-0 border-0 rounded-lg"
        sandbox="allow-scripts allow-same-origin"
        title={`Component ${currentStudioComponentId}`}
      />
    </div>
  );
};
