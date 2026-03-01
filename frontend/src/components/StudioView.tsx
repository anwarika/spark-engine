import React, { useState, useCallback } from 'react';
import { useChatStore } from '../store/chatStore';
import { StudioPreview } from './StudioPreview';
import { StudioChat } from './StudioChat';

export const StudioView: React.FC = () => {
  const exitStudioMode = useChatStore((s) => s.exitStudioMode);
  const [leftPercent, setLeftPercent] = useState(65);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging) return;
      const total = window.innerWidth;
      const x = e.clientX;
      const pct = Math.max(25, Math.min(75, (x / total) * 100));
      setLeftPercent(pct);
    },
    [isDragging]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  React.useEffect(() => {
    if (!isDragging) return;
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <div className="h-screen flex flex-col bg-base-100">
      <div className="flex-none navbar bg-base-300 shadow-lg">
        <div className="flex-1">
          <button
            className="btn btn-ghost btn-sm gap-2"
            onClick={exitStudioMode}
            title="Back to chat"
          >
            ← Back to Chat
          </button>
          <span className="text-xl font-bold ml-4">⚡ Spark AI</span>
          <span className="badge badge-outline badge-sm ml-2">Edit Mode</span>
        </div>
      </div>

      <div className="flex-1 flex min-h-0 overflow-hidden">
        <div
          className="min-w-0 overflow-hidden"
          style={{ width: `${leftPercent}%` }}
        >
          <StudioPreview />
        </div>

        <div
          className="w-2 flex-shrink-0 bg-base-300 hover:bg-primary/20 cursor-col-resize flex items-center justify-center group"
          onMouseDown={handleMouseDown}
          role="separator"
          aria-orientation="vertical"
        >
          <div className="w-1 h-12 rounded-full bg-base-content/20 group-hover:bg-primary/50 transition-colors" />
        </div>

        <div
          className="min-w-0 overflow-hidden"
          style={{ width: `${100 - leftPercent}%` }}
        >
          <StudioChat />
        </div>
      </div>
    </div>
  );
};
