/**
 * useSpark — React hook for the full generate → pin → update lifecycle.
 *
 * Usage:
 *   const { generate, pin, regenerate, unpin, pinnedApps, status } = useSpark(client);
 *
 *   // Generate a new app from a chat message
 *   const app = await generate({ prompt, data_context });
 *
 *   // Pin it to the user's nav bar
 *   await pin({ component_id: app.component_id!, slot_name: 'Pipeline' });
 */

import { useState, useCallback, useRef } from "react";
import type {
  GenerateRequest,
  GenerateResponse,
  PinRequest,
  PinnedApp,
  RegenerateRequest,
  RegenerateResponse,
  UpdatePinMetaRequest,
} from "./types";
import { SparkClient } from "./SparkClient";

// ------------------------------------------------------------------
// Hook state shape
// ------------------------------------------------------------------

export type SparkStatus = "idle" | "generating" | "loading" | "error";

export interface UseSparkState {
  status: SparkStatus;
  error: string | null;
  /** The last successfully generated component response. */
  lastGenerated: GenerateResponse | null;
  /** All pinned apps for the current user. */
  pinnedApps: PinnedApp[];
}

export interface UseSparkActions {
  /** Generate a micro-app from a prompt. Returns the full response. */
  generate(req: GenerateRequest): Promise<GenerateResponse>;
  /** Pin a generated component. */
  pin(req: PinRequest): Promise<PinnedApp>;
  /** Update the label / icon of a pin. */
  updatePin(pinId: string, updates: UpdatePinMetaRequest): Promise<PinnedApp>;
  /** Re-generate the component under a pin (optionally with a new prompt). */
  regenerate(pinId: string, req?: RegenerateRequest): Promise<RegenerateResponse>;
  /** Unpin an app. */
  unpin(pinId: string): Promise<void>;
  /** Refresh the pinned apps list from the server. */
  refreshPinnedApps(): Promise<void>;
  /** Reset error state. */
  clearError(): void;
}

export type UseSparkReturn = UseSparkState & UseSparkActions;

// ------------------------------------------------------------------
// Hook
// ------------------------------------------------------------------

export function useSpark(client: SparkClient): UseSparkReturn {
  const [status, setStatus] = useState<SparkStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastGenerated, setLastGenerated] = useState<GenerateResponse | null>(null);
  const [pinnedApps, setPinnedApps] = useState<PinnedApp[]>([]);

  // Use a ref so callbacks don't re-create on every render
  const clientRef = useRef(client);
  clientRef.current = client;

  // ------------------------------------------------------------------

  const clearError = useCallback(() => setError(null), []);

  const generate = useCallback(async (req: GenerateRequest): Promise<GenerateResponse> => {
    setStatus("generating");
    setError(null);
    try {
      const res = await clientRef.current.generate(req);
      setLastGenerated(res);
      setStatus("idle");
      return res;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setStatus("error");
      throw err;
    }
  }, []);

  const refreshPinnedApps = useCallback(async () => {
    setStatus("loading");
    try {
      const { pinned_apps } = await clientRef.current.listPinnedApps();
      setPinnedApps(pinned_apps);
      setStatus("idle");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setStatus("error");
    }
  }, []);

  const pin = useCallback(async (req: PinRequest): Promise<PinnedApp> => {
    setStatus("loading");
    setError(null);
    try {
      const pinned = await clientRef.current.pinApp(req);
      // Optimistically prepend to list
      setPinnedApps((prev) => [pinned, ...prev.filter((p) => p.id !== pinned.id)]);
      setStatus("idle");
      return pinned;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setStatus("error");
      throw err;
    }
  }, []);

  const updatePin = useCallback(async (
    pinId: string,
    updates: UpdatePinMetaRequest,
  ): Promise<PinnedApp> => {
    setError(null);
    try {
      const updated = await clientRef.current.updatePinMeta(pinId, updates);
      setPinnedApps((prev) => prev.map((p) => (p.id === pinId ? updated : p)));
      return updated;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      throw err;
    }
  }, []);

  const regenerate = useCallback(async (
    pinId: string,
    req?: RegenerateRequest,
  ): Promise<RegenerateResponse> => {
    setStatus("generating");
    setError(null);
    try {
      const result = await clientRef.current.regeneratePin(pinId, req);
      // Update the pin in-place with the new component_id / iframe_url
      setPinnedApps((prev) =>
        prev.map((p) =>
          p.id === pinId
            ? {
                ...p,
                component_id: result.new_component_id,
                iframe_url: result.iframe_url,
                updated_at: result.updated_at,
              }
            : p,
        ),
      );
      setStatus("idle");
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setStatus("error");
      throw err;
    }
  }, []);

  const unpin = useCallback(async (pinId: string): Promise<void> => {
    setError(null);
    try {
      await clientRef.current.unpinApp(pinId);
      setPinnedApps((prev) => prev.filter((p) => p.id !== pinId));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      throw err;
    }
  }, []);

  return {
    status,
    error,
    lastGenerated,
    pinnedApps,
    generate,
    pin,
    updatePin,
    regenerate,
    unpin,
    refreshPinnedApps,
    clearError,
  };
}
