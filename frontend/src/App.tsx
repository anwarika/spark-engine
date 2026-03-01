import { useState } from 'react';
import { ChatWindow } from './components/ChatWindow';
import { ComponentsView } from './components/ComponentsView';
import { SandboxView } from './components/SandboxView';
import { Tabs, TabsList, TabsTrigger } from './components/ui/tabs';
import { MessageSquare, LayoutGrid, FlaskConical, Zap, Github } from 'lucide-react';

const GITHUB_REPO = 'https://github.com/your-org/spark';

type Tab = 'chat' | 'components' | 'sandbox';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('chat');

  const switchToChat = () => setActiveTab('chat');

  return (
    <div className="h-screen flex flex-col bg-background">
      <header className="flex-none flex items-center justify-between px-6 py-3 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-primary-foreground">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <span className="text-base font-semibold tracking-tight">Spark AI</span>
            <span className="hidden sm:inline text-xs text-muted-foreground ml-2">Micro App Generator</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as Tab)}>
            <TabsList className="h-9">
              <TabsTrigger value="chat" className="gap-1.5 text-xs sm:text-sm px-3">
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Chat</span>
              </TabsTrigger>
              <TabsTrigger value="components" className="gap-1.5 text-xs sm:text-sm px-3">
                <LayoutGrid className="w-3.5 h-3.5" />
                <span>Components</span>
              </TabsTrigger>
              <TabsTrigger value="sandbox" className="gap-1.5 text-xs sm:text-sm px-3">
                <FlaskConical className="w-3.5 h-3.5" />
                <span>Sandbox</span>
              </TabsTrigger>
            </TabsList>
          </Tabs>
          <a
            href={GITHUB_REPO}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <Github className="w-4 h-4" />
            <span className="hidden sm:inline">Star on GitHub</span>
          </a>
        </div>
      </header>
      <main className="flex-1 overflow-hidden">
        {activeTab === 'chat' && <ChatWindow />}
        {activeTab === 'components' && <ComponentsView />}
        {activeTab === 'sandbox' && <SandboxView onTryInChat={switchToChat} />}
      </main>
    </div>
  );
}

export default App;
