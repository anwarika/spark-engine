import React, { useEffect } from 'react';
import { usePinStore } from '../store/pinStore';
import { useChatStore } from '../store/chatStore';
import { MicroappIframe } from './MicroappIframe';

export const PinnedAppPanel: React.FC = () => {
  const pinnedApps = usePinStore((s) => s.pinnedApps);
  const selectedPinId = usePinStore((s) => s.selectedPinId);
  const selectPin = usePinStore((s) => s.selectPin);
  const unpin = usePinStore((s) => s.unpin);
  const regeneratePin = usePinStore((s) => s.regeneratePin);
  const loading = usePinStore((s) => s.loading);
  const error = usePinStore((s) => s.error);
  const refreshPinnedApps = usePinStore((s) => s.refreshPinnedApps);

  const enterStudioMode = useChatStore((s) => s.enterStudioMode);
  const messages = useChatStore((s) => s.messages);

  useEffect(() => {
    if (pinnedApps.length > 0 && !selectedPinId) {
      selectPin(pinnedApps[0].id);
    }
  }, [pinnedApps, selectedPinId, selectPin]);

  useEffect(() => {
    if (
      selectedPinId &&
      pinnedApps.length > 0 &&
      !pinnedApps.some((p) => p.id === selectedPinId)
    ) {
      selectPin(pinnedApps[0].id);
    }
  }, [pinnedApps, selectedPinId, selectPin]);

  const pin = pinnedApps.find((p) => p.id === selectedPinId);

  const handleRegenerate = async () => {
    if (!selectedPinId) return;
    const prompt = window.prompt('Optional: new prompt for regeneration (leave empty to reuse stored prompt)');
    if (prompt === null) return;
    try {
      await regeneratePin(selectedPinId, prompt || undefined);
    } catch {
      /* store sets error */
    }
  };

  if (pinnedApps.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-6">
        <div className="text-center max-w-md space-y-2">
          <h2 className="text-2xl font-bold">No pinned apps</h2>
          <p className="text-base-content/70">
            Use <strong>Pin</strong> on a microapp in Chat or Components, or trigger{' '}
            <code className="text-xs">spark.pin()</code> from inside an app.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col md:flex-row min-h-0">
      <aside className="w-full md:w-56 flex-none border-b md:border-b-0 md:border-r border-base-300 p-3 overflow-y-auto bg-base-200/50">
        <div className="flex items-center justify-between mb-2">
          <span className="font-semibold text-sm">Pinned</span>
          <button type="button" className="btn btn-ghost btn-xs" onClick={() => refreshPinnedApps()}>
            Refresh
          </button>
        </div>
        <ul className="menu menu-sm p-0 gap-1">
          {pinnedApps.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                className={p.id === selectedPinId ? 'active' : ''}
                onClick={() => selectPin(p.id)}
              >
                {p.icon ? <span className="mr-1">{p.icon}</span> : null}
                {p.slot_name}
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        {error && (
          <div className="alert alert-warning mb-4">
            <span>{error}</span>
          </div>
        )}
        {pin && (
          <div className="max-w-5xl mx-auto space-y-3">
            <div className="flex flex-wrap items-center gap-2 justify-between">
              <h2 className="text-xl font-bold">
                {pin.icon ? `${pin.icon} ` : ''}
                {pin.slot_name}
              </h2>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn btn-sm btn-outline"
                  disabled={loading}
                  onClick={handleRegenerate}
                >
                  Regenerate
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-error btn-outline"
                  onClick={async () => {
                    if (!window.confirm(`Unpin "${pin.slot_name}"?`)) return;
                    try {
                      await unpin(pin.id);
                    } catch {
                      /* handled */
                    }
                  }}
                >
                  Unpin
                </button>
              </div>
            </div>
            <MicroappIframe
              key={pin.component_id}
              componentId={pin.component_id}
              onIterate={() => {
                const src = messages.find((m) => m.componentId === pin.component_id);
                enterStudioMode(pin.component_id, src?.id ?? '');
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
};
