import React, { useEffect, useState, useRef, useCallback } from 'react';
import type { SparkPinnedPostMessage } from '../types';

interface MicroappIframeProps {
  componentId: string;
  onFeedback?: (rating: 1 | 5) => void;
  onIterate?: () => void;
  /** Host handles pin request from iframe (spark:pinned) or Pin button */
  onSparkPinned?: (detail: {
    componentId: string;
    slotName: string;
    meta?: Record<string, unknown>;
  }) => void;
  /** Show a Pin button that calls this (e.g. opens prompt in parent) */
  onPinClick?: () => void;
  /** Layout variant: chat uses tall iframe; panel for dashboard tiles */
  variant?: 'chat' | 'panel';
}

export const MicroappIframe: React.FC<MicroappIframeProps> = ({
  componentId,
  onFeedback,
  onIterate,
  onSparkPinned,
  onPinClick,
  variant = 'chat',
}) => {
  const iframeUrl = `/api/components/${componentId}/iframe`;
  const sandbox = 'allow-scripts allow-same-origin';
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const [iframeHeight, setIframeHeight] = useState(variant === 'panel' ? 320 : 600);
  const [dataMode, setDataMode] = useState<'sample' | 'real'>('sample');

  useEffect(() => {
    if (variant === 'panel') {
      setIframeHeight(320);
      return;
    }

    const calculateReserved = () => {
      const header = document.querySelector('.chat-container .flex-none:first-child');
      const footer = document.querySelector('.chat-container > div:last-child');
      const padding = 32;
      const headerHeight = header ? header.getBoundingClientRect().height : 0;
      const footerHeight = footer ? footer.getBoundingClientRect().height : 0;
      return headerHeight + footerHeight + padding;
    };

    const updateHeight = () => {
      const reservedSpace = calculateReserved();
      const viewportHeight = window.innerHeight;
      const calculatedHeight = Math.min(Math.max(viewportHeight - reservedSpace, 360), 1000);
      setIframeHeight(calculatedHeight);
    };

    updateHeight();
    window.addEventListener('resize', updateHeight);
    return () => window.removeEventListener('resize', updateHeight);
  }, [variant]);

  const handleSparkMessage = useCallback(
    (event: MessageEvent) => {
      if (!onSparkPinned) return;
      const data = event.data as SparkPinnedPostMessage;
      if (!data || data.type !== 'spark:pinned') return;
      if (String(data.componentId) !== componentId) return;
      const slotName = (data.payload?.slotName || '').trim() || `App ${componentId.slice(0, 8)}`;
      onSparkPinned({
        componentId,
        slotName,
        meta: data.payload?.meta,
      });
    },
    [componentId, onSparkPinned]
  );

  useEffect(() => {
    if (!onSparkPinned) return;
    window.addEventListener('message', handleSparkMessage);
    return () => window.removeEventListener('message', handleSparkMessage);
  }, [onSparkPinned, handleSparkMessage]);

  const handleDataModeChange = (mode: 'sample' | 'real') => {
    setDataMode(mode);
    iframeRef.current?.contentWindow?.postMessage(
      { type: 'data_swap', mode },
      '*'
    );
  };

  return (
    <div className="card bg-base-200 shadow-xl">
      <div className="card-body p-2">
        <div className="flex justify-between items-center mb-2 gap-2 flex-wrap">
          <span className="badge badge-sm badge-outline">
            Data: {dataMode === 'sample' ? 'Sample' : 'Real'}
          </span>
          <div className="flex gap-2 items-center flex-wrap">
            {onPinClick && (
              <button
                type="button"
                className="btn btn-xs btn-secondary"
                onClick={onPinClick}
                title="Pin this microapp to your bar"
              >
                Pin
              </button>
            )}
            {onIterate && (
              <button
                type="button"
                className="btn btn-xs btn-primary"
                onClick={onIterate}
                title="Edit this microapp in studio mode"
              >
                Iterate
              </button>
            )}
            <div className="join">
              <button
                type="button"
                className={`btn btn-xs join-item ${dataMode === 'sample' ? 'btn-active' : ''}`}
                onClick={() => handleDataModeChange('sample')}
                title="Use sample/mock data"
              >
                Sample
              </button>
              <button
                type="button"
                className={`btn btn-xs join-item ${dataMode === 'real' ? 'btn-active' : ''}`}
                onClick={() => handleDataModeChange('real')}
                title="Use real data (requires POST to /data/swap first)"
              >
                Real
              </button>
            </div>
          </div>
        </div>
        <iframe
          key={componentId}
          ref={iframeRef}
          src={iframeUrl}
          style={{ height: `${iframeHeight}px` }}
          className="w-full rounded-lg border-0 min-h-[200px]"
          sandbox={sandbox}
          title={`Component ${componentId}`}
          onError={(e) => console.error('Iframe error:', e)}
        />
        {onFeedback && (
          <div className="card-actions justify-end mt-2">
            <button
              type="button"
              className="btn btn-sm btn-ghost"
              onClick={() => onFeedback(1)}
              title="Thumbs down"
              aria-label="Thumbs down"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
              </svg>
            </button>
            <button
              type="button"
              className="btn btn-sm btn-ghost"
              onClick={() => onFeedback(5)}
              title="Thumbs up"
              aria-label="Thumbs up"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017a2 2 0 01-.485-.06L7 20m7-10v-5a2 2 0 00-2-2h-.096c-.5 0-.905.405-.905.904 0 .715-.211 1.413-.608 2.008L7 11v9m7-10h-2M7 11H5a2 2 0 00-2 2v6a2 2 0 002 2h2.5" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
