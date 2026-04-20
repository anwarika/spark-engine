// Core client
export { SparkClient, SparkError } from "./SparkClient";

// Typed errors
export {
  SparkError as SparkBaseError,
  SparkAuthError,
  SparkPermissionError,
  SparkRateLimitError,
  SparkGenerationError,
  SparkTimeoutError,
} from "./errors";

// React components
export { SparkWidget } from "./SparkWidget";
export type { SparkWidgetProps, SparkWidgetHandle } from "./SparkWidget";

export { SparkNavBar } from "./SparkNavBar";
export type { SparkNavBarProps } from "./SparkNavBar";

// React hook
export { useSpark } from "./useSpark";
export type { UseSparkReturn, UseSparkState, UseSparkActions, SparkStatus } from "./useSpark";

// All types
export type {
  SparkClientConfig,
  SparkComponent,
  GenerateRequest,
  GenerateResponse,
  PinRequest,
  PinnedApp,
  RegenerateRequest,
  RegenerateResponse,
  UpdatePinMetaRequest,
  SparkEvent,
  SparkReadyPayload,
  SparkErrorPayload,
  SparkPinnedPayload,
  SparkActionPayload,
  SparkDataAppliedPayload,
  AnySparkEvent,
  SparkCommand,
  SparkDataCommand,
  SparkPingCommand,
} from "./types";
