export type MemoryLayer = 'profile' | 'episodic';

export interface ProviderPreset {
  id: string;
  name: string;
  badge: string;
  base_url: string;
  models: string[];
  requires_key: boolean;
}

export interface ModelProvider {
  id: string;
  name: string;
  base_url: string;
  models: string[];
  is_enabled: boolean;
  has_key: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  active_provider_id: string;
  active_model: string;
  memory_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface MemoryItem {
  id: string;
  layer: MemoryLayer;
  category: string;
  content: string;
  source_quote?: string | null;
  confidence: number;
  score?: number;
  is_pinned: boolean;
  is_enabled: boolean;
  status: 'active' | 'archived';
  created_at: string;
}

export interface MemoryEvent {
  action: 'ADD' | 'UPDATE';
  gate_label?: string;
  memory: MemoryItem;
  undone?: boolean;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  model_used?: string | null;
  memory_refs: MemoryItem[];
  memory_events: MemoryEvent[];
  streaming?: boolean;
}

export interface SessionSummary {
  id: string;
  conversation_id: string;
  summary_text: string;
  key_topics: string[];
  updated_at: string;
}

export interface ExtensionSlot {
  slot: 'asr' | 'skill' | 'tool';
  label: string;
  status: 'reserved' | 'active';
  count?: number;
}
