from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.db.repository import Repository
from app.extensions.interfaces import ExtensionRegistry
from app.llm.provider import PRESET_PROVIDERS, MultiProviderClient
from app.memory.pipeline import MemoryPipeline
from app.ml.embedder import MemoryEmbedder
from app.ml.memory_gate import MemoryGateClassifier


class ProviderUpsertRequest(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=60)
    base_url: str = Field(min_length=4, max_length=260)
    api_key: str = ""
    models: list[str] = Field(min_length=1)
    is_enabled: bool = True


class ConversationCreateRequest(BaseModel):
    title: str = "新对话"
    active_provider_id: str = "demo"
    active_model: str = "memorychat-demo"
    memory_enabled: bool = True


class ConversationPatchRequest(BaseModel):
    title: str | None = None
    active_provider_id: str | None = None
    active_model: str | None = None
    memory_enabled: bool | None = None


class MemoryCreateRequest(BaseModel):
    layer: str = "profile"
    category: str = "preference"
    content: str = Field(min_length=1, max_length=300)
    is_pinned: bool = False

    @field_validator("content")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Memory content cannot be blank")
        return v.strip()


class MemoryPatchRequest(BaseModel):
    layer: str | None = None
    category: str | None = None
    content: str | None = None
    is_pinned: bool | None = None
    is_enabled: bool | None = None


class ChatStreamRequest(BaseModel):
    conversation_id: str
    content: str
    provider_id: str | None = None
    model: str | None = None
    memory_enabled: bool | None = None
    top_k: int = Field(default=5, ge=1, le=10)
    threshold: float = Field(default=0.15, ge=0.0, le=0.95)

    @field_validator("content")
    @classmethod
    def _validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        return v.strip()


