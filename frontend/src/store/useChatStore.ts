import { create } from 'zustand';
import { api } from '../api';
import type {
  ChatMessage,
  Conversation,
  MemoryItem,
  MemoryLayer,
  ModelProvider,
  SessionSummary,
  SkillMeta,
} from '../types';

interface ChatStore {
  providers: ModelProvider[];
  conversations: Conversation[];
  activeConvId: string | null;
  messages: ChatMessage[];
  memories: MemoryItem[];
  summaries: SessionSummary[];
  skills: SkillMeta[];

  selectedProviderId: string;
  selectedModel: string;
  incognito: boolean;
  sidebarOpen: boolean;
  drawerOpen: boolean;
  settingsOpen: boolean;
  streaming: boolean;
  topK: number;
  threshold: number;

  bootstrap: () => Promise<void>;
  refreshMemories: () => Promise<void>;
  setSidebarOpen: (open: boolean) => void;
  setDrawerOpen: (open: boolean) => void;
  setSettingsOpen: (open: boolean) => void;
  setSelectedModel: (providerId: string, model: string) => void;
  setTopK: (val: number) => void;
  setThreshold: (val: number) => void;
  toggleIncognito: () => Promise<void>;

  selectConversation: (conv: Conversation) => Promise<void>;
  startNewConversation: () => Promise<void>;
  removeConversation: (convId: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;

  addMemory: (layer: MemoryLayer, content: string) => Promise<void>;
  toggleMemoryEnable: (mem: MemoryItem) => Promise<void>;
  toggleMemoryPin: (mem: MemoryItem) => Promise<void>;
  archiveMemory: (memId: string) => Promise<void>;
  undoMessageMemory: (memId: string, msgId: string) => Promise<void>;

  saveProvider: (payload: {
    id: string;
    name: string;
    base_url: string;
    api_key: string;
    models: string[];
  }) => Promise<void>;
  deleteProvider: (id: string) => Promise<void>;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  providers: [],
  conversations: [],
  activeConvId: null,
  messages: [],
  memories: [],
  summaries: [],
  skills: [],

  selectedProviderId: '',
  selectedModel: '',
  incognito: false,
  sidebarOpen: true,
  drawerOpen: false,
  settingsOpen: false,
  streaming: false,
  topK: 5,
  threshold: 0.25,

  bootstrap: async () => {
    const [provList, convList, memList, sumList, skillList] = await Promise.all([
      api.getProviders(),
      api.getConversations(),
      api.getMemories(),
      api.getSummaries(),
      api.getSkills(),
    ]);

    const firstProv = provList[0];
    set({
      providers: provList,
      conversations: convList,
      memories: memList,
      summaries: sumList,
      skills: skillList,
      selectedProviderId: firstProv ? firstProv.id : '',
      selectedModel: firstProv?.models[0] || '',
    });

    if (convList.length > 0) {
      const top = convList[0];
      const msgs = await api.getMessages(top.id);
      set({
        activeConvId: top.id,
        incognito: !top.memory_enabled,
        messages: msgs,
      });
    }
  },

  refreshMemories: async () => {
    const [mems, sums] = await Promise.all([api.getMemories(), api.getSummaries()]);
    set({ memories: mems, summaries: sums });
  },

  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setDrawerOpen: (open) => set({ drawerOpen: open }),
  setSettingsOpen: (open) => set({ settingsOpen: open }),
  setSelectedModel: (providerId, model) => set({ selectedProviderId: providerId, selectedModel: model }),
  setTopK: (val) => set({ topK: val }),
  setThreshold: (val) => set({ threshold: val }),

  toggleIncognito: async () => {
    const next = !get().incognito;
    set({ incognito: next });
    const convId = get().activeConvId;
    if (convId) {
      await api.patchConversation(convId, { memory_enabled: !next });
    }
  },

  selectConversation: async (conv) => {
    const msgs = await api.getMessages(conv.id);
    set({
      activeConvId: conv.id,
      incognito: !conv.memory_enabled,
      messages: msgs,
    });
  },

  startNewConversation: async () => {
    const { selectedProviderId, selectedModel, incognito } = get();
    const created = await api.createConversation({
      title: '新对话',
      active_provider_id: selectedProviderId,
      active_model: selectedModel,
      memory_enabled: !incognito,
    });
    set((s) => ({
      conversations: [created, ...s.conversations],
      activeConvId: created.id,
      messages: [],
    }));
  },

  removeConversation: async (convId) => {
    await api.deleteConversation(convId);
    set((s) => {
      const nextList = s.conversations.filter((c) => c.id !== convId);
      const isCurrent = s.activeConvId === convId;
      return {
        conversations: nextList,
        activeConvId: isCurrent ? null : s.activeConvId,
        messages: isCurrent ? [] : s.messages,
      };
    });
  },

  sendMessage: async (content) => {
    const state = get();
    if (!state.selectedProviderId || !state.selectedModel) {
      set({ settingsOpen: true });
      return;
    }

    let convId = state.activeConvId;
    if (!convId) {
      const created = await api.createConversation({
        title: content.slice(0, 20),
        active_provider_id: state.selectedProviderId,
        active_model: state.selectedModel,
        memory_enabled: !state.incognito,
      });
      convId = created.id;
      set((s) => ({
        conversations: [created, ...s.conversations],
        activeConvId: created.id,
      }));
    }

    const tempUserId = `u_${Date.now()}`;
    const tempAsstId = `a_${Date.now()}`;
    set((s) => ({
      streaming: true,
      messages: [
        ...s.messages,
        { id: tempUserId, conversation_id: convId!, role: 'user', content, memory_refs: [], memory_events: [] },
        { id: tempAsstId, conversation_id: convId!, role: 'assistant', content: '', memory_refs: [], memory_events: [], streaming: true },
      ],
    }));

    try {
      await api.streamChat(
        {
          conversation_id: convId,
          content,
          provider_id: state.selectedProviderId,
          model: state.selectedModel,
          memory_enabled: !state.incognito,
          top_k: state.topK,
          threshold: state.threshold,
        },
        {
          onContext: (items) => {
            set((s) => ({
              messages: s.messages.map((m) => (m.id === tempAsstId ? { ...m, memory_refs: items } : m)),
            }));
          },
          onDelta: (delta) => {
            set((s) => ({
              messages: s.messages.map((m) => (m.id === tempAsstId ? { ...m, content: m.content + delta } : m)),
            }));
          },
          onMemoryUpdated: (ev) => {
            set((s) => ({
              messages: s.messages.map((m) =>
                m.id === tempUserId ? { ...m, memory_events: [...m.memory_events, ev] } : m,
              ),
            }));
            get().refreshMemories();
          },
          onDone: () => {
            set((s) => ({
              messages: s.messages.map((m) => (m.id === tempAsstId ? { ...m, streaming: false } : m)),
            }));
          },
        },
      );
      const updatedConvs = await api.getConversations();
      set({ conversations: updatedConvs });
    } finally {
      set({ streaming: false });
    }
  },

  addMemory: async (layer, content) => {
    await api.createMemory({ layer, category: 'general', content, is_pinned: layer === 'profile' });
    await get().refreshMemories();
  },

  toggleMemoryEnable: async (mem) => {
    await api.patchMemory(mem.id, { is_enabled: !mem.is_enabled });
    await get().refreshMemories();
  },

  toggleMemoryPin: async (mem) => {
    await api.patchMemory(mem.id, { is_pinned: !mem.is_pinned });
    await get().refreshMemories();
  },

  archiveMemory: async (memId) => {
    await api.deleteMemory(memId);
    await get().refreshMemories();
  },

  undoMessageMemory: async (memId, msgId) => {
    await api.undoMemory(memId);
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === msgId
          ? {
              ...m,
              memory_events: m.memory_events.map((ev) =>
                ev.memory.id === memId ? { ...ev, undone: true } : ev,
              ),
            }
          : m,
      ),
    }));
    await get().refreshMemories();
  },

  saveProvider: async (payload) => {
    const saved = await api.saveProvider(payload);
    const list = await api.getProviders();
    set({
      providers: list,
      selectedProviderId: saved.id,
      selectedModel: saved.models[0] || '',
    });
  },

  deleteProvider: async (id) => {
    await api.deleteProvider(id);
    const list = await api.getProviders();
    const first = list[0];
    set({
      providers: list,
      selectedProviderId: first ? first.id : '',
      selectedModel: first?.models[0] || '',
    });
  },
}));
