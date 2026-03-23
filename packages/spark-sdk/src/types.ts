// ============================================================
// Spark SDK — shared types
// ============================================================

// ----------------------------------------------------------
// Auth / init
// ----------------------------------------------------------

export interface SparkClientConfig {
  /** Base URL of the Spark backend, e.g. "https://spark.yourapp.com" */
  baseUrl: string;
  /** Your tenant identifier */
  tenantId: string;
  /** The authenticated user's ID */
  userId: string;
  /**
   * Optional pre-built Bearer token (base64(tenantId:userId)).
   * If omitted the SDK builds it automatically from tenantId + userId.
   * In production, mint this on your backend and pass it here so
   * tenantId / userId are never hardcoded in the browser.
   */
  token?: string;
  /** Request timeout in ms (default 30 000) */
  timeoutMs?: number;
}

// ----------------------------------------------------------
// Components
// ----------------------------------------------------------

export interface SparkComponent {
  id: string;
  name: string;
  description: string;
  version: string;
  bundle_size_bytes: number;
  status: string;
  created_at: string;
  updated_at: string;
}

// ----------------------------------------------------------
// A2A generation
// ----------------------------------------------------------

export interface GenerateRequest {
  prompt: string;
  /** Existing component ID to iterate on */
  component_id?: string;
  data_context?: Record<string, unknown>;
  style_context?: Record<string, unknown>;
  llm_config?: Record<string, unknown>;
}

export interface GenerateResponse {
  status: "success" | "needs_info" | "error";
  microapp_url?: string;
  component_id?: string;
  parent_component_id?: string;
  missing_info?: Record<string, unknown>;
  message?: string;
}

// ----------------------------------------------------------
// Pinned apps
// ----------------------------------------------------------

export interface PinRequest {
  component_id: string;
  slot_name: string;
  description?: string;
  icon?: string;
  sort_order?: number;
  metadata?: Record<string, unknown>;
}

export interface PinnedApp {
  id: string;
  tenant_id: string;
  user_id: string;
  component_id: string;
  slot_name: string;
  description: string;
  icon: string;
  sort_order: number;
  metadata: Record<string, unknown>;
  pinned_at: string;
  updated_at: string;
  // Joined
  component_name?: string;
  component_version?: string;
  component_status?: string;
  /** Fully-resolved iframe URL ready to embed */
  iframe_url: string;
}

export interface RegenerateRequest {
  prompt?: string;
  data_context?: Record<string, unknown>;
  style_context?: Record<string, unknown>;
}

export interface RegenerateResponse extends PinnedApp {
  previous_component_id: string;
  new_component_id: string;
}

export interface UpdatePinMetaRequest {
  slot_name?: string;
  description?: string;
  icon?: string;
  sort_order?: number;
  metadata?: Record<string, unknown>;
}

// ----------------------------------------------------------
// spark:* postMessage event protocol
// ----------------------------------------------------------

/** Every event emitted by a Spark iframe follows this shape. */
export interface SparkEvent<T = unknown> {
  /** Always starts with "spark:" */
  type: string;
  componentId: string;
  payload: T;
  ts: number;
}

export interface SparkReadyPayload {
  componentId: string;
  timing?: Record<string, number>;
}

export interface SparkErrorPayload {
  message: string;
  type?: string;
  url?: string;
  line?: number;
  col?: number;
}

export interface SparkPinnedPayload {
  slotName: string;
  meta?: Record<string, unknown>;
}

export interface SparkActionPayload {
  actionType: string;
  data?: unknown;
}

export interface SparkDataAppliedPayload {
  mode: "sample" | "real";
}

/** Union of all known Spark events. The `type` field is the discriminant. */
export type AnySparkEvent =
  | SparkEvent<SparkReadyPayload>    // spark:ready
  | SparkEvent<SparkErrorPayload>    // spark:error
  | SparkEvent<SparkPinnedPayload>   // spark:pinned
  | SparkEvent<SparkActionPayload>   // spark:action
  | SparkEvent<SparkDataAppliedPayload> // spark:data_applied
  | SparkEvent<{ ts: number }>       // spark:pong

// ----------------------------------------------------------
// Inbound commands (host → iframe)
// ----------------------------------------------------------

export interface SparkDataCommand {
  type: "spark:data";
  payload: { mode: "sample" | "real"; data: unknown };
}

export interface SparkPingCommand {
  type: "spark:ping";
}

export type SparkCommand = SparkDataCommand | SparkPingCommand;
