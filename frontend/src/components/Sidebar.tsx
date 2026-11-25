import { useState } from 'react';
import {
  Layers,
  Moon,
  PanelLeftClose,
  Search,
  Settings,
  SquarePen,
  Sun,
  Trash2,
} from 'lucide-react';
import { useChatStore } from '../store/useChatStore';

interface Props {
  theme: 'auto' | 'light' | 'dark';
  onToggleTheme: () => void;
}

export function Sidebar({ theme, onToggleTheme }: Props) {
  const [query, setQuery] = useState('');
  const {
    sidebarOpen,
    conversations,
    activeConvId,
    memories,
    drawerOpen,
    setSidebarOpen,
    setDrawerOpen,
    setSettingsOpen,
    startNewConversation,
    selectConversation,
    removeConversation,
  } = useChatStore();

  if (!sidebarOpen) return null;

  const activeMemCount = memories.filter((m) => m.is_enabled).length;
  const filtered = conversations.filter(
    (c) => !query.trim() || c.title.toLowerCase().includes(query.trim().toLowerCase()),
  );

  return (
    <aside
      aria-label="会话侧边栏"
      className="w-[256px] shrink-0 flex flex-col border-r"
      style={{ background: 'var(--mc-sidebar)', borderColor: 'var(--mc-border)' }}
    >
      {/* Top Bar */}
      <div className="h-[52px] px-3 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setSidebarOpen(false)}
          aria-label="收起侧边栏"
          className="w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer transition-colors hover:opacity-80"
          style={{ color: 'var(--mc-fg-muted)' }}
        >
          <PanelLeftClose size={18} strokeWidth={1.75} aria-hidden="true" />
        </button>

        <button
          type="button"
          onClick={startNewConversation}
          aria-label="新建对话"
          className="w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer transition-colors hover:opacity-80"
          style={{ color: 'var(--mc-fg-muted)' }}
        >
          <SquarePen size={18} strokeWidth={1.75} aria-hidden="true" />
        </button>
      </div>

      {/* Search Box */}
      <div className="px-3 pb-2">
        <div
          className="flex items-center gap-2 px-2.5 h-8 rounded-lg border text-xs"
          style={{ background: 'var(--mc-bg)', borderColor: 'var(--mc-border)' }}
        >
          <Search size={14} strokeWidth={1.75} style={{ color: 'var(--mc-fg-muted)' }} aria-hidden="true" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索对话..."
            aria-label="搜索历史对话"
            className="w-full bg-transparent outline-none text-xs"
          />
        </div>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-0.5 text-[13px]">
        {filtered.map((conv) => (
          <div
            key={conv.id}
            onClick={() => selectConversation(conv)}
            className="group flex items-center justify-between px-2.5 py-2 rounded-lg cursor-pointer transition-colors"
            style={{
              background: conv.id === activeConvId ? 'var(--mc-surface)' : 'transparent',
            }}
          >
            <span className="truncate pr-2">{conv.title}</span>
            <button
              type="button"
              aria-label={`删除会话 ${conv.title}`}
              onClick={(e) => {
                e.stopPropagation();
                removeConversation(conv.id);
              }}
              className="opacity-0 group-hover:opacity-100 w-6 h-6 rounded flex items-center justify-center cursor-pointer"
              style={{ color: 'var(--mc-fg-muted)' }}
            >
              <Trash2 size={13} strokeWidth={1.75} aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>

      {/* Bottom Anchored Utility Bar */}
      <div className="p-2.5 border-t space-y-1 text-[13px]" style={{ borderColor: 'var(--mc-border)' }}>
        <button
          type="button"
          onClick={() => setDrawerOpen(!drawerOpen)}
          className="w-full flex items-center justify-between px-2.5 py-2 rounded-lg cursor-pointer transition-colors"
          style={{ background: drawerOpen ? 'var(--mc-surface)' : 'transparent' }}
        >
          <span className="flex items-center gap-2.5">
            <Layers size={16} strokeWidth={1.75} aria-hidden="true" />
            <span>个人记忆库</span>
          </span>
          <span
            className="text-xs px-1.5 py-0.5 rounded-md border"
            style={{ borderColor: 'var(--mc-border)', color: 'var(--mc-fg-muted)' }}
          >
            {activeMemCount}
          </span>
        </button>

        <div className="flex items-center justify-between gap-1">
          <button
            type="button"
            onClick={() => setSettingsOpen(true)}
            aria-label="打开模型服务设置"
            className="flex-1 flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left cursor-pointer"
          >
            <Settings size={16} strokeWidth={1.75} aria-hidden="true" />
            <span>模型服务</span>
          </button>

          <button
            type="button"
            onClick={onToggleTheme}
            aria-label="切换深浅色主题"
            className="w-9 h-9 rounded-lg flex items-center justify-center cursor-pointer"
            style={{ color: 'var(--mc-fg-muted)' }}
          >
            {theme === 'dark' ? (
              <Sun size={16} strokeWidth={1.75} aria-hidden="true" />
            ) : (
              <Moon size={16} strokeWidth={1.75} aria-hidden="true" />
            )}
          </button>
        </div>
      </div>
    </aside>
  );
}
