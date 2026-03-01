import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import api from '../services/api';

interface MicroappIframeProps {
    componentId: string;
    onFeedback?: (rating: 1 | 5) => void;
}

const MIN_HEIGHT = 200;
const MAX_HEIGHT = 800;
const DEFAULT_HEIGHT = 360;

export const MicroappIframe: React.FC<MicroappIframeProps> = ({
    componentId,
    onFeedback: _onFeedback,
}) => {
    const iframeRef = useRef<HTMLIFrameElement>(null);
    const [iframeHeight, setIframeHeight] = useState(DEFAULT_HEIGHT);
    const [dataMode, setDataMode] = useState<'sample' | 'real'>('sample');
    const [isLoadingData, setIsLoadingData] = useState(false);

    // Fetch mock data from the component data endpoint and inject into the iframe.
    const injectData = useCallback(async (mode: 'sample' | 'real') => {
        setIsLoadingData(true);
        try {
            const response = await api.post(`/components/${componentId}/data`, { data_mode: mode });
            iframeRef.current?.contentWindow?.postMessage(
                { type: 'spark_data', payload: response.data },
                '*'
            );
        } catch {
            // Silently ignore — component falls back to its own sample data
        } finally {
            setIsLoadingData(false);
        }
    }, [componentId]);

    // After iframe loads: send theme + inject sample mock data
    useEffect(() => {
        const iframe = iframeRef.current;
        if (!iframe) return;
        const onLoad = () => {
            // Theme
            const isDark = document.documentElement.classList.contains('dark');
            iframe.contentWindow?.postMessage({ type: 'spark_theme', theme: isDark ? 'dark' : 'light' }, '*');
            // Inject mock data (non-blocking)
            injectData(dataMode);
        };
        iframe.addEventListener('load', onLoad);
        return () => iframe.removeEventListener('load', onLoad);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [componentId]);

    // Resize listener
    useEffect(() => {
        const onMessage = (event: MessageEvent) => {
            if (event.data?.type === 'spark_resize' && typeof event.data.height === 'number') {
                const h = Math.min(Math.max(event.data.height + 16, MIN_HEIGHT), MAX_HEIGHT);
                setIframeHeight(h);
            }
        };
        window.addEventListener('message', onMessage);
        return () => window.removeEventListener('message', onMessage);
    }, []);

    const handleDataModeChange = async (mode: 'sample' | 'real') => {
        setDataMode(mode);
        await injectData(mode);
    };

    return (
        <Card className="overflow-hidden">
            <CardContent className="p-0">
                <div className="flex items-center gap-2 px-3 py-2 border-b bg-muted/30">
                    <Badge variant="outline" className="text-xs">
                        {isLoadingData ? 'Loading…' : dataMode === 'sample' ? 'Sample data' : 'Real data'}
                    </Badge>
                    <div className="flex gap-1 ml-auto">
                        <Button
                            variant={dataMode === 'sample' ? 'secondary' : 'ghost'}
                            size="sm"
                            className="h-6 px-2 text-xs"
                            onClick={() => handleDataModeChange('sample')}
                            disabled={isLoadingData}
                        >
                            Sample
                        </Button>
                        <Button
                            variant={dataMode === 'real' ? 'secondary' : 'ghost'}
                            size="sm"
                            className="h-6 px-2 text-xs"
                            onClick={() => handleDataModeChange('real')}
                            disabled={isLoadingData}
                        >
                            Real
                        </Button>
                    </div>
                </div>
                <iframe
                    ref={iframeRef}
                    src={`/api/components/${componentId}/iframe`}
                    style={{ height: `${iframeHeight}px` }}
                    className="w-full border-0"
                    sandbox="allow-scripts allow-same-origin"
                    title={`Component ${componentId}`}
                />
            </CardContent>
        </Card>
    );
};
