/**
 * SparkNavBar — reference nav bar component for pinned apps.
 *
 * This is an ADOPTABLE reference, not an opinionated library component.
 * It is intentionally unstyled (no CSS imports, no Tailwind classes) so
 * integrators can fork it and apply their own design system.
 *
 * It renders a horizontal (or vertical) strip of pinned app bookmarks.
 * Each item shows the icon + slot_name and fires onSelect when clicked.
 *
 * Usage:
 *   <SparkNavBar
 *     apps={pinnedApps}
 *     activeId={currentPinId}
 *     onSelect={(pin) => setCurrentPin(pin)}
 *     onUnpin={(pinId) => unpin(pinId)}
 *     renderItem={(pin, isActive) => <MyCustomNavItem pin={pin} active={isActive} />}
 *   />
 */

import React from "react";
import type { PinnedApp } from "./types";

// ------------------------------------------------------------------
// Props
// ------------------------------------------------------------------

export interface SparkNavBarProps {
  /** The list of pinned apps to display. */
  apps: PinnedApp[];
  /** The currently active pin ID, if any. */
  activeId?: string | null;
  /** Fired when the user clicks a pin item. */
  onSelect?: (pin: PinnedApp) => void;
  /** Fired when the user triggers an unpin action. */
  onUnpin?: (pinId: string) => void;
  /** Layout direction. Default: "horizontal". */
  direction?: "horizontal" | "vertical";
  /** className for the outer container. */
  className?: string;
  /** Inline styles for the outer container. */
  style?: React.CSSProperties;
  /**
   * Optional custom renderer for each nav item.
   * If provided, this completely replaces the default item rendering.
   * The component is responsible for calling onSelect / onUnpin itself.
   */
  renderItem?: (
    pin: PinnedApp,
    isActive: boolean,
    handlers: {
      onSelect: () => void;
      onUnpin: () => void;
    },
  ) => React.ReactNode;
  /** Shown when apps is empty. */
  emptyState?: React.ReactNode;
}

// ------------------------------------------------------------------
// Default item
// ------------------------------------------------------------------

interface DefaultItemProps {
  pin: PinnedApp;
  isActive: boolean;
  onSelect: () => void;
  onUnpin: () => void;
}

function DefaultNavItem({ pin, isActive, onSelect, onUnpin }: DefaultItemProps) {
  return (
    <div
      data-spark-pin-id={pin.id}
      data-spark-active={isActive}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        padding: "6px 10px",
        cursor: "pointer",
        userSelect: "none",
        position: "relative",
        opacity: isActive ? 1 : 0.75,
        fontWeight: isActive ? 600 : 400,
      }}
      role="button"
      tabIndex={0}
      aria-current={isActive ? "page" : undefined}
      aria-label={pin.slot_name}
      onClick={onSelect}
      onKeyDown={(e) => e.key === "Enter" && onSelect()}
    >
      {pin.icon && (
        <span aria-hidden="true" style={{ fontSize: "1rem" }}>
          {pin.icon}
        </span>
      )}
      <span>{pin.slot_name}</span>
      <button
        aria-label={`Unpin ${pin.slot_name}`}
        style={{
          marginLeft: "4px",
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: "2px 4px",
          opacity: 0.5,
          fontSize: "0.75rem",
          lineHeight: 1,
        }}
        onClick={(e) => {
          e.stopPropagation();
          onUnpin();
        }}
      >
        ✕
      </button>
    </div>
  );
}

// ------------------------------------------------------------------
// SparkNavBar
// ------------------------------------------------------------------

export function SparkNavBar({
  apps,
  activeId,
  onSelect,
  onUnpin,
  direction = "horizontal",
  className,
  style,
  renderItem,
  emptyState,
}: SparkNavBarProps) {
  if (apps.length === 0) {
    return emptyState ? <>{emptyState}</> : null;
  }

  return (
    <nav
      className={className}
      style={{
        display: "flex",
        flexDirection: direction === "vertical" ? "column" : "row",
        alignItems: direction === "vertical" ? "stretch" : "center",
        gap: "2px",
        ...style,
      }}
      aria-label="Pinned apps"
    >
      {apps.map((pin) => {
        const isActive = pin.id === activeId;
        const handlers = {
          onSelect: () => onSelect?.(pin),
          onUnpin: () => onUnpin?.(pin.id),
        };

        if (renderItem) {
          return (
            <React.Fragment key={pin.id}>
              {renderItem(pin, isActive, handlers)}
            </React.Fragment>
          );
        }

        return (
          <DefaultNavItem
            key={pin.id}
            pin={pin}
            isActive={isActive}
            onSelect={handlers.onSelect}
            onUnpin={handlers.onUnpin}
          />
        );
      })}
    </nav>
  );
}
