import { useState } from 'react';
import { ChatWindow } from './components/ChatWindow';
import { ComponentsView } from './components/ComponentsView';
import { Tabs, TabsList, TabsTrigger } from './components/ui/tabs';

type Tab = 'chat' | 'components';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('chat');

  return (
    <div className="h-screen flex flex-col bg-background">
      <div className="flex items-center justify-between px-4 py-2 border-b shadow-sm">
        <div className="flex items-center gap-4">
          <span className="text-xl font-bold">⚡ Spark AI</span>
          <span className="text-sm text-muted-foreground">Micro App Generator</span>
        </div>
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as Tab)}>
          <TabsList>
            <TabsTrigger value="chat">💬 Chat</TabsTrigger>
            <TabsTrigger value="components">🧩 Components</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      <div className="flex-1 overflow-hidden">
        {activeTab === 'chat' && <ChatWindow />}
        {activeTab === 'components' && <ComponentsView />}
      </div>
    </div>
  );
}

export default App;
