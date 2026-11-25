import { useEffect, useState } from 'react';
import {
  Brain,
  ChevronDown,
  Ghost,
  MessageSquare,
  Moon,
  Plus,
  Settings2,
  Sun,
  Trash2,
} from 'lucide-react';
import { api } from './api';
import { ChatStage } from './components/ChatStage';
import { MemoryDrawer } from './components/MemoryDrawer';
import { ProviderDialog } from './components/ProviderDialog';
import type {
  ChatMessage,
  Conversation,
  ExtensionSlot,
  MemoryItem,
  MemoryLayer,
  ModelProvider,
  ProviderPreset,
  SessionSummary,
} from './types';

export default function App() {
  const [presets, setPresets] = useState<ProviderPreset[]>([]);
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [summaries, setSummaries] = useState<SessionSummary[]>([]);
  const [extensionSlots, setExtensionSlots] = useState<ExtensionSlot[]>([]);

  const [selectedProviderId, setSelectedProviderId] = useState<string>('demo');
  const [selectedModel, setSelectedModel] = useState<string>('memorychat-demo');
  const [incognito, setIncognito] = useState<boolean>(false);
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [modelMenuOpen, setModelMenuOpen] = useState<boolean>(false);
  const [providerDialogOpen, setProviderDialogOpen] = useState<boolean>(false);
  const [streaming, setStreaming] = useState<boolean>(false);
  const [topK, setTopK] = useState<number>(5);
  const [threshold, setThreshold] = useState<number>(0.15);
  const [theme, setTheme] = useState<'auto' | 'light' | 'dark'>('auto');

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'auto') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', theme);
  }, [theme]);

  const refreshMemories = async () => {
    const [mems, sums] = await Promise.all([api.getMemories(), api.getSummaries()]);
    setMemories(mems);
    setSummaries(sums);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [presetList, provList, convList, memList, slotList] = await Promise.all([
        api.getPresets(),
        api.getProviders(),
        api.getConversations(),
        api.getMemories(),
        api.getExtensionSlots(),
      ]);
      if (cancelled) return;
      setPresets(presetList);
      setProviders(provList);
      setConversations(convList);
      setMemories(memList);
      setExtensionSlots(slotList);

      const nonDemo = provList.find((p) => p.id !== 'demo' && p.has_key);
      const activeProv = nonDemo || provList[0];
      if (activeProv) {
        setSelectedProviderId(activeProv.id);
        setSelectedModel(activeProv.models[0] || 'memorychat-demo');
      }
      if (convList.length > 0) {
        setActiveConvId(convList[0].id);
        setIncognito(!convList[0].memory_enabled);
        const msgs = await api.getMessages(convList[0].id);
        if (!cancelled) setMessages(msgs);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectConversation = async (conv: Conversation) => {
    setActiveConvId(conv.id);
    setIncognito(!conv.memory_enabled);
    const msgs = await api.getMessages(conv.id);
    setMessages(msgs);
  };

  const handleNewConversation = async () => {
    const created = await api.createConversation({
      title: '新对话',
      active_provider_id: selectedProviderId,
      active_model: selectedModel,
      memory_enabled: !incognito,
    });
    setConversations((prev) => [created, ...prev]);
    setActiveConvId(created.id);
    setMessages([]);
  };

  const handleToggleIncognito = async () => {
    const next = !incognito;
    setIncognito(next);
    if (activeConvId) {
      await api.patchConversation(activeConvId, { memory_enabled: !next });
    }
  };

  const handleSend = async (text: string) => {
    let convId = activeConvId;
    if (!convId) {
      const created = await api.createConversation({
        title: text.slice(0, 18),
        active_provider_id: selectedProviderId,
        active_model: selectedModel,
        memory_enabled: !incognito,
      });
      setConversations((prev) => [created, ...prev]);
      convId = created.id;
      setActiveConvId(convId);
    }

    const tempUserId = `u_${Date.now()}`;
    const tempAsstId = `a_${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: tempUserId, conversation_id: convId!, role: 'user', content: text, memory_refs: [], memory_events: [] },
      { id: tempAsstId, conversation_id: convId!, role: 'assistant', content: '', memory_refs: [], memory_events: [], streaming: true },
    ]);
    setStreaming(true);

    try {
      await api.streamChat(
        {
          conversation_id: convId,
          content: text,
          provider_id: selectedProviderId,
          model: selectedModel,
          memory_enabled: !incognito,
          top_k: topK,
          threshold,
        },
        {
          onContext: (items) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === tempAsstId ? { ...m, memory_refs: items } : m)),
            );
          },
          onDelta: (delta) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === tempAsstId ? { ...m, content: m.content + delta } : m)),
            );
          },
          onMemoryUpdated: (ev) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === tempUserId ? { ...m, memory_events: [...m.memory_events, ev] } : m)),
            );
            refreshMemories();
          },
          onDone: () => {
            setMessages((prev) =>
              prev.map((m) => (m.id === tempAsstId ? { ...m, streaming: false } : m)),
            );
          },
        },
      );
      const updatedConvs = await api.getConversations();
      setConversations(updatedConvs);
    } finally {
      setStreaming(false);
    }
  };

  const activeMemoryCount = memories.filter((m) => m.is_enabled).length;

  return (
    <div className="app-shell">
      {/* Left Minimal Sidebar */}
      <nav className="sidebar" aria-label="会话导航栏">
        <button
          type="button"
          className="icon-btn primary"
          style={{ width: '100%', justifyContent: 'center', padding: '9px 12px' }}
          onClick={handleNewConversation}
          aria-label="新建对话"
        >
          <Plus size={16} aria-hidden="true" />
        </button>

        <div className="scroller" style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
          {conversations.map((c) => (
            <div
              key={c.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '7px 10px',
                borderRadius: 10,
                background: c.id === activeConvId ? 'var(--brand-soft)' : 'transparent',
                color: c.id === activeConvId ? 'var(--brand)' : 'var(--fg)',
                cursor: 'pointer',
                fontSize: 13,
              }}
              onClick={() => selectConversation(c)}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: 7, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <MessageSquare size={14} aria-hidden="true" />
                {c.title}
              </span>
              <button
                type="button"
                aria-label={`删除会话 ${c.title}`}
                onClick={async (e) => {
                  e.stopPropagation();
                  await api.deleteConversation(c.id);
                  setConversations((prev) => prev.filter((item) => item.id !== c.id));
                  if (activeConvId === c.id) {
                    setActiveConvId(null);
                    setMessages([]);
                  }
                }}
                style={{ border: 'none', background: 'transparent', color: 'var(--fg-muted)', cursor: 'pointer', padding: 2 }}
              >
                <Trash2 size={13} aria-hidden="true" />
              </button>
            </div>
          ))}
        </div>

        {/* Bottom Icon Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: 10 }}>
          <button
            type="button"
            className="icon-btn"
            aria-label="模型连接设置"
            onClick={() => setProviderDialogOpen(true)}
          >
            <Settings2 size={15} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="icon-btn"
            aria-label="切换深浅色主题"
            onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
          >
            {theme === 'dark' ? <Sun size={15} aria-hidden="true" /> : <Moon size={15} aria-hidden="true" />}
          </button>
        </div>
      </nav>

      {/* Center Immersive Chat Column */}
      <main className="main-column">
        <header className="top-bar">
          {/* Model Status Capsule */}
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              className="icon-btn"
              aria-label="切换或接入模型"
              onClick={() => setModelMenuOpen((o) => !o)}
            >
              <span className={`status-dot ${selectedProviderId === 'demo' ? 'demo' : ''}`} />
              <span>{selectedModel}</span>
              <ChevronDown size={14} aria-hidden="true" />
            </button>

            {modelMenuOpen && (
              <div
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 6px)',
                  left: 0,
                  minWidth: 210,
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 14,
                  padding: 6,
                  zIndex: 20,
                  boxShadow: '0 12px 28px rgba(0,0,0,0.16)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 4,
                }}
              >
                {providers.flatMap((p) =>
                  p.models.map((m) => (
                    <button
                      key={`${p.id}:${m}`}
                      type="button"
                      onClick={() => {
                        setSelectedProviderId(p.id);
                        setSelectedModel(m);
                        setModelMenuOpen(false);
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '7px 10px',
                        borderRadius: 9,
                        border: 'none',
                        background: p.id === selectedProviderId && m === selectedModel ? 'var(--brand-soft)' : 'transparent',
                        color: 'var(--fg)',
                        fontSize: 13,
                        cursor: 'pointer',
                      }}
                    >
                      <span>{m}</span>
                      <span style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{p.name}</span>
                    </button>
                  )),
                )}
                <button
                  type="button"
                  aria-label="管理模型供应商"
                  className="icon-btn"
                  style={{ width: '100%', marginTop: 4 }}
                  onClick={() => {
                    setModelMenuOpen(false);
                    setProviderDialogOpen(true);
                  }}
                >
                  <Plus size={14} aria-hidden="true" />
                  Provider
                </button>
              </div>
            )}
          </div>

          {/* Right Capsules: Incognito Ghost + Memory Counter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              type="button"
              aria-label="无痕模式"
              aria-pressed={incognito}
              title="无痕模式"
              className={`icon-btn ${incognito ? 'incognito-on' : ''}`}
              onClick={handleToggleIncognito}
            >
              <Ghost size={16} aria-hidden="true" />
            </button>

            <button
              type="button"
              aria-label="记忆面板"
              aria-expanded={drawerOpen}
              className={`icon-btn ${drawerOpen ? 'memory-active' : ''}`}
              onClick={() => {
                setDrawerOpen((o) => !o);
                refreshMemories();
              }}
            >
              <Brain size={16} aria-hidden="true" />
              <span>{activeMemoryCount}</span>
            </button>
          </div>
        </header>

        <ChatStage
          messages={messages}
          incognito={incognito}
          streaming={streaming}
          extensionSlots={extensionSlots}
          onSend={handleSend}
          onOpenProfile={() => setDrawerOpen(true)}
          onOpenProviders={() => setProviderDialogOpen(true)}
          onUndoMemory={async (memId, msgId) => {
            await api.undoMemory(memId);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === msgId
                  ? {
                      ...m,
                      memory_events: m.memory_events.map((ev) =>
                        ev.memory.id === memId ? { ...ev, undone: true } : ev,
                      ),
                    }
                  : m,
              ),
            );
            await refreshMemories();
          }}
        />
      </main>

      {/* Right Visual Memory Drawer */}
      {drawerOpen && (
        <MemoryDrawer
          memories={memories}
          summaries={summaries}
          topK={topK}
          threshold={threshold}
          onChangeTopK={setTopK}
          onChangeThreshold={setThreshold}
          onAddMemory={async (layer: MemoryLayer, category: string, content: string) => {
            await api.createMemory({ layer, category, content, is_pinned: layer === 'profile' });
            await refreshMemories();
          }}
          onToggleEnable={async (mem) => {
            await api.patchMemory(mem.id, { is_enabled: !mem.is_enabled });
            await refreshMemories();
          }}
          onTogglePin={async (mem) => {
            await api.patchMemory(mem.id, { is_pinned: !mem.is_pinned });
            await refreshMemories();
          }}
          onArchive={async (memId) => {
            await api.deleteMemory(memId);
            await refreshMemories();
          }}
          onClose={() => setDrawerOpen(false)}
        />
      )}

      <ProviderDialog
        open={providerDialogOpen}
        presets={presets}
        onClose={() => setProviderDialogOpen(false)}
        onSave={async (payload) => {
          const saved = await api.saveProvider(payload);
          const list = await api.getProviders();
          setProviders(list);
          setSelectedProviderId(saved.id);
          setSelectedModel(saved.models[0] || 'default');
        }}
      />
    </div>
  );
}
