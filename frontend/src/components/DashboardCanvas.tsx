import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import GridLayout, { WidthProvider, type Layout } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { usePinStore } from '../store/pinStore';
import { useChatStore } from '../store/chatStore';
import { dashboardsAPI } from '../services/api';
import { MicroappIframe } from './MicroappIframe';
import type { DashboardLayoutItem } from '../types';

const Grid = WidthProvider(GridLayout);

function layoutToRgl(items: DashboardLayoutItem[]): Layout[] {
  return items.map((it) => ({
    i: it.i,
    x: it.x,
    y: it.y,
    w: it.w,
    h: it.h,
    minW: it.minW,
    minH: it.minH,
  }));
}

function rglToLayout(layout: Layout[]): DashboardLayoutItem[] {
  return layout.map((l) => ({
    i: l.i,
    x: l.x,
    y: l.y,
    w: l.w,
    h: l.h,
    minW: l.minW,
    minH: l.minH,
  }));
}

function filterLayoutForPins(layout: Layout[], pinIds: Set<string>): Layout[] {
  return layout.filter((l) => pinIds.has(l.i));
}

export const DashboardCanvas: React.FC = () => {
  const pinnedApps = usePinStore((s) => s.pinnedApps);
  const refreshPinnedApps = usePinStore((s) => s.refreshPinnedApps);
  const pinComponent = usePinStore((s) => s.pinComponent);
  const pinIds = useMemo(() => new Set(pinnedApps.map((p) => p.id)), [pinnedApps]);

  const enterStudioMode = useChatStore((s) => s.enterStudioMode);
  const messages = useChatStore((s) => s.messages);

  const [layout, setLayout] = useState<Layout[]>([]);
  const [loading, setLoading] = useState(true);
  const [saveError, setSaveError] = useState<string | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [addPinId, setAddPinId] = useState<string>('');

  const load = useCallback(async () => {
    setLoading(true);
    setSaveError(null);
    try {
      await refreshPinnedApps();
      const pins = usePinStore.getState().pinnedApps;
      const ids = new Set(pins.map((p) => p.id));
      const { layout: saved } = await dashboardsAPI.getLayout('default');
      const rgl = layoutToRgl(saved);
      setLayout(filterLayoutForPins(rgl, ids));
    } catch (e) {
      console.error(e);
      setSaveError('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, [refreshPinnedApps]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    };
  }, []);

  useEffect(() => {
    setLayout((prev) => filterLayoutForPins(prev, pinIds));
  }, [pinIds]);

  const scheduleSave = useCallback((next: Layout[]) => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      try {
        await dashboardsAPI.saveLayout(rglToLayout(next), 'default');
        setSaveError(null);
      } catch (e) {
        console.error(e);
        setSaveError('Failed to save layout');
      }
    }, 600);
  }, []);

  const onLayoutChange = useCallback(
    (_layout: Layout[]) => {
      setLayout(_layout);
      scheduleSave(_layout);
    },
    [scheduleSave]
  );

  const removeWidget = useCallback(
    (pinId: string) => {
      const next = layout.filter((l) => l.i !== pinId);
      setLayout(next);
      scheduleSave(next);
    },
    [layout, scheduleSave]
  );

  const addWidget = useCallback(() => {
    if (!addPinId || layout.some((l) => l.i === addPinId)) return;
    const maxY = layout.reduce((m, l) => Math.max(m, l.y + l.h), 0);
    const next: Layout[] = [
      ...layout,
      { i: addPinId, x: 0, y: maxY, w: 4, h: 8, minW: 2, minH: 4 },
    ];
    setLayout(next);
    scheduleSave(next);
    setAddPinId('');
  }, [addPinId, layout, scheduleSave]);

  const pinsOnCanvas = useMemo(
    () => pinnedApps.filter((p) => layout.some((l) => l.i === p.id)),
    [pinnedApps, layout]
  );

  const pinsNotOnCanvas = useMemo(
    () => pinnedApps.filter((p) => !layout.some((l) => l.i === p.id)),
    [pinnedApps, layout]
  );

  const handleSparkPinned = useCallback(
    async (detail: { componentId: string; slotName: string; meta?: Record<string, unknown> }) => {
      try {
        await pinComponent(detail.componentId, detail.slotName, { metadata: detail.meta });
        await refreshPinnedApps();
      } catch {
        /* pinStore sets error */
      }
    },
    [pinComponent, refreshPinnedApps]
  );

  if (loading && pinnedApps.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="loading loading-spinner loading-lg" />
      </div>
    );
  }

  return (
    <div className="p-4 h-full flex flex-col min-h-0">
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <p className="text-sm text-base-content/70">
          Drag and resize pinned apps. Layout is saved per user.
        </p>
        {saveError && <span className="text-error text-sm">{saveError}</span>}
        <div className="flex flex-wrap items-center gap-2 ml-auto">
          <select
            className="select select-bordered select-sm"
            value={addPinId}
            onChange={(e) => setAddPinId(e.target.value)}
            aria-label="Add pinned app to dashboard"
          >
            <option value="">Add pinned app…</option>
            {pinsNotOnCanvas.map((p) => (
              <option key={p.id} value={p.id}>
                {p.icon ? `${p.icon} ` : ''}
                {p.slot_name}
              </option>
            ))}
          </select>
          <button type="button" className="btn btn-sm btn-primary" onClick={addWidget} disabled={!addPinId}>
            Add to canvas
          </button>
        </div>
      </div>

      {pinnedApps.length === 0 ? (
        <div className="alert alert-info">
          <span>Pin apps from Chat or Components first, then add them to the dashboard.</span>
        </div>
      ) : (
        <div className="flex-1 min-h-[480px] overflow-auto bg-base-200/50 rounded-lg p-2">
          <Grid
            className="layout"
            cols={12}
            rowHeight={30}
            margin={[8, 8]}
            containerPadding={[8, 8]}
            layout={layout}
            onLayoutChange={onLayoutChange}
            draggableHandle=".widget-drag-handle"
            compactType="vertical"
            preventCollision={false}
          >
            {pinsOnCanvas.map((pin) => (
              <div key={pin.id} className="bg-base-100 rounded-lg shadow flex flex-col overflow-hidden border border-base-300">
                <div className="widget-drag-handle flex-none flex items-center justify-between gap-2 px-2 py-1 bg-base-300 cursor-grab active:cursor-grabbing">
                  <span className="text-sm font-semibold truncate">
                    {pin.icon ? `${pin.icon} ` : ''}
                    {pin.slot_name}
                  </span>
                  <button
                    type="button"
                    className="btn btn-ghost btn-xs"
                    onClick={() => removeWidget(pin.id)}
                    title="Remove from dashboard"
                  >
                    Remove
                  </button>
                </div>
                <div className="flex-1 min-h-0 overflow-auto p-1">
                  <MicroappIframe
                    componentId={pin.component_id}
                    variant="panel"
                    onIterate={() => {
                      const src = messages.find((m) => m.componentId === pin.component_id);
                      enterStudioMode(pin.component_id, src?.id ?? '');
                    }}
                    onSparkPinned={handleSparkPinned}
                  />
                </div>
              </div>
            ))}
          </Grid>
        </div>
      )}
    </div>
  );
};
