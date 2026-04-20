/**
 * SparkClient — typed API wrapper for the Spark backend.
 *
 * Usage:
 *   const spark = new SparkClient({
 *     baseUrl: 'https://spark.yourapp.com',
 *     tenantId: 'acme',
 *     userId: currentUser.id,
 *   });
 *
 *   const { component_id, microapp_url } = await spark.generate({
 *     prompt: 'Show me a pipeline dashboard',
 *     data_context: { deals: [...] },
 *   });
 */

import type {
  SparkClientConfig,
  SparkComponent,
  GenerateRequest,
  GenerateResponse,
  PinRequest,
  PinnedApp,
  RegenerateRequest,
  RegenerateResponse,
  UpdatePinMetaRequest,
} from "./types";

import {
  SparkError,
  SparkTimeoutError,
  classifyError,
} from "./errors";

// Re-export for consumers who import from the client module directly
export { SparkError } from "./errors";

function buildToken(tenantId: string, userId: string): string {
  // base64(tenantId:userId) — matches the middleware's _parse_bearer logic
  const raw = `${tenantId}:${userId}`;
  if (typeof btoa !== "undefined") return btoa(raw);
  // Node / SSR fallback
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (globalThis as any).Buffer?.from(raw).toString("base64") ?? btoa(raw);
}

export class SparkClient {
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;
  private readonly timeoutMs: number;

  constructor(config: SparkClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, "");
    this.timeoutMs = config.timeoutMs ?? 30_000;

    // API key (sk_live_*) takes precedence over legacy token/headers
    const authToken =
      config.apiKey ??
      config.token ??
      (config.tenantId && config.userId
        ? buildToken(config.tenantId, config.userId)
        : null);

