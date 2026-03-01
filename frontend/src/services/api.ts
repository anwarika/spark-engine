import axios from 'axios';
import type { ChatResponse, Component } from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
    'X-Tenant-ID': 'default-tenant',
    'X-User-ID': 'default-user'
  }
});

export const chatAPI = {
  sendMessage: async (sessionId: string, message: string): Promise<ChatResponse> => {
    const response = await api.post('/chat/message', {
      session_id: sessionId,
      tenant_id: 'default-tenant',
      user_id: 'default-user',
      message
    });
    return response.data;
  }
};

export const componentAPI = {
  list: async (): Promise<Component[]> => {
    const response = await api.get('/components');
    return response.data.components;
  },

  get: async (id: string): Promise<Component> => {
    const response = await api.get(`/components/${id}`);
    return response.data;
  },

  submitFeedback: async (componentId: string, rating: 1 | 5, feedbackText: string = '') => {
    await api.put(`/components/${componentId}/feedback`, {
      component_id: componentId,
      user_id: 'default-user',
      rating,
      feedback_text: feedbackText
    });
  }
};

export interface BuiltInTemplate {
  name: string;
  category: string;
  description: string;
  tags: string[];
  data_requirements: string[];
  code: string;
}

export interface SaveTemplatePayload {
  name: string;
  description?: string;
  category?: string;
  tags?: string[];
  react_code: string;
  is_public?: boolean;
}

export const demoAPI = {
  status: async (): Promise<{ seeded: boolean; count: number; total: number; components: Component[] }> => {
    const response = await api.get('/demo/status');
    return response.data;
  },
  seed: async (): Promise<{ status: string; created: { id: string; name: string }[]; skipped: string[]; errors: string[] }> => {
    const response = await api.post('/demo/seed');
    return response.data;
  }
};

export const catalogAPI = {
  listBuiltIn: async (category?: string): Promise<BuiltInTemplate[]> => {
    const params = category ? { category } : {};
    const response = await api.get('/catalog/built-in-templates', { params });
    return response.data.templates;
  },

  preview: async (reactCode: string): Promise<string> => {
    const response = await api.post(
      '/catalog/preview',
      { react_code: reactCode },
      { responseType: 'text' }
    );
    return response.data;
  },

  saveTemplate: async (payload: SaveTemplatePayload): Promise<{ template: unknown }> => {
    const response = await api.post('/catalog/templates', payload);
    return response.data;
  }
};

export default api;
