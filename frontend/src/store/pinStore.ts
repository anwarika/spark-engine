import { create } from 'zustand';
import type { PinnedApp, RegeneratePinResponse } from '../types';
import { appsAPI } from '../services/api';

interface PinState {
  pinnedApps: PinnedApp[];
  selectedPinId: string | null;
  loading: boolean;
  error: string | null;
  refreshPinnedApps: () => Promise<void>;
  selectPin: (pinId: string | null) => void;
  pinComponent: (
    componentId: string,
    slotName: string,
    opts?: { description?: string; icon?: string; metadata?: Record<string, unknown> }
  ) => Promise<PinnedApp>;
  unpin: (pinId: string) => Promise<void>;
  regeneratePin: (pinId: string, prompt?: string) => Promise<RegeneratePinResponse>;
  mergePinnedApp: (app: PinnedApp) => void;
  removePinLocal: (pinId: string) => void;
  clearError: () => void;
}

function sortPins(apps: PinnedApp[]): PinnedApp[] {
  return [...apps].sort((a, b) => {
    if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order;
    return a.pinned_at.localeCompare(b.pinned_at);
  });
}

export const usePinStore = create<PinState>((set) => ({
  pinnedApps: [],
  selectedPinId: null,
  loading: false,
  error: null,

  clearError: () => set({ error: null }),

  refreshPinnedApps: async () => {
    set({ loading: true, error: null });
    try {
      const { pinned_apps } = await appsAPI.listPinnedApps();
      set({ pinnedApps: sortPins(pinned_apps), loading: false });
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'response' in e
          ? String((e as { response?: { data?: { detail?: string } } }).response?.data?.detail)
          : e instanceof Error
            ? e.message
            : 'Failed to load pinned apps';
      set({ error: msg ?? 'Failed to load pinned apps', loading: false });
    }
  },

  selectPin: (pinId) => set({ selectedPinId: pinId }),

  pinComponent: async (componentId, slotName, opts) => {
    set({ loading: true, error: null });
    try {
      const pinned = await appsAPI.pinApp({
        component_id: componentId,
        slot_name: slotName,
        description: opts?.description,
        icon: opts?.icon,
        metadata: opts?.metadata,
      });
      set((state) => ({
        pinnedApps: sortPins([...state.pinnedApps.filter((p) => p.id !== pinned.id), pinned]),
        loading: false,
        selectedPinId: pinned.id,
      }));
      return pinned;
    } catch (e: unknown) {
      const detail =
        e && typeof e === 'object' && 'response' in e
          ? (e as { response?: { data?: { detail?: string }; status?: number } }).response?.data
              ?.detail
          : undefined;
      const msg =
        detail ??
        (e instanceof Error ? e.message : 'Failed to pin app');
      set({ error: String(msg), loading: false });
      throw e;
    }
  },

  unpin: async (pinId) => {
    set({ error: null });
    try {
      await appsAPI.unpinApp(pinId);
      set((state) => ({
        pinnedApps: state.pinnedApps.filter((p) => p.id !== pinId),
        selectedPinId: state.selectedPinId === pinId ? null : state.selectedPinId,
      }));
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'response' in e
          ? String((e as { response?: { data?: { detail?: string } } }).response?.data?.detail)
          : e instanceof Error
            ? e.message
            : 'Failed to unpin';
      set({ error: String(msg) });
      throw e;
    }
  },

  regeneratePin: async (pinId, prompt) => {
    set({ loading: true, error: null });
    try {
      const result = await appsAPI.regeneratePin(pinId, prompt ? { prompt } : undefined);
      set((state) => ({
        pinnedApps: sortPins(
          state.pinnedApps.map((p) => (p.id === pinId ? { ...result } : p))
        ),
        loading: false,
      }));
      return result;
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'response' in e
          ? String((e as { response?: { data?: { detail?: string } } }).response?.data?.detail)
          : e instanceof Error
            ? e.message
            : 'Regenerate failed';
      set({ error: String(msg), loading: false });
      throw e;
    }
  },

  mergePinnedApp: (app) =>
    set((state) => ({
      pinnedApps: sortPins([...state.pinnedApps.filter((p) => p.id !== app.id), app]),
    })),

  removePinLocal: (pinId) =>
    set((state) => ({
      pinnedApps: state.pinnedApps.filter((p) => p.id !== pinId),
      selectedPinId: state.selectedPinId === pinId ? null : state.selectedPinId,
    })),
}));