    this.headers = {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      // Legacy fallback headers (no-op when API key is set)
      ...(config.tenantId ? { "X-Tenant-ID": config.tenantId } : {}),
      ...(config.userId ? { "X-User-ID": config.userId } : {}),
    };
  }

  // ------------------------------------------------------------------
  // Private helpers
  // ------------------------------------------------------------------

  private url(path: string): string {
    return `${this.baseUrl}${path}`;
  }

  private async fetch<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      controller.abort();
    }, this.timeoutMs);

    try {
      const res = await fetch(this.url(path), {
        method,
        headers: this.headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!res.ok) {
        let detail = res.statusText;
        try {
          const json = await res.json();
          detail = json.detail ?? json.message ?? detail;
        } catch {}
        throw classifyError(res.status, detail, res.headers);
      }

      if (res.status === 204) return undefined as T;
      return res.json() as Promise<T>;
    } catch (err) {
      if (err instanceof SparkError) throw err;
      // AbortError → SparkTimeoutError
      if ((err as Error)?.name === "AbortError") {
        throw new SparkTimeoutError(this.timeoutMs);
      }
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }

  // ------------------------------------------------------------------
  // Component generation (A2A)
  // ------------------------------------------------------------------

  /** Generate a new micro-app from a prompt. */
  async generate(req: GenerateRequest): Promise<GenerateResponse> {
    return this.fetch<GenerateResponse>("POST", "/api/a2a/generate", req);
  }

  /**
   * Generate a micro-app and return the iframe URL directly.
   *
   * Combines generate() + iframeUrl() into a single call — the most common
   * pattern for chat apps. Throws if generation fails.
   *
   *   const url = await spark.generateAndWait({ prompt });
   *   // url is ready to embed immediately
   */
  async generateAndWait(req: GenerateRequest): Promise<string & { componentId: string }> {
    const result = await this.generate(req);
    if (result.status !== "success" || !result.component_id) {
      throw new (await import("./errors")).SparkGenerationError(
        result.message ?? "Generation did not return a component",
      );
    }
    const url = (result.microapp_url ?? this.iframeUrl(result.component_id)) as string & {
      componentId: string;
    };
    // Attach componentId as a non-enumerable property for convenience
    Object.defineProperty(url, "componentId", { value: result.component_id });
    return url;
  }

  // ------------------------------------------------------------------
  // Component management
  // ------------------------------------------------------------------

  /** List all active components for the current tenant. */
  async listComponents(opts?: {
    limit?: number;
    offset?: number;
    status?: string;
  }): Promise<{ components: SparkComponent[]; total: number }> {
    const params = new URLSearchParams();
    if (opts?.limit != null) params.set("limit", String(opts.limit));
    if (opts?.offset != null) params.set("offset", String(opts.offset));
    if (opts?.status) params.set("status", opts.status);
    const qs = params.toString();
    return this.fetch(`GET`, `/api/components${qs ? `?${qs}` : ""}`);
  }

  /** Get a single component by ID. */
  async getComponent(componentId: string): Promise<SparkComponent> {
    return this.fetch("GET", `/api/components/${componentId}`);
  }

  /**
   * Returns the iframe URL for a component.
   * No network call — purely derives the URL.
   */
  iframeUrl(componentId: string): string {
    return `${this.baseUrl}/api/components/${componentId}/iframe`;
  }

  // ------------------------------------------------------------------
  // Pinned apps
  // ------------------------------------------------------------------

  /** List all pinned apps for the current user. */
  async listPinnedApps(): Promise<{ pinned_apps: PinnedApp[]; total: number }> {
    return this.fetch("GET", "/api/apps");
  }

  /** Pin a generated component to the user's nav bar. */
  async pinApp(req: PinRequest): Promise<PinnedApp> {
    return this.fetch("POST", "/api/apps/pin", req);
  }

  /** Get a single pinned app by its pin ID. */
  async getPinnedApp(pinId: string): Promise<PinnedApp> {
    return this.fetch("GET", `/api/apps/${pinId}`);
  }

  /** Update the label, icon, or sort order of a pin. */
  async updatePinMeta(
    pinId: string,
    updates: UpdatePinMetaRequest,
  ): Promise<PinnedApp> {
    return this.fetch("PATCH", `/api/apps/${pinId}`, updates);
  }

  /**
   * Re-generate the component under a pin.
   * The pin's ID and slot_name remain stable — only the underlying
   * component_id is swapped.
   */
  async regeneratePin(
    pinId: string,
    req?: RegenerateRequest,
  ): Promise<RegenerateResponse> {
    return this.fetch("POST", `/api/apps/${pinId}/regenerate`, req ?? {});
  }

  /** Unpin (delete) a pinned app. */
  async unpinApp(pinId: string): Promise<void> {
    return this.fetch("DELETE", `/api/apps/${pinId}`);
  }

  // ------------------------------------------------------------------
  // Data Bridge
  // ------------------------------------------------------------------

  /**
   * Push real data to a running component via the Data Bridge.
   * Call this after an iframe is mounted to replace sample data with live data.
   */
  async pushData(
    componentId: string,
    data: unknown,
    mode: "real" | "sample" = "real",
    ttlSeconds?: number,
  ): Promise<void> {
    await this.fetch("POST", `/api/components/${componentId}/data/swap`, {
      mode,
      data,
      ...(ttlSeconds !== undefined ? { ttl_seconds: ttlSeconds } : {}),
    });
  }

  // ------------------------------------------------------------------
  // Python Data Transform Layer
  // ------------------------------------------------------------------

  /**
   * Transform raw data with an LLM-generated Python script (Monty sandbox)
   * and cache the result in the Data Bridge for `componentId`.
   *
   * The component automatically renders with the transformed data — no
   * code changes needed in the component itself.
   *
   * @param componentId  The component whose Data Bridge slot to populate.
   * @param rawData      Any JSON-serializable object — the dataset to transform.
   * @param transform    Plain-English description of what to compute,
   *                     e.g. "Top 5 products by revenue this month".
   * @param opts.ttlSeconds  How long to cache the result (60–86400, default 3600).
   * @param opts.dryRun      If true, execute but do NOT cache. Returns result for inspection.
   */
  async transformData(
    componentId: string,
    rawData: Record<string, unknown>,
    transform: string,
    opts?: { ttlSeconds?: number; dryRun?: boolean },
  ): Promise<{
    outputKeys: string[];
    executionMs: number;
    cached: boolean;
    ttlSeconds: number | null;
  }> {
    const res = await this.fetch<{
      output_keys: string[];
      execution_ms: number;
      cached: boolean;
      ttl_seconds: number | null;
    }>("POST", `/api/components/${componentId}/data/transform`, {
      raw_data: rawData,
      transform,
      ttl_seconds: opts?.ttlSeconds ?? 3600,
      dry_run: opts?.dryRun ?? false,
    });
    return {
      outputKeys: res.output_keys,
      executionMs: res.execution_ms,
      cached: res.cached,
      ttlSeconds: res.ttl_seconds,
    };
  }

  /**
   * Run a transform against raw data WITHOUT caching — useful for previewing
   * what the LLM-generated code does before committing to a component.
   *
   * Returns the generated Python code and the transformed output dict.
   */
  async previewTransform(
    rawData: Record<string, unknown>,
    transform: string,
  ): Promise<{
    code: string;
    result: Record<string, unknown>;
    outputKeys: string[];
    executionMs: number;
  }> {
    const res = await this.fetch<{
      code: string;
      result: Record<string, unknown>;
      output_keys: string[];
      execution_ms: number;
    }>("POST", "/api/transform/preview", {
      raw_data: rawData,
      transform,
    });
    return {
      code: res.code,
      result: res.result,
      outputKeys: res.output_keys,
      executionMs: res.execution_ms,
    };
  }

  /**
   * Retrieve the last Python transform code generated for a component.
   * Only available while the cached result is still in Redis.
   */
  async getTransformCode(
    componentId: string,
  ): Promise<{ code: string; expiresInSeconds: number }> {
    const res = await this.fetch<{ code: string; expires_in_seconds: number }>(
      "GET",
      `/api/components/${componentId}/data/transform/code`,
    );
    return { code: res.code, expiresInSeconds: res.expires_in_seconds };
  }

  // ------------------------------------------------------------------
  // API Key management (requires 'admin' scope)
  // ------------------------------------------------------------------

  /** Create a new API key. The raw key is returned ONCE — store it safely. */
  async createApiKey(opts?: {
    label?: string;
    scopes?: string[];
    rateLimitRpm?: number;
  }): Promise<{ id: string; key: string; label: string; scopes: string[] }> {
    return this.fetch("POST", "/api/keys", {
      label: opts?.label ?? "Default Key",
      scopes: opts?.scopes ?? ["generate", "read"],
      rate_limit_rpm: opts?.rateLimitRpm ?? 60,
    });
  }

  /** List all active API keys for the current tenant/user. */
  async listApiKeys(): Promise<Array<{ id: string; label: string; key_prefix: string; scopes: string[] }>> {
    return this.fetch("GET", "/api/keys");
  }

  /** Revoke an API key by its ID. */
  async revokeApiKey(keyId: string): Promise<void> {
    return this.fetch("DELETE", `/api/keys/${keyId}`);
  }
}
