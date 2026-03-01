import { useState } from 'react';
import { useChatStore } from './store/chatStore';
import { ChatWindow } from './components/ChatWindow';
import { ComponentsView } from './components/ComponentsView';
import { StudioView } from './components/StudioView';

type Tab = 'chat' | 'components';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  const studioComponentId = useChatStore((s) => s.studioComponentId);

  if (studioComponentId) {
    return <StudioView />;
  }

  return (
    <div className="h-screen flex flex-col bg-base-100">
      <div className="navbar bg-base-300 shadow-lg">
        <div className="flex-1">
          <span className="text-xl font-bold">⚡ Spark AI</span>
          <span className="text-sm ml-4 opacity-70">Micro App Generator</span>
        </div>
        <div className="flex-none">
          <div className="tabs tabs-boxed">
            <button
              className={`tab ${activeTab === 'chat' ? 'tab-active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              💬 Chat
            </button>
            <button
              className={`tab ${activeTab === 'components' ? 'tab-active' : ''}`}
              onClick={() => setActiveTab('components')}
            >
              🧩 Components
            </button>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-hidden">
        {activeTab === 'chat' && <ChatWindow />}
        {activeTab === 'components' && <ComponentsView />}
      </div>
    </div>
  );
}

export default App;
