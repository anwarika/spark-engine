import React, { useEffect, useState, useRef } from 'react';

interface MicroappIframeProps {
    componentId: string;
    onFeedback?: (rating: 1 | 5) => void;
    onIterate?: () => void;
}

export const MicroappIframe: React.FC<MicroappIframeProps> = ({
    componentId,
    onFeedback,
    onIterate
}) => {
    const iframeUrl = `/api/components/${componentId}/iframe`;
    const sandbox = 'allow-scripts allow-same-origin';
    const iframeRef = useRef<HTMLIFrameElement>(null);

    const [iframeHeight, setIframeHeight] = useState(600);
    const [dataMode, setDataMode] = useState<'sample' | 'real'>('sample');

    useEffect(() => {
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
    }, []);

    const handleDataModeChange = (mode: 'sample' | 'real') => {
        setDataMode(mode);
        iframeRef.current?.contentWindow?.postMessage(
            { type: 'data_swap', mode },
            '*'  // Same-origin in production; allows dev with different ports
        );
    };

    return (
        <div className="card bg-base-200 shadow-xl">
            <div className="card-body p-2">
                <div className="flex justify-between items-center mb-2 gap-2 flex-wrap">
                    <span className="badge badge-sm badge-outline">
                        Data: {dataMode === 'sample' ? 'Sample' : 'Real'}
                    </span>
                    <div className="flex gap-2 items-center">
                        {onIterate && (
                            <button
                                className="btn btn-xs btn-primary"
                                onClick={onIterate}
                                title="Edit this microapp in studio mode"
                            >
                                ✏ Iterate
                            </button>
                        )}
                    <div className="join">
                        <button
                            className={`btn btn-xs join-item ${dataMode === 'sample' ? 'btn-active' : ''}`}
                            onClick={() => handleDataModeChange('sample')}
                            title="Use sample/mock data"
                        >
                            Sample
                        </button>
                        <button
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
                    className="w-full rounded-lg border-0 min-h-[360px]"
                    sandbox={sandbox}
                    title={`Component ${componentId}`}
                    onError={(e) => console.error('Iframe error:', e)}
                />
                {onFeedback && (
                    <div className="card-actions justify-end mt-2">
                        <button
                            className="btn btn-sm btn-ghost"
                            onClick={() => onFeedback(1)}
                            title="Thumbs down"
                        >
                            👎
                        </button>
                        <button
                            className="btn btn-sm btn-ghost"
                            onClick={() => onFeedback(5)}
                            title="Thumbs up"
                        >
                            👍
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};


