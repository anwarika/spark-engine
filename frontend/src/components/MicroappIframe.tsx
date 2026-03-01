import React, { useEffect, useState, useRef } from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';

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
        <Card>
            <CardContent className="p-2">
                <div className="flex justify-between items-center mb-2 gap-2">
                    <Badge variant="outline">
                        Data: {dataMode === 'sample' ? 'Sample' : 'Real'}
                    </Badge>
                    <div className="flex gap-1">
                        <Button
                            variant={dataMode === 'sample' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => handleDataModeChange('sample')}
                            title="Use sample/mock data"
                        >
                            Sample
                        </Button>
                        <Button
                            variant={dataMode === 'real' ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => handleDataModeChange('real')}
                            title="Use real data (inject via POST /api/components/{id}/data)"
                        >
                            Real
                        </Button>
                    </div>
                </div>
                <iframe
                    ref={iframeRef}
                    src={iframeUrl}
                    style={{ height: `${iframeHeight}px` }}
                    className="w-full rounded-lg border-0 min-h-[360px]"
                    sandbox={sandbox}
                    title={`Component ${componentId}`}
                    onError={(e) => console.error('Iframe error:', e)}
                />
                {onFeedback && (
                    <div className="flex justify-end gap-1 mt-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onFeedback(1)}
                            title="Thumbs down"
                        >
                            👎
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onFeedback(5)}
                            title="Thumbs up"
                        >
                            👍
                        </Button>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};


