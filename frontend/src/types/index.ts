export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  componentId?: string;
  reasoning?: string;
  timestamp: Date;
}

export interface ChatResponse {
  type: 'text' | 'component';
  content: string;
  component_id?: string;
  reasoning?: string;
}

export interface Component {
  id: string;
  name: string;
  description: string;
  version: string;
  bundle_size_bytes: number;
  status: string;
  created_at: string;
  updated_at: string;
}
