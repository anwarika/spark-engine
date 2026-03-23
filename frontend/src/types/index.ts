export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  componentId?: string;
  reasoning?: string;
  timestamp: Date;
}

export interface SendMessagePayload {
  session_id: string;
  message: string;
  tenant_id: string;
  user_id: string;
  component_id?: string;  // Present in studio mode for iteration
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

// --- Pinned apps (aligned with /api/apps and @spark-engine/sdk types) ---

export interface PinAppRequestBody {
  component_id: string;
  slot_name: string;
  description?: string;
  icon?: string;
  sort_order?: number;
  metadata?: Record<string, unknown>;
}

export interface UpdatePinMetaRequestBody {
  slot_name?: string;
  description?: string;
  icon?: string;
  sort_order?: number;
  metadata?: Record<string, unknown>;
}

export interface RegeneratePinRequestBody {
  prompt?: string;
  data_context?: Record<string, unknown>;
  style_context?: Record<string, unknown>;
}

/** Row from GET /api/apps — iframe_url added by backend */
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
  component_name?: string;
  component_version?: string;
  component_status?: string;
  iframe_url: string;
}

export interface RegeneratePinResponse extends PinnedApp {
  previous_component_id: string;
  new_component_id: string;
}

/** iframe postMessage: spark:pinned (from window.spark.pin) */
export interface SparkPinnedMessagePayload {
  slotName?: string;
  meta?: Record<string, unknown>;
}

export interface SparkPinnedPostMessage {
  type: 'spark:pinned';
  componentId: string;
  payload: SparkPinnedMessagePayload;
  ts: number;
}

// --- Dashboard layout (GET/PUT /api/dashboards/layout) ---

export interface DashboardLayoutItem {
  /** Stable widget key — use pin_id for react-grid-layout `i` */
  i: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
}

export interface DashboardLayoutResponse {
  name: string;
  layout: DashboardLayoutItem[];
}
