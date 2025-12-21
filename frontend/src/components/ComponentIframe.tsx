import React from 'react';
import { MicroappIframe } from './MicroappIframe';

interface ComponentIframeProps {
  componentId: string;
  onFeedback?: (rating: 1 | 5) => void;
}

export const ComponentIframe: React.FC<ComponentIframeProps> = ({ componentId, onFeedback }) => {
  return <MicroappIframe componentId={componentId} onFeedback={onFeedback} />;
};