def _sse_frame(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def create_app(db_path: str | Path | None = None) -> FastAPI:
    default_db = Path(__file__).resolve().parents[1] / "data" / "memorychat.db"
    repo = Repository(db_path or default_db)
    repo.init_db()

    gate = MemoryGateClassifier()
    embedder = MemoryEmbedder()
    llm = MultiProviderClient()
    pipeline = MemoryPipeline(repo=repo, gate=gate, embedder=embedder, llm=llm)
    extensions = ExtensionRegistry()

    app = FastAPI(title="MemoryChat API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": "1.0.0"}

    # ---- Providers ----
    @app.get("/api/providers/presets")
    def list_presets() -> list[dict[str, Any]]:
        return PRESET_PROVIDERS

    @app.get("/api/providers")
    def list_providers() -> list[dict[str, Any]]:
        return repo.list_providers()

    @app.post("/api/providers")
    def upsert_provider(req: ProviderUpsertRequest) -> dict[str, Any]:
        return repo.upsert_provider(
            provider_id=req.id.strip(),
            name=req.name.strip(),
            base_url=req.base_url.strip(),
            models=[m.strip() for m in req.models if m.strip()],
            api_key=req.api_key.strip(),
            is_enabled=req.is_enabled,
        )

    @app.delete("/api/providers/{provider_id}")
    def delete_provider(provider_id: str) -> dict[str, bool]:
        return {"deleted": repo.delete_provider(provider_id)}

    # ---- Conversations ----
    @app.get("/api/conversations")
    def list_conversations() -> list[dict[str, Any]]:
        return repo.list_conversations()

    @app.post("/api/conversations")
    def create_conversation(req: ConversationCreateRequest) -> dict[str, Any]:
        return repo.create_conversation(
            title=req.title,
            active_provider_id=req.active_provider_id,
            active_model=req.active_model,
            memory_enabled=req.memory_enabled,
        )

    @app.patch("/api/conversations/{conv_id}")
    def patch_conversation(conv_id: str, req: ConversationPatchRequest) -> dict[str, Any]:
        updated = repo.update_conversation(conv_id, **req.model_dump(exclude_none=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return updated

    @app.delete("/api/conversations/{conv_id}")
    def remove_conversation(conv_id: str) -> dict[str, bool]:
        return {"deleted": repo.delete_conversation(conv_id)}

    @app.get("/api/conversations/{conv_id}/messages")
    def list_messages(conv_id: str) -> list[dict[str, Any]]:
        return repo.list_messages(conv_id)

    # ---- Memories & Summaries ----
    @app.get("/api/memories")
    def list_memories(layer: str | None = None) -> list[dict[str, Any]]:
        return repo.list_memories(layer=layer, active_only=True)

    @app.post("/api/memories")
    def create_memory(req: MemoryCreateRequest) -> dict[str, Any]:
        layer = req.layer if req.layer in {"profile", "episodic"} else "profile"
        blob = embedder.to_blob(embedder.encode(req.content))
        return repo.add_memory(
            layer=layer,
            category=req.category,
            content=req.content,
            confidence=1.0,
            embedding_blob=blob,
            is_pinned=req.is_pinned or (layer == "profile"),
        )

    @app.patch("/api/memories/{mem_id}")
    def patch_memory(mem_id: str, req: MemoryPatchRequest) -> dict[str, Any]:
        fields = req.model_dump(exclude_none=True)
        if "content" in fields:
            fields["content"] = fields["content"].strip()
            fields["embedding_blob"] = embedder.to_blob(embedder.encode(fields["content"]))
        updated = repo.update_memory(mem_id, **fields)
        if not updated:
            raise HTTPException(status_code=404, detail="Memory not found")
        return updated

    @app.delete("/api/memories/{mem_id}")
    def delete_memory(mem_id: str) -> dict[str, Any]:
        archived = repo.archive_memory(mem_id)
        if not archived:
            raise HTTPException(status_code=404, detail="Memory not found")
        return archived

    @app.post("/api/memories/{mem_id}/undo")
    def undo_memory(mem_id: str) -> dict[str, Any]:
        archived = repo.archive_memory(mem_id, replaced_by_id=None)
        if not archived:
            raise HTTPException(status_code=404, detail="Memory not found")
        return archived

    @app.get("/api/summaries")
    def list_summaries() -> list[dict[str, Any]]:
        return repo.list_summaries()

    # ---- Extension Slots ----
    @app.get("/api/extensions/slots")
    def list_extension_slots() -> list[dict[str, Any]]:
        return extensions.list_slots()

    # ---- Streaming Chat + Memory Linkage ----
    @app.post("/api/chat/stream")
    def chat_stream(req: ChatStreamRequest) -> StreamingResponse:
        conv = repo.get_conversation(req.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        provider_id = req.provider_id or conv["active_provider_id"] or "demo"
        provider = repo.get_provider(provider_id) or repo.get_provider("demo")
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")

        model = req.model or conv["active_model"] or (provider["models"][0] if provider["models"] else "memorychat-demo")
        mem_enabled = req.memory_enabled if req.memory_enabled is not None else conv["memory_enabled"]

        # Auto-title new conversations concisely from the first user prompt
        history = repo.list_messages(conv["id"])
        if not history and conv["title"] == "新对话":
            repo.update_conversation(conv["id"], title=req.content[:18])

        sys_prompt, refs = pipeline.prepare_context(
            conversation_id=conv["id"],
            query=req.content,
            memory_enabled=mem_enabled,
            top_k=req.top_k,
            threshold=req.threshold,
        )

        user_msg = repo.add_message(
            conversation_id=conv["id"],
            role="user",
            content=req.content,
        )

        llm_messages = [{"role": "system", "content": sys_prompt}]
        for m in history[-10:]:
            if m["role"] in {"user", "assistant"}:
                llm_messages.append({"role": m["role"], "content": m["content"]})
        llm_messages.append({"role": "user", "content": req.content})

        def event_stream() -> Iterator[str]:
            yield _sse_frame("memory_context", {"items": refs})
            collected: list[str] = []
            try:
                for delta in llm.stream_chat(provider=provider, model=model, messages=llm_messages):
                    collected.append(delta)
                    yield _sse_frame("text_delta", {"delta": delta})
            except Exception as exc:
                err_msg = f"模型请求失败（{exc}）"
                collected.append(err_msg)
                yield _sse_frame("text_delta", {"delta": err_msg})

            assistant_msg = repo.add_message(
                conversation_id=conv["id"],
                role="assistant",
                content="".join(collected),
                model_used=model,
                memory_refs=refs,
            )

            mem_event = pipeline.process_turn(
                conversation_id=conv["id"],
                message_id=user_msg["id"],
                user_text=req.content,
                provider=provider,
                model=model,
                memory_enabled=mem_enabled,
            )
            if mem_event:
                yield _sse_frame("memory_updated", mem_event)

            pipeline.maybe_update_summary(conv["id"], provider=provider, model=model)
            yield _sse_frame("done", {"message_id": assistant_msg["id"], "model": model})

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return app


app = create_app()
