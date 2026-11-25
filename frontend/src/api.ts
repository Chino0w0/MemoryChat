import type {
  ChatMessage,
  Conversation,
  MemoryEvent,
  MemoryItem,
  MemoryLayer,
  ModelProvider,
  SessionSummary,
  SkillMeta,
} from './types';

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getProviders: () => request<ModelProvider[]>('/api/providers'),
  saveProvider: (payload: {
    id: string;
    name: string;
    base_url: string;
    api_key: string;
    models: string[];
  }) => request<ModelProvider>('/api/providers', { method: 'POST', body: JSON.stringify(payload) }),
  testProvider: (payload: { base_url: string; api_key: string }) =>
    request<{ ok: boolean; models: string[] }>('/api/providers/test', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  deleteProvider: (id: string) => request<{ deleted: boolean }>(`/api/providers/${id}`, { method: 'DELETE' }),

  getConversations: () => request<Conversation[]>('/api/conversations'),
  createConversation: (payload: Partial<Conversation> = {}) =>
    request<Conversation>('/api/conversations', { method: 'POST', body: JSON.stringify(payload) }),
  patchConversation: (id: string, payload: Partial<Conversation>) =>
    request<Conversation>(`/api/conversations/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteConversation: (id: string) =>
    request<{ deleted: boolean }>(`/api/conversations/${id}`, { method: 'DELETE' }),
  getMessages: (convId: string) => request<ChatMessage[]>(`/api/conversations/${convId}/messages`),

  getMemories: () => request<MemoryItem[]>('/api/memories'),
  createMemory: (payload: { layer: MemoryLayer; category: string; content: string; is_pinned?: boolean }) =>
    request<MemoryItem>('/api/memories', { method: 'POST', body: JSON.stringify(payload) }),
  patchMemory: (id: string, payload: Partial<MemoryItem>) =>
    request<MemoryItem>(`/api/memories/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteMemory: (id: string) => request<MemoryItem>(`/api/memories/${id}`, { method: 'DELETE' }),
  undoMemory: (id: string) => request<MemoryItem>(`/api/memories/${id}/undo`, { method: 'POST' }),

  getSummaries: () => request<SessionSummary[]>('/api/summaries'),
  getSkills: () => request<SkillMeta[]>('/api/skills'),

  async streamChat(
    params: {
      conversation_id: string;
      content: string;
      provider_id: string;
      model: string;
      memory_enabled: boolean;
      top_k: number;
      threshold: number;
    },
    handlers: {
      onContext: (items: MemoryItem[]) => void;
      onDelta: (delta: string) => void;
      onMemoryUpdated: (ev: MemoryEvent) => void;
      onDone: () => void;
    },
  ): Promise<void> {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!res.ok || !res.body) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `Stream HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let boundary = buffer.indexOf('\n\n');
      while (boundary !== -1) {
        const rawBlock = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);

        let eventName = 'message';
        let dataLine = '';
        for (const line of rawBlock.split('\n')) {
          if (line.startsWith('event:')) eventName = line.slice(6).trim();
          if (line.startsWith('data:')) dataLine = line.slice(5).trim();
        }
        if (dataLine) {
          const parsed = JSON.parse(dataLine);
          if (eventName === 'memory_context') handlers.onContext(parsed.items || []);
          else if (eventName === 'text_delta') handlers.onDelta(parsed.delta || '');
          else if (eventName === 'memory_updated') handlers.onMemoryUpdated(parsed);
          else if (eventName === 'done') handlers.onDone();
        }
        boundary = buffer.indexOf('\n\n');
      }
    }
  },
};
