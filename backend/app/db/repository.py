from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repository:
    """Lightweight SQLite authority store for conversations, providers, and 3-layer memories."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        schema_sql = schema_path.read_text(encoding="utf-8")
        with self._connect() as conn:
            conn.executescript(schema_sql)
            existing = conn.execute("SELECT id FROM model_providers WHERE id = 'demo'").fetchone()
            if not existing:
                conn.execute(
                    """
                    INSERT INTO model_providers (id, name, base_url, api_key, models_json, is_enabled, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("demo", "Local Demo", "local://demo", "", json.dumps(["memorychat-demo"]), 1, _utc_now()),
                )

    # ---- Providers ----
    def list_providers(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM model_providers ORDER BY created_at ASC").fetchall()
        return [self._format_provider(r) for r in rows]

    def get_provider(self, provider_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM model_providers WHERE id = ?", (provider_id,)).fetchone()
        return self._format_provider(row, include_secret=True) if row else None

    def upsert_provider(
        self,
        provider_id: str,
        name: str,
        base_url: str,
        models: list[str],
        api_key: str = "",
        is_enabled: bool = True,
    ) -> dict[str, Any]:
        now = _utc_now()
        with self._connect() as conn:
            prev = conn.execute("SELECT api_key, created_at FROM model_providers WHERE id = ?", (provider_id,)).fetchone()
            final_key = api_key if api_key else (prev["api_key"] if prev else "")
            created_at = prev["created_at"] if prev else now
            conn.execute(
                """
                INSERT INTO model_providers (id, name, base_url, api_key, models_json, is_enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    base_url = excluded.base_url,
                    api_key = excluded.api_key,
                    models_json = excluded.models_json,
                    is_enabled = excluded.is_enabled
                """,
                (provider_id, name, base_url, final_key, json.dumps(models), int(is_enabled), created_at),
            )
            row = conn.execute("SELECT * FROM model_providers WHERE id = ?", (provider_id,)).fetchone()
        return self._format_provider(row)

    def delete_provider(self, provider_id: str) -> bool:
        if provider_id == "demo":
            return False
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM model_providers WHERE id = ?", (provider_id,))
        return cur.rowcount > 0

    @staticmethod
    def _format_provider(row: sqlite3.Row, include_secret: bool = False) -> dict[str, Any]:
        data = {
            "id": row["id"],
            "name": row["name"],
            "base_url": row["base_url"],
            "models": json.loads(row["models_json"] or "[]"),
            "is_enabled": bool(row["is_enabled"]),
            "has_key": bool(row["api_key"]) or row["base_url"].startswith("local://"),
            "created_at": row["created_at"],
        }
        if include_secret:
            data["api_key"] = row["api_key"] or ""
        return data

    # ---- Conversations & Messages ----
    def create_conversation(
        self,
        title: str = "新对话",
        active_provider_id: str = "demo",
        active_model: str = "memorychat-demo",
        memory_enabled: bool = True,
    ) -> dict[str, Any]:
        conv_id = f"conv_{uuid.uuid4().hex[:10]}"
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, title, active_provider_id, active_model, memory_enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (conv_id, title, active_provider_id, active_model, int(memory_enabled), now, now),
            )
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        return self._format_conversation(row)

    def list_conversations(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
        return [self._format_conversation(r) for r in rows]

    def get_conversation(self, conv_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        return self._format_conversation(row) if row else None

    def update_conversation(self, conv_id: str, **fields: Any) -> dict[str, Any] | None:
        allowed = {"title", "active_provider_id", "active_model", "memory_enabled"}
        updates: list[str] = []
        values: list[Any] = []
        for k, v in fields.items():
            if k in allowed and v is not None:
                updates.append(f"{k} = ?")
                values.append(int(v) if k == "memory_enabled" else v)
        if not updates:
            return self.get_conversation(conv_id)
        updates.append("updated_at = ?")
        values.append(_utc_now())
        values.append(conv_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?", values)
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        return self._format_conversation(row) if row else None

    def delete_conversation(self, conv_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        return cur.rowcount > 0

    @staticmethod
    def _format_conversation(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "active_provider_id": row["active_provider_id"],
            "active_model": row["active_model"],
            "memory_enabled": bool(row["memory_enabled"]),
            "active_skills": json.loads(row["active_skills_json"] or "[]"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model_used: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        memory_refs: list[dict[str, Any]] | None = None,
        memory_events: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, model_used, tool_calls_json, memory_refs_json, memory_events_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg_id,
                    conversation_id,
                    role,
                    content,
                    model_used,
                    json.dumps(tool_calls or [], ensure_ascii=False),
                    json.dumps(memory_refs or [], ensure_ascii=False),
                    json.dumps(memory_events or [], ensure_ascii=False),
                    now,
                ),
            )
            conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
            row = conn.execute("SELECT * FROM messages WHERE id = ?", (msg_id,)).fetchone()
        return self._format_message(row)

    def update_message_events(self, msg_id: str, memory_events: list[dict[str, Any]]) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE messages SET memory_events_json = ? WHERE id = ?",
                (json.dumps(memory_events, ensure_ascii=False), msg_id),
            )

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC, rowid ASC",
                (conversation_id,),
            ).fetchall()
        return [self._format_message(r) for r in rows]

    @staticmethod
    def _format_message(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "role": row["role"],
            "content": row["content"],
            "model_used": row["model_used"],
            "tool_calls": json.loads(row["tool_calls_json"] or "[]"),
            "memory_refs": json.loads(row["memory_refs_json"] or "[]"),
            "memory_events": json.loads(row["memory_events_json"] or "[]"),
            "created_at": row["created_at"],
        }

    # ---- Layered Personal Memories ----
    def add_memory(
        self,
        layer: str,
        content: str,
        category: str = "general",
        source_message_id: str | None = None,
        source_quote: str | None = None,
        confidence: float = 1.0,
        embedding_blob: bytes | None = None,
        is_pinned: bool = False,
        is_enabled: bool = True,
    ) -> dict[str, Any]:
        mem_id = f"mem_{uuid.uuid4().hex[:10]}"
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (
                    id, layer, category, content, source_message_id, source_quote,
                    confidence, embedding_blob, is_pinned, is_enabled, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    mem_id,
                    layer,
                    category,
                    content,
                    source_message_id,
                    source_quote,
                    float(confidence),
                    embedding_blob,
                    int(is_pinned),
                    int(is_enabled),
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (mem_id,)).fetchone()
        return self._format_memory(row)

    def get_memory(self, mem_id: str, include_blob: bool = False) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (mem_id,)).fetchone()
        return self._format_memory(row, include_blob=include_blob) if row else None

    def list_memories(
        self,
        layer: str | None = None,
        active_only: bool = True,
        include_blob: bool = False,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if active_only:
            clauses.append("status = 'active'")
        if layer:
            clauses.append("layer = ?")
            params.append(layer)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM memories {where_sql} ORDER BY is_pinned DESC, updated_at DESC",
                params,
            ).fetchall()
        return [self._format_memory(r, include_blob=include_blob) for r in rows]

    def list_injectable_memories(self, include_blob: bool = True) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM memories WHERE status = 'active' AND is_enabled = 1 ORDER BY is_pinned DESC, updated_at DESC"
            ).fetchall()
        return [self._format_memory(r, include_blob=include_blob) for r in rows]

    def update_memory(self, mem_id: str, **fields: Any) -> dict[str, Any] | None:
        allowed = {"layer", "category", "content", "is_pinned", "is_enabled", "embedding_blob"}
        updates: list[str] = []
        values: list[Any] = []
        for k, v in fields.items():
            if k in allowed and v is not None:
                updates.append(f"{k} = ?")
                values.append(int(v) if k in {"is_pinned", "is_enabled"} else v)
        if not updates:
            return self.get_memory(mem_id)
        updates.append("updated_at = ?")
        values.append(_utc_now())
        values.append(mem_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE memories SET {', '.join(updates)} WHERE id = ?", values)
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (mem_id,)).fetchone()
        return self._format_memory(row) if row else None

    def archive_memory(self, mem_id: str, replaced_by_id: str | None = None) -> dict[str, Any] | None:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE memories SET status = 'archived', replaced_by_id = ?, updated_at = ? WHERE id = ?",
                (replaced_by_id, now, mem_id),
            )
            # If undoing an UPDATE memory, restore any memory it superseded
            if replaced_by_id is None:
                conn.execute(
                    "UPDATE memories SET status = 'active', replaced_by_id = NULL, updated_at = ? WHERE replaced_by_id = ?",
                    (now, mem_id),
                )
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (mem_id,)).fetchone()
        return self._format_memory(row) if row else None

    @staticmethod
    def _format_memory(row: sqlite3.Row, include_blob: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": row["id"],
            "layer": row["layer"],
            "category": row["category"],
            "content": row["content"],
            "source_message_id": row["source_message_id"],
            "source_quote": row["source_quote"],
            "confidence": round(float(row["confidence"]), 3),
            "is_pinned": bool(row["is_pinned"]),
            "is_enabled": bool(row["is_enabled"]),
            "status": row["status"],
            "replaced_by_id": row["replaced_by_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        if include_blob:
            data["embedding_blob"] = row["embedding_blob"]
        return data

    # ---- Session Summaries ----
    def upsert_summary(
        self,
        conversation_id: str,
        summary_text: str,
        key_topics: list[str] | None = None,
        covered_until_msg_id: str | None = None,
        embedding_blob: bytes | None = None,
    ) -> dict[str, Any]:
        now = _utc_now()
        with self._connect() as conn:
            prev = conn.execute(
                "SELECT id FROM session_summaries WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            sum_id = prev["id"] if prev else f"sum_{uuid.uuid4().hex[:10]}"
            conn.execute(
                """
                INSERT INTO session_summaries (id, conversation_id, summary_text, key_topics_json, covered_until_msg_id, embedding_blob, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    summary_text = excluded.summary_text,
                    key_topics_json = excluded.key_topics_json,
                    covered_until_msg_id = excluded.covered_until_msg_id,
                    embedding_blob = excluded.embedding_blob,
                    updated_at = excluded.updated_at
                """,
                (
                    sum_id,
                    conversation_id,
                    summary_text,
                    json.dumps(key_topics or [], ensure_ascii=False),
                    covered_until_msg_id,
                    embedding_blob,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM session_summaries WHERE conversation_id = ?", (conversation_id,)).fetchone()
        return self._format_summary(row)

    def get_summary(self, conversation_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM session_summaries WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
        return self._format_summary(row) if row else None

    def list_summaries(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM session_summaries ORDER BY updated_at DESC").fetchall()
        return [self._format_summary(r) for r in rows]

    @staticmethod
    def _format_summary(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "summary_text": row["summary_text"],
            "key_topics": json.loads(row["key_topics_json"] or "[]"),
            "covered_until_msg_id": row["covered_until_msg_id"],
            "updated_at": row["updated_at"],
        }
