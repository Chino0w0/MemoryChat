import { useEffect, useState } from 'react';
import { ChatArea } from './components/ChatArea';
import { MemoryDrawer } from './components/MemoryDrawer';
import { ModelSettings } from './components/ModelSettings';
import { Sidebar } from './components/Sidebar';
import { useChatStore } from './store/useChatStore';

export default function App() {
  const [theme, setTheme] = useState<'auto' | 'light' | 'dark'>('auto');
  const bootstrap = useChatStore((s) => s.bootstrap);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'auto') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', theme);
  }, [theme]);

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <Sidebar
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
      />
      <ChatArea />
      <MemoryDrawer />
      <ModelSettings />
    </div>
  );
}
