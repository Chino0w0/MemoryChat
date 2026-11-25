PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS model_providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    api_key TEXT DEFAULT '',
    models_json TEXT NOT NULL,
    is_enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    active_provider_id TEXT DEFAULT '',
    active_model TEXT DEFAULT '',
    memory_enabled INTEGER DEFAULT 1,
    active_skills_json TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    model_used TEXT,
    tool_calls_json TEXT DEFAULT '[]',
    memory_refs_json TEXT DEFAULT '[]',
    memory_events_json TEXT DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    layer TEXT NOT NULL CHECK(layer IN ('profile', 'episodic')),
    category TEXT NOT NULL DEFAULT 'general',
    content TEXT NOT NULL,
    source_message_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
    source_quote TEXT,
    confidence REAL DEFAULT 1.0,
    embedding_blob BLOB,
    is_pinned INTEGER DEFAULT 0,
    is_enabled INTEGER DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'archived')),
    replaced_by_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_summaries (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL UNIQUE REFERENCES conversations(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    key_topics_json TEXT DEFAULT '[]',
    covered_until_msg_id TEXT,
    embedding_blob BLOB,
    updated_at TEXT NOT NULL
);
