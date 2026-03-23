import axios from 'axios';
import type {
  ChatResponse,
  Component,
  PinAppRequestBody,
  UpdatePinMetaRequestBody,
  RegeneratePinRequestBody,
  PinnedApp,
  RegeneratePinResponse,
  DashboardLayoutResponse,
  DashboardLayoutItem,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
    'X-Tenant-ID': 'default-tenant',
    'X-User-ID': 'default-user'
  }
});

export const chatAPI = {
  sendMessage: async (
    sessionId: string,
    message: string,
    componentId?: string
  ): Promise<ChatResponse> => {
    const body: Record<string, string> = {
      session_id: sessionId,
      tenant_id: 'default-tenant',
      user_id: 'default-user',
      message
    };
    if (componentId) {
      body.component_id = componentId;
    }
    const response = await api.post('/chat/message', body);
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

function normalizePinnedApp(raw: Record<string, unknown>): PinnedApp {
  const nested = raw.components as Record<string, unknown> | undefined;
  const component_name =
    (raw.component_name as string | undefined) ??
    (nested?.name as string | undefined);
  const component_version =
    (raw.component_version as string | undefined) ??
    (nested?.version as string | undefined);
  const component_status =
    (raw.component_status as string | undefined) ??
    (nested?.status as string | undefined);

  let metadata = raw.metadata;
  if (typeof metadata === 'string') {
    try {
      metadata = JSON.parse(metadata as string) as Record<string, unknown>;
    } catch {
      metadata = {};
    }
  }
  if (!metadata || typeof metadata !== 'object') metadata = {};

  return {
    id: String(raw.id),
    tenant_id: String(raw.tenant_id ?? ''),
    user_id: String(raw.user_id ?? ''),
    component_id: String(raw.component_id ?? ''),
    slot_name: String(raw.slot_name ?? ''),
    description: String(raw.description ?? ''),
    icon: String(raw.icon ?? ''),
    sort_order: Number(raw.sort_order ?? 0),
    metadata: metadata as Record<string, unknown>,
    pinned_at: String(raw.pinned_at ?? ''),
    updated_at: String(raw.updated_at ?? ''),
    component_name,
    component_version,
    component_status,
    iframe_url: String(raw.iframe_url ?? ''),
  };
}

export const appsAPI = {
  listPinnedApps: async (): Promise<{ pinned_apps: PinnedApp[]; total: number }> => {
    const response = await api.get('/apps');
    const raw = response.data.pinned_apps as Record<string, unknown>[] | undefined;
    const pinned_apps = (raw ?? []).map((row) => normalizePinnedApp(row));
    return {
      pinned_apps,
      total: response.data.total ?? pinned_apps.length,
    };
  },

  pinApp: async (body: PinAppRequestBody): Promise<PinnedApp> => {
    const response = await api.post('/apps/pin', {
      component_id: body.component_id,
      slot_name: body.slot_name,
      description: body.description ?? '',
      icon: body.icon ?? '',
      sort_order: body.sort_order ?? 0,
      metadata: body.metadata ?? {},
    });
    return normalizePinnedApp(response.data as Record<string, unknown>);
  },

  getPinnedApp: async (pinId: string): Promise<PinnedApp> => {
    const response = await api.get(`/apps/${pinId}`);
    return normalizePinnedApp(response.data as Record<string, unknown>);
  },

  updatePinMeta: async (
    pinId: string,
    updates: UpdatePinMetaRequestBody
  ): Promise<PinnedApp> => {
    const response = await api.patch(`/apps/${pinId}`, updates);
    return normalizePinnedApp(response.data as Record<string, unknown>);
  },

  regeneratePin: async (
    pinId: string,
    body?: RegeneratePinRequestBody
  ): Promise<RegeneratePinResponse> => {
    const response = await api.post(`/apps/${pinId}/regenerate`, body ?? {});
    const p = normalizePinnedApp(response.data as Record<string, unknown>);
    return {
      ...p,
      previous_component_id: String(
        (response.data as Record<string, unknown>).previous_component_id ?? ''
      ),
      new_component_id: String(
        (response.data as Record<string, unknown>).new_component_id ?? ''
      ),
    };
  },

  unpinApp: async (pinId: string): Promise<void> => {
    await api.delete(`/apps/${pinId}`);
  },
};

export const dashboardsAPI = {
  getLayout: async (name = 'default'): Promise<DashboardLayoutResponse> => {
    const response = await api.get('/dashboards/layout', { params: { name } });
    return {
      name: response.data.name ?? name,
      layout: (response.data.layout ?? []) as DashboardLayoutItem[],
    };
  },

  saveLayout: async (
    layout: DashboardLayoutItem[],
    name = 'default'
  ): Promise<DashboardLayoutResponse> => {
    const response = await api.put('/dashboards/layout', { layout, name });
    return {
      name: response.data.name ?? name,
      layout: (response.data.layout ?? layout) as DashboardLayoutItem[],
    };
  },
};

export default api;
