import React, { useEffect, useState } from 'react';

interface MicroappIframeProps {
    componentId: string;
    onFeedback?: (rating: 1 | 5) => void;
}

export const MicroappIframe: React.FC<MicroappIframeProps> = ({
    componentId,
    onFeedback
}) => {
    const iframeUrl = `/api/components/${componentId}/iframe`;
    const sandbox = 'allow-scripts allow-same-origin';

    const [iframeHeight, setIframeHeight] = useState(600);

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

    return (
        <div className="card bg-base-200 shadow-xl">
            <div className="card-body p-2">
                <iframe
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


