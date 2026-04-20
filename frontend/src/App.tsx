import { useState, useEffect, useRef, useLayoutEffect } from 'react';
import { useChatStore } from './store/chatStore';
import { usePinStore } from './store/pinStore';
import { ChatWindow } from './components/ChatWindow';
import { ComponentsView } from './components/ComponentsView';
import { StudioView } from './components/StudioView';
import { DashboardCanvas } from './components/DashboardCanvas';
import { PinnedAppPanel } from './components/PinnedAppPanel';
import { Playground } from './components/Playground';
import { AdminDashboard } from './components/AdminDashboard';

type MainTab = 'playground' | 'chat' | 'components' | 'pinned' | 'dashboard' | 'admin';

function App() {
  const [activeTab, setActiveTab] = useState<MainTab>('playground');
  const tabsRef = useRef<HTMLDivElement>(null);
  const [indicator, setIndicator] = useState({ left: 0, width: 0 });
  const studioComponentId = useChatStore((s) => s.studioComponentId);
  const pinnedApps = usePinStore((s) => s.pinnedApps);
  const selectedPinId = usePinStore((s) => s.selectedPinId);
  const selectPin = usePinStore((s) => s.selectPin);
  const refreshPinnedApps = usePinStore((s) => s.refreshPinnedApps);
  const pinError = usePinStore((s) => s.error);

  useEffect(() => {
    refreshPinnedApps();
  }, [refreshPinnedApps]);

  useLayoutEffect(() => {
    const update = () => {
      const container = tabsRef.current;
      if (!container) return;
      const activeBtn = container.querySelector('[data-active="true"]') as HTMLElement | null;
      if (activeBtn) {
        setIndicator({
          left: activeBtn.offsetLeft,
          width: activeBtn.offsetWidth,
        });
      }
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, [activeTab, pinnedApps.length]);

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
          <div ref={tabsRef} className="tabs relative border-b border-base-300">
            <button
              type="button"
              className={`tab ${activeTab === 'playground' ? 'font-semibold' : 'opacity-70'}`}
              data-active={activeTab === 'playground' || undefined}
              onClick={() => setActiveTab('playground')}
            >
              Playground
            </button>
            <button
              type="button"
              className={`tab ${activeTab === 'chat' ? 'font-semibold' : 'opacity-70'}`}
              data-active={activeTab === 'chat' || undefined}
              onClick={() => setActiveTab('chat')}
            >
              Chat
            </button>
            <button
              type="button"
              className={`tab ${activeTab === 'components' ? 'font-semibold' : 'opacity-70'}`}
              data-active={activeTab === 'components' || undefined}
              onClick={() => setActiveTab('components')}
            >
              Components
            </button>
            <button
              type="button"
              className={`tab ${activeTab === 'pinned' ? 'font-semibold' : 'opacity-70'}`}
              data-active={activeTab === 'pinned' || undefined}
              onClick={() => setActiveTab('pinned')}
            >
              Pinned
              {pinnedApps.length > 0 ? (
                <span className="badge badge-sm badge-primary ml-1">{pinnedApps.length}</span>
              ) : null}
            </button>
            <button
              type="button"
              className={`tab ${activeTab === 'dashboard' ? 'font-semibold' : 'opacity-70'}`}
              data-active={activeTab === 'dashboard' || undefined}
              onClick={() => setActiveTab('dashboard')}
            >
              Dashboard
            </button>
            <button
              type="button"
              className={`tab ${activeTab === 'admin' ? 'font-semibold' : 'opacity-70'}`}
              data-active={activeTab === 'admin' || undefined}
              onClick={() => setActiveTab('admin')}
            >
              Admin
            </button>
            <div
              className="tab-indicator"
              style={{ left: indicator.left, width: indicator.width }}
              aria-hidden
            />
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
        {activeTab === 'playground' && <Playground />}
        {activeTab === 'chat' && <ChatWindow />}
        {activeTab === 'components' && <ComponentsView />}
        {activeTab === 'pinned' && <PinnedAppPanel />}
        {activeTab === 'dashboard' && <DashboardCanvas />}
        {activeTab === 'admin' && <AdminDashboard />}
      </div>
    </div>
  );
}

export default App;
