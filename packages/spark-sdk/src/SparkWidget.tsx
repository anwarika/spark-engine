/**
 * SparkWidget — headless React component for rendering a Spark micro-app.
 *
 * "Headless" means zero styling opinions. The component renders an <iframe>
 * with the correct sandbox attributes and wires up the spark:* event protocol.
 * All lifecycle and action events are surfaced as typed callbacks — the host
 * app is in full control of rendering the chrome around it.
 *
 * Usage:
 *   <SparkWidget
 *     iframeUrl={spark.iframeUrl(componentId)}
 *     onReady={(payload) => console.log('rendered in', payload.timing)}
 *     onPinned={(payload) => spark.pinApp({ component_id, slot_name: payload.slotName })}
 *     onAction={(payload) => handleWorkflowAction(payload)}
 *   />
 */

import React, {
  useRef,
  useEffect,
  useImperativeHandle,
  forwardRef,
  useCallback,
} from "react";

import type {
  SparkReadyPayload,
  SparkErrorPayload,
  SparkPinnedPayload,
  SparkActionPayload,
  SparkDataAppliedPayload,
  AnySparkEvent,
  SparkCommand,
} from "./types";

// ------------------------------------------------------------------
// Props
// ------------------------------------------------------------------

export interface SparkWidgetProps {
  /** Fully-resolved iframe URL from SparkClient.iframeUrl() */
  iframeUrl: string;

  // ---- Styling props (intentionally minimal) ----------------------
  /** className applied to the wrapping <div>. Default: none. */
  className?: string;
  /** Inline styles for the wrapping <div>. */
  style?: React.CSSProperties;
  /** className applied directly to the <iframe>. */
  iframeClassName?: string;
  /** Inline styles for the <iframe>. */
  iframeStyle?: React.CSSProperties;

  // ---- Lifecycle callbacks ----------------------------------------
  /** Fired when the app has finished rendering. Includes timing data. */
  onReady?: (payload: SparkReadyPayload) => void;
  /** Fired on any runtime error inside the iframe. */
  onError?: (payload: SparkErrorPayload) => void;
  /** Fired when the app requests to be pinned (user gesture inside app). */
  onPinned?: (payload: SparkPinnedPayload) => void;
  /** Fired when the app emits a custom action (future write surface). */
  onAction?: (payload: SparkActionPayload) => void;
  /** Fired after a data swap has been applied inside the iframe. */
  onDataApplied?: (payload: SparkDataAppliedPayload) => void;
  /** Catch-all for any spark:* event not handled above. */
  onEvent?: (event: AnySparkEvent) => void;

  /**
   * Title for the iframe (accessibility). Defaults to "Spark micro-app".
   */
  title?: string;
}

// ------------------------------------------------------------------
// Imperative handle — lets parents push commands into the iframe
// ------------------------------------------------------------------

export interface SparkWidgetHandle {
  /** Push real (or sample) data into the running app via postMessage. */
  sendData(data: unknown, mode?: "real" | "sample"): void;
  /** Ping the iframe — onReady callback fires with spark:pong on success. */
  ping(): void;
  /** Send any raw SparkCommand to the iframe. */
  send(cmd: SparkCommand): void;
  /** The underlying <iframe> element (null before mount). */
  iframe: HTMLIFrameElement | null;
}

// ------------------------------------------------------------------
// Component
// ------------------------------------------------------------------

export const SparkWidget = forwardRef<SparkWidgetHandle, SparkWidgetProps>(
  function SparkWidget(props, ref) {
    const {
      iframeUrl,
      className,
      style,
      iframeClassName,
      iframeStyle,
      onReady,
      onError,
      onPinned,
      onAction,
      onDataApplied,
      onEvent,
      title = "Spark micro-app",
    } = props;

    const iframeRef = useRef<HTMLIFrameElement>(null);

    // ------------------------------------------------------------------
    // Outbound — send a command to the iframe
    // ------------------------------------------------------------------

    const send = useCallback((cmd: SparkCommand) => {
      iframeRef.current?.contentWindow?.postMessage(cmd, "*");
    }, []);

    // ------------------------------------------------------------------
    // Imperative handle
    // ------------------------------------------------------------------

    useImperativeHandle(
      ref,
      () => ({
        sendData(data: unknown, mode: "real" | "sample" = "real") {
          send({ type: "spark:data", payload: { mode, data } });
        },
        ping() {
          send({ type: "spark:ping" });
        },
        send,
        get iframe() {
          return iframeRef.current;
        },
      }),
      [send],
    );

    // ------------------------------------------------------------------
    // Inbound — listen for spark:* events from the iframe
    // ------------------------------------------------------------------

    useEffect(() => {
      function handleMessage(event: MessageEvent) {
        const msg = event.data as AnySparkEvent;
        if (!msg || typeof msg.type !== "string" || !msg.type.startsWith("spark:")) {
          return;
        }

        // Route to specific callbacks
        switch (msg.type) {
          case "spark:ready":
            onReady?.(msg.payload as SparkReadyPayload);
            break;
          case "spark:error":
            onError?.(msg.payload as SparkErrorPayload);
            break;
          case "spark:pinned":
            onPinned?.(msg.payload as SparkPinnedPayload);
            break;
          case "spark:action":
            onAction?.(msg.payload as SparkActionPayload);
            break;
          case "spark:data_applied":
            onDataApplied?.(msg.payload as SparkDataAppliedPayload);
            break;
        }

        // Always call catch-all
        onEvent?.(msg);
      }

      window.addEventListener("message", handleMessage);
      return () => window.removeEventListener("message", handleMessage);
    }, [onReady, onError, onPinned, onAction, onDataApplied, onEvent]);

    // ------------------------------------------------------------------
    // Render
    // ------------------------------------------------------------------

    return (
      <div className={className} style={style}>
        <iframe
          ref={iframeRef}
          src={iframeUrl}
          title={title}
          className={iframeClassName}
          style={{
            border: "none",
            width: "100%",
            height: "100%",
            ...iframeStyle,
          }}
          sandbox="allow-scripts allow-same-origin"
          loading="lazy"
        />
      </div>
    );
  },
);

SparkWidget.displayName = "SparkWidget";
