import { useState, useEffect } from 'react';
import { useChatStore } from './store/chatStore';
import { usePinStore } from './store/pinStore';
import { ChatWindow } from './components/ChatWindow';
import { ComponentsView } from './components/ComponentsView';
import { StudioView } from './components/StudioView';
import { DashboardCanvas } from './components/DashboardCanvas';
import { PinnedAppPanel } from './components/PinnedAppPanel';

type MainTab = 'chat' | 'components' | 'pinned' | 'dashboard';

function App() {
  const [activeTab, setActiveTab] = useState<MainTab>('chat');
  const studioComponentId = useChatStore((s) => s.studioComponentId);
  const pinnedApps = usePinStore((s) => s.pinnedApps);
  const selectedPinId = usePinStore((s) => s.selectedPinId);
  const selectPin = usePinStore((s) => s.selectPin);
  const refreshPinnedApps = usePinStore((s) => s.refreshPinnedApps);
  const pinError = usePinStore((s) => s.error);

  useEffect(() => {
    refreshPinnedApps();
  }, [refreshPinnedApps]);

  if (studioComponentId) {
    return <StudioView />;
  }

  return (
    <div className="h-screen flex flex-col bg-base-100">
      <div className="navbar bg-base-300 shadow-lg flex-wrap gap-2 py-2 min-h-0">
        <div className="flex-1 min-w-[200px]">
          <span className="text-xl font-bold">⚡ Spark AI</span>
          <span className="text-sm ml-4 opacity-70">Micro App Generator</span>
        </div>
        <div className="flex-none">
          <div className="tabs tabs-bordered">
            <button
              type="button"
              className={`tab ${activeTab === 'chat' ? 'tab-active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              Chat
            </button>
            <button
              type="button"
              className={`tab ${activeTab === 'components' ? 'tab-active' : ''}`}
              onClick={() => setActiveTab('components')}
            >
              Components
            </button>
            <button
              type="button"
              className={`tab ${activeTab === 'pinned' ? 'tab-active' : ''}`}
              onClick={() => setActiveTab('pinned')}
            >
              Pinned
              {pinnedApps.length > 0 ? (
                <span className="badge badge-sm badge-primary ml-1">{pinnedApps.length}</span>
              ) : null}
            </button>
            <button
              type="button"
              className={`tab ${activeTab === 'dashboard' ? 'tab-active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              Dashboard
            </button>
          </div>
        </div>
      </div>

      {pinnedApps.length > 0 && (
        <div className="flex-none px-4 py-2 bg-base-200 border-b border-base-300 flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold opacity-70 shrink-0">Pins:</span>
          <div className="flex flex-wrap gap-1 overflow-x-auto">
            {pinnedApps.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`btn btn-xs ${p.id === selectedPinId && activeTab === 'pinned' ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => {
                  selectPin(p.id);
                  setActiveTab('pinned');
                }}
              >
                {p.icon ? <span className="mr-0.5">{p.icon}</span> : null}
                {p.slot_name}
              </button>
            ))}
          </div>
        </div>
      )}

      {pinError && (
        <div className="alert alert-warning rounded-none py-2 min-h-0 text-sm">
          <span>{pinError}</span>
          <button type="button" className="btn btn-ghost btn-xs" onClick={() => usePinStore.getState().clearError()}>
            Dismiss
          </button>
        </div>
      )}

      <div className="flex-1 overflow-hidden min-h-0">
        {activeTab === 'chat' && <ChatWindow />}
        {activeTab === 'components' && <ComponentsView />}
        {activeTab === 'pinned' && <PinnedAppPanel />}
        {activeTab === 'dashboard' && <DashboardCanvas />}
      </div>
    </div>
  );
}

export default App;
