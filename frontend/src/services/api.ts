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

export default api;
